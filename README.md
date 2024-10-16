# atlas_cluster_scale
Custom cluster tier scaler for MongoDB Atlas

## Configuration
1. Clone or download the repository
```
git clone https://github.com/mhelmstetter/atlas_cluster_scale.git
```
2. Install dependencies
```
pip3 install requests
```

## Launch the Binary

To see all options: 

```
python3 cluster_scale.py --help
```

Scale up cluster tier to M40:

```
python3 cluster_scale.py --projectId 5b8e97b20ffffeeeeddd0000 --username abcxyzz --apiKey 6f1af08d-5a44-41cb-a950-0cc46da2629d --clusterName Cluster3 --scaleUp --clusterTier M40
```

Scale down cluster tier to M30:

```
python3 cluster_scale.py --projectId 5b8e97b20ffffeeeeddd0000 --username abcxyzz --apiKey 6f1af08d-5a44-41cb-a950-0cc46da2629d --clusterName Cluster3 --scaleUp --clusterTier M30
```