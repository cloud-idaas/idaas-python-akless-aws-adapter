"""IDaaS PAM AWS credentials adapter."""

from cloud_idaas.adapter.aws.pam.credential_factory import IDaaSPamAklessCredentialFactory
from cloud_idaas.adapter.aws.pam.credentials_provider import (
    AwsSessionCredentials,
    IDaaSPamAwsCredentialsProvider,
)

__all__ = [
    "AwsSessionCredentials",
    "IDaaSPamAklessCredentialFactory",
    "IDaaSPamAwsCredentialsProvider",
]
