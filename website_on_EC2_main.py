#!/usr/bin/env python
import os, json
from constructs import Construct
from cdktf import App, TerraformStack
from imports.aws.provider import AwsProvider
from imports.aws.vpc import Vpc
from imports.aws.subnet import Subnet
from imports.aws.internet_gateway import InternetGateway
from imports.aws.route_table import RouteTable, RouteTableRoute
from imports.aws.route_table_association import RouteTableAssociation
from imports.aws.iam_role import IamRole
from imports.aws.instance import Instance
from imports.aws.iam_instance_profile import IamInstanceProfile
from imports.aws.s3_bucket import S3Bucket
from imports.aws.s3_object import S3Object
from imports.aws.security_group import SecurityGroup, SecurityGroupIngress, SecurityGroupEgress

class MyStack(TerraformStack):
    def __init__(self, scope: Construct, id: str):
        super().__init__(scope, id)

        AwsProvider(self, 'AWS', region='us-east-1')
        
        vpc = Vpc(self, "VPC",
            cidr_block = "10.0.0.0/16",
            enable_dns_support = True,
            enable_dns_hostnames = True,
            tags = { "Name": "WebServerVPC" }
        )
        
        public_subnet_1 = Subnet(self, "PublicSubnet01",
            vpc_id = vpc.id,
            cidr_block = "10.0.0.0/17",
            map_public_ip_on_launch = True,
            availability_zone = "us-east-1a",
            tags = { "Name": "PublicSubnet01" }
        )
        
        igw = InternetGateway(self, "InternetGateway",
            vpc_id = vpc.id,
            tags = { "Name": "IGW" }
        )
        
        public_route_table_1 = RouteTable(self, "PublicRouteTable01",
            vpc_id = vpc.id,
            route = [RouteTableRoute(cidr_block = "0.0.0.0/0", gateway_id = igw.id)],
            tags = { "Name": "PublicRouteTable01" }
        )
        
        RouteTableAssociation(self, 'RouteTableAssociation1',
            subnet_id = public_subnet_1.id,
            route_table_id = public_route_table_1.id
        )
        
        
        # public_subnet_2 = Subnet(self, "PublicSubnet02",
        #     vpc_id = vpc.id,
        #     cidr_block = "10.0.128.0/17", 
        #     map_public_ip_on_launch = True,
        #     availability_zone = "us-east-1b",
        #     tags = { "Name": "PublicSubnet02" }
        # )
        
        # public_route_table_2 = RouteTable(self, 'PublicRouteTable02',
        #     vpc_id = vpc.id,
        #     route = [RouteTableRoute(cidr_block = "0.0.0.0/0", gateway_id = igw.id)],
        #     tags = { "Name": public_subnet_2.id }
        # )
        
        # RouteTableAssociation(self, 'RouteTableAssociation2',
        #     subnet_id = public_subnet_2.id,
        #     route_table_id = public_route_table_2.id
        # )
        
        instance_role = IamRole(self, "InstanceRole",
            assume_role_policy = json.dumps({
                "Version": "2012-10-17",
                "Statement": [{
                    "Action": "sts:AssumeRole",
                    "Effect": "Allow",
                    "Principal": { "Service": "ec2.amazonaws.com" },
                }]
            }),
            managed_policy_arns = ["arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore", "arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess"],
            name = "InstanceRole"
        )
        
        s3_bucket = S3Bucket(self, "WebServerBucket", 
            bucket = "my-website-server-bucket-midterm-2",
            force_destroy = True
        )
        
        config_name = "configure.sh"
        config_path = os.path.join(os.path.dirname(__file__), config_name)
        s3_object = S3Object(self, "WebServerConfigObject", 
            bucket = s3_bucket.id,
            key = config_name,
            source = config_path
        )
        
        user_data = """
            #!/bin/bash
            aws s3 cp s3://{s3_bucket.bucket}/{config_name} /tmp/{config_name}
            sudo chmod +x /tmp/{config_name}
            sudo /tmp/{config_name}  
            """.format(s3_bucket=s3_bucket, config_name=config_name)
  
        iam_instance_profile =  IamInstanceProfile(self, "IamInstanceProfile", role = instance_role.name)
        
        security_group = SecurityGroup(self, "SG",
            vpc_id = vpc.id,
            ingress = [SecurityGroupIngress(
                from_port = 80,
                to_port = 80,
                protocol = "tcp",
                cidr_blocks = ["0.0.0.0/0"],
            )],
            egress = [SecurityGroupEgress(
                from_port = 0,
                to_port = 0,
                protocol = "-1",
                cidr_blocks = ["0.0.0.0/0"],
            )],
            tags = { "Name": "WebServerSG" }
        )
    
        instance = Instance(self, "EC2Instance",
            subnet_id = public_subnet_1.id,
            instance_type = "t2.micro",
            ami = "ami-0bef12ee7bc073414",
            iam_instance_profile = iam_instance_profile.name,
            user_data = user_data,
            vpc_security_group_ids = [security_group.id],
            tags = { "Name": "WebInstance" },
            depends_on = [s3_object]
        )
        
app = App()
MyStack(app, "midterm-EC2")

app.synth()

