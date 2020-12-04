def iou(predict, target, eps=1e-6):
    dims = tuple(range(len(predict.shape))[1:])
    intersect = (predict * target).sum(dims)
    union = (predict + target - predict * target).sum(dims) + eps
    return (intersect / union).sum() / intersect.numel()

def iou_loss(predict, target):
    return 1 - iou(predict, target)

def multiview_iou_loss(predicts, targets_a, targets_b):
    loss = (iou_loss(predicts[0], targets_a[:, 3]) + \
            iou_loss(predicts[1], targets_a[:, 3]) + \
            iou_loss(predicts[2], targets_b[:, 3]) + \
            iou_loss(predicts[3], targets_b[:, 3])) / 4
    return loss