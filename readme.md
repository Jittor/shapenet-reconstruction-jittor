3D reconstruction for ShapeNet dataset

# 数据集下载
```
bash download_dataset.sh
```

# 训练

```
git clone https://github.com/Jittor/shapenet-reconstruction-jittor.git
cd shapenet-reconstruction-jittor
git clone https://github.com/Jittor/jrender.git
mv jrender jrender-bak
mv jrender-bak/jrender .
python train.py -eid rcon
```

# 测试
```
python test.py -eid test -d 'data/results/models/recon/checkpoint_0250000.pkl'
```

# 速度测试

|           | 200次训练所用时间   | 
|  ----     | ----          |
| Jittor    | 15.66        |
| PyTorch   | 19.25        |
| 加速比   | 1.22           |

# 指标对比

| Class       | IoU(Jittor) | IoU(pytorch) | IoU(paper with pytorch) |
| ----------- | ----------- | ------------ | ----------------------- |
| Airplane    | **0.651**   | 0.650        | 0.642          |
| Bench       | **0.501**   | 0.488        | 0.508               |
| Cabinet     | 0.697   | 0.688        | **0.711**                       |
| Car         | 0.738       | 0.732        | **0.770**      |
| Chair       | 0.526       | 0.526      | **0.527**          |
| Display     | **0.627**   | 0.610        | 0.616           |
| Lamp        | 0.459   | 0.457        | **0.463**      |
| Loudspeaker | 0.654       | 0.651 | **0.665**       |
| Rifle       | 0.686 | **0.688** | 0.681                |
| Sofa        | 0.687       | 0.685 | **0.688**    |
| Table       | 0.458   | **0.459** | 0.449           |
| Telephone   | **0.854**   | 0.827 | 0.790                       |
| Watercraft  | **0.617**   | 0.613 | 0.595                       |
| **OverAll** | **0.627**   | 0.621 | 0.623          |