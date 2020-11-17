#!/usr/bin/env bash

# (C) Oliver Schoenborn 
#
# Publish the disk usage below a certain path on an EC2 instance
# Uses `du ... path` and `aws cloudwatch put-metric-data`
#
# Requires that the ec2 have following policy
# {
#     "Version": "2012-10-17",
#     "Statement": [
#         {
#             "Action": [
#                 "cloudwatch:PutMetricData"
#             ],
#             "Effect": "Allow",
#             "Resource": "*"
#         }
#     ]
# }
#
# First arg must be the CloudWatch namespace to push metrics to; 
# Second arg must be the path to measure from. 
#
# Example: $0 MyNamespace /var/log/nginx

set -o errexit

if [[ ! -f ec2-metadata ]]; then 
  echo "Downloading ec2-metadata"
  wget http://s3.amazonaws.com/ec2metadata/ec2-metadata
  chmod u+x ec2-metadata
fi

namespace=$1
folder_path=$2
if [[ -z $folder_path ]]; then
  echo "Specify folder path"
  exit 1
fi

PATH=/usr/local/bin:$PATH
space=$(du --bytes ${folder_path} | cut -f 1)
echo "$(date -Isec) - Disk space used by ${folder_path}: ${space} bytes"
iid=$(./ec2-metadata --instance-id | cut -f 2 -d " ")

if aws cloudwatch put-metric-data --namespace ${namespace} --metric-name DiskSpaceUsed \
     --unit Bytes --value ${space} --dimensions Path="${folder_path}",InstanceId=${iid}
then
  echo "# Metric pushed to CloudWatch, check https://console.aws.amazon.com/cloudwatch -> ${namespace} -> Path,InstanceId"
  echo "# -------"
else
  echo "# ERROR could not push to CloudWatch: $?"
fi
