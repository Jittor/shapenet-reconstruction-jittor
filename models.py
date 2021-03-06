import jittor as jt
jt.flags.use_cuda = 1
from jittor import nn

import jrender as jr
import math


class Encoder(nn.Module):
    def __init__(self, dim_in=4, dim_out=512, dim1=64, dim2=1024, im_size=64):
        super(Encoder, self).__init__()
        dim_hidden = [dim1, dim1*2, dim1*4, dim2, dim2]

        self.conv1 = nn.Conv(dim_in, dim_hidden[0], kernel_size=5, stride=2, padding=2)
        self.conv2 = nn.Conv(dim_hidden[0], dim_hidden[1], kernel_size=5, stride=2, padding=2)
        self.conv3 = nn.Conv(dim_hidden[1], dim_hidden[2], kernel_size=5, stride=2, padding=2)

        self.bn1 = nn.BatchNorm(dim_hidden[0])
        self.bn2 = nn.BatchNorm(dim_hidden[1])
        self.bn3 = nn.BatchNorm(dim_hidden[2])

        self.fc1 = nn.Linear(dim_hidden[2]*math.ceil(im_size/8)**2, dim_hidden[3])
        self.fc2 = nn.Linear(dim_hidden[3], dim_hidden[4])
        self.fc3 = nn.Linear(dim_hidden[4], dim_out)

    def execute(self, x):
        x = nn.relu(self.bn1(self.conv1(x)))
        x = nn.relu(self.bn2(self.conv2(x)))
        x = nn.relu(self.bn3(self.conv3(x)))
        x = x.view(x.size(0), -1)
        x = nn.relu(self.fc1(x))
        x = nn.relu(self.fc2(x))
        x = nn.relu(self.fc3(x))
        return x


class Decoder(nn.Module):
    def __init__(self, filename_obj, dim_in=512, centroid_scale=0.1, bias_scale=1.0, centroid_lr=0.1, bias_lr=1.0):
        super(Decoder, self).__init__()
        # load .obj
        self.template_mesh = jr.Mesh.from_obj(filename_obj)
        # vertices_base, faces = jr.load_obj(filename_obj)
        self.vertices_base = self.template_mesh.vertices[0].stop_grad() #vertices_base
        self.faces = self.template_mesh.faces[0].stop_grad() #faces

        self.nv = self.vertices_base.size(0)
        self.nf = self.faces.size(0)
        self.centroid_scale = centroid_scale
        self.bias_scale = bias_scale
        self.obj_scale = 0.5

        dim = 1024
        dim_hidden = [dim, dim*2]
        self.fc1 = nn.Linear(dim_in, dim_hidden[0])
        self.fc2 = nn.Linear(dim_hidden[0], dim_hidden[1])
        self.fc_centroid = nn.Linear(dim_hidden[1], 3)
        self.fc_bias = nn.Linear(dim_hidden[1], self.nv*3)

    def execute(self, x):
        batch_size = x.shape[0]
        x = nn.relu(self.fc1(x))
        x = nn.relu(self.fc2(x))

        # decoder follows NMR
        centroid = self.fc_centroid(x) * self.centroid_scale

        bias = self.fc_bias(x) * self.bias_scale
        bias = bias.view(-1, self.nv, 3)

        base = self.vertices_base * self.obj_scale

        sign = nn.sign(base )
        base = base.abs()
        base = jt.log(base / (1 - base))

        centroid = jt.tanh(centroid[:, None, :])
        scale_pos = 1 - centroid
        scale_neg = centroid + 1

        vertices = (base + bias).sigmoid() * sign
        vertices = nn.relu(vertices) * scale_pos - nn.relu(-vertices) * scale_neg
        vertices = vertices + centroid
        vertices = vertices * 0.5
        faces = self.faces[None, :, :].repeat(batch_size, 1, 1)

        return vertices, faces


class Model(nn.Module):
    def __init__(self, filename_obj, args):
        super(Model, self).__init__()

        self.encoder = Encoder(im_size=args.image_size)
        self.decoder = Decoder(filename_obj)
        self.renderer = jr.Renderer(image_size=args.image_size, sigma_val=args.sigma_val, 
                                        aggr_func_rgb='hard', camera_mode='look_at', viewing_angle=15,
                                        dist_eps=1e-10, dr_type='softras')
        self.laplacian_loss = jr.LaplacianLoss(self.decoder.vertices_base, self.decoder.faces)
        self.flatten_loss = jr.FlattenLoss(self.decoder.faces)

    def model_param(self):
        return list(self.encoder.parameters()) + list(self.decoder.parameters())

    def set_sigma(self, sigma):
        self.renderer.set_sigma(sigma)

    def reconstruct(self, images):
        vertices, faces = self.decoder(self.encoder(images))
        return vertices, faces

    def predict_multiview(self, image_a, image_b, viewpoint_a, viewpoint_b):
        batch_size = image_a.size(0)
        # [Ia, Ib]
        images = jt.contrib.concat((image_a, image_b), dim=0)
        # [Va, Va, Vb, Vb], set viewpoints
        viewpoints = jt.contrib.concat((viewpoint_a, viewpoint_a, viewpoint_b, viewpoint_b), dim=0)
        self.renderer.transform.set_eyes(viewpoints)

        vertices, faces = self.reconstruct(images)
        laplacian_loss = self.laplacian_loss(vertices)
        flatten_loss = self.flatten_loss(vertices)

        # [Ma, Mb, Ma, Mb]
        vertices = jt.contrib.concat((vertices, vertices), dim=0)
        faces = jt.contrib.concat((faces, faces), dim=0)

        # [Raa, Rba, Rab, Rbb], cross render multiview images
        silhouettes = self.renderer(vertices, faces, mode="silhouettes")
        return silhouettes.chunk(4, dim=0), laplacian_loss, flatten_loss

    def evaluate_iou(self, images, voxels):
        vertices, faces = self.reconstruct(images)

        faces_ = jr.face_vertices(vertices, faces)
        faces_norm = faces_ * 1. * (32. - 1) / 32. + 0.5
        voxels_predict = jr.voxelization(faces_norm, 32, False).numpy()
        voxels_predict = voxels_predict.transpose(0, 2, 1, 3)[:, :, :, ::-1]
        iou = (voxels * voxels_predict).sum((1, 2, 3)) / (0 < (voxels + voxels_predict)).sum((1, 2, 3))

        # print(faces_.min(), faces_.max())
        # print(faces_norm.min(), faces_norm.max())
        # print(voxels_predict.min(), faces_norm.max())
        # tmp = (voxels * voxels_predict)
        # print(tmp.min(), tmp.max(), tmp.sum())
        # tmp1 = (0 < (voxels + voxels_predict))
        # print(tmp1.min(), tmp1.max(), tmp1.sum())
        # breakpoint()
        # print(iou.min(), iou.max())
        # print("Voxels" + str(voxels_predict))
        # print("IoU" + str(iou))
        return iou, vertices, faces

    def execute(self, images=None, viewpoints=None, voxels=None, task='train'):
        if task == 'train':
            return self.predict_multiview(images[0], images[1], viewpoints[0], viewpoints[1])
        elif task == 'test':
            return self.evaluate_iou(images, voxels)
