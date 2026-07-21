"""
Sample: Use IDaaS PAM AKless authentication to access Amazon S3.

Prerequisites:
1. Configure cloud-idaas-core (config file with scope "urn:cloud:idaas:pam|.all")
2. Ensure the PAM role has AWS S3 permissions
3. pip install cloud-idaas-akless-aws-adapter
"""

from cloud_idaas.adapter.aws.pam import IDaaSPamAklessCredentialFactory
from cloud_idaas.core import IDaaSCredentialProviderFactory


def main():
    # 1. Initialize IDaaS Core SDK
    IDaaSCredentialProviderFactory.init()

    # 2. Create AWS credentials provider via factory
    #    role_arn: the Cloud Account Role ARN configured in IDaaS PAM
    provider = IDaaSPamAklessCredentialFactory.get_aws_credentials_provider(role_arn="your-role-arn")

    # 3. Create a boto3 session with IDaaS credentials
    session = provider.get_boto3_session(region_name="us-east-1")

    # 4. Create S3 client and list buckets
    s3 = session.client("s3")
    print("=== S3 Buckets ===")
    response = s3.list_buckets()
    for bucket in response["Buckets"]:
        print(f"  {bucket['Name']} (created: {bucket['CreationDate']})")
    print(f"Total: {len(response['Buckets'])} buckets")

    # 5. Clean up
    provider.close()


if __name__ == "__main__":
    main()
