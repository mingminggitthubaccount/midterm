#!/usr/bin/env python
import os, json, mimetypes
from constructs import Construct
from cdktf import App, TerraformStack
from imports.aws.provider import AwsProvider
from imports.aws.s3_bucket import S3Bucket, S3BucketWebsite
from imports.aws.s3_bucket_acl import S3BucketAcl
from imports.aws.s3_bucket_ownership_controls import S3BucketOwnershipControls, S3BucketOwnershipControlsRule
from imports.aws.s3_bucket_policy import S3BucketPolicy
from imports.aws.s3_bucket_public_access_block import S3BucketPublicAccessBlock
from imports.aws.s3_bucket_versioning import S3BucketVersioningA, S3BucketVersioningVersioningConfiguration
from imports.aws.s3_bucket_website_configuration import S3BucketWebsiteConfiguration, S3BucketWebsiteConfigurationIndexDocument
from imports.aws.s3_object import S3Object

class MyStack(TerraformStack):
    def __init__(self, scope: Construct, id: str):
        super().__init__(scope, id)
        
        AwsProvider(self, 'AWS', region='us-east-1')
        
        s3_bucket = S3Bucket(self, "MyWebsiteBucket", 
            bucket = "my-unique-bucket-name-for-website",
            force_destroy = True
        )
        
        S3BucketWebsiteConfiguration(self, "MyWebsiteConfiguration",
            bucket = s3_bucket.id,
            index_document = S3BucketWebsiteConfigurationIndexDocument(suffix = "index.html")
        ) 
        
        s3_versioning = S3BucketVersioningA(self, "MyWebsiteVersioning",
            bucket = s3_bucket.id,
            versioning_configuration = S3BucketVersioningVersioningConfiguration(status = "Enabled")
        )
        
        s3_bucket_public_access_block = S3BucketPublicAccessBlock(self, "MyWebsiteBucketPublicAccessBlock",
            bucket = s3_bucket.id,
            block_public_acls = True,
            ignore_public_acls = True,
            block_public_policy = False,
            restrict_public_buckets = False,
        )
        
        s3_bucket_ownership_controls = S3BucketOwnershipControls(self, "MyWebsiteBucketOwnershipControls",
            bucket = s3_bucket.id,
            rule = S3BucketOwnershipControlsRule(object_ownership = "BucketOwnerPreferred")
        )
        
        s3_acl = S3BucketAcl(self, "MyWebsiteBucketAcl",
            bucket = s3_bucket.id,
            depends_on = [s3_bucket_ownership_controls, s3_bucket_public_access_block, s3_versioning],
            acl = "private",
        )
        
        s3_policy = S3BucketPolicy(self, "MyWebsiteBucketPolicy",
            bucket = s3_bucket.id,
            depends_on = [s3_acl],
            policy = json.dumps({
                "Version": "2012-10-17",
                "Statement": [{
                    "Action": "s3:GetObject",
                    "Effect": "Allow",
                    "Resource": [ "arn:aws:s3:::my-unique-bucket-name-for-website/*" ],
                    "Principal": "*"
                }]
            })
        )
        
        directory_path = os.path.abspath("static-website")
        for root, dirs, files in os.walk(directory_path):
            for file in files:
                file_path = os.path.join(root, file)
                s3_path = os.path.relpath(file_path, start = directory_path)
                content_type, _ = mimetypes.guess_type(file_path)
                S3Object(self, s3_path,
                    bucket = s3_bucket.id,
                    depends_on = [s3_policy],
                    key = s3_path,
                    source = file_path,
                    content_type = content_type,
                )
    
app = App()
MyStack(app, "Midterm")

app.synth()
