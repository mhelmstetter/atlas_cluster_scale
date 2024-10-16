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
Note that `scaleUp` will also *unset* the "Allow cluster to be scaled down" option, such
that if `scaleUp` is called well in advance of expected load, we can ensure that auto-scaling will not
lower the tier.

Scale down cluster tier to M30:

```
python3 cluster_scale.py --projectId 5b8e97b20ffffeeeeddd0000 --username abcxyzz --apiKey 6f1af08d-5a44-41cb-a950-0cc46da2629d --clusterName Cluster3 --scaleDown --clusterTier M30
```

Note that `scaleDown` will enable the "Allow cluster to be scaled down" option, to allow auto-scaling to
scale down as necessary to the min tier configured.
If `scaleDown` is called with `clusterTier` less than the current minimum tier, the minimum tier will be lowered to the specified `clusterTier`.