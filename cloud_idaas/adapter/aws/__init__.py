"""IDaaS AWS adapter."""

from cloud_idaas.adapter.aws.pam import (
    AwsSessionCredentials,
    IDaaSPamAklessCredentialFactory,
    IDaaSPamAwsCredentialsProvider,
)

__all__ = [
    "AwsSessionCredentials",
    "IDaaSPamAklessCredentialFactory",
    "IDaaSPamAwsCredentialsProvider",
]

# Version management - keep at the end, skip import sorting
from importlib import metadata  # isort: skip

try:
    __version__ = metadata.version(__package__)
except metadata.PackageNotFoundError:
    __version__ = ""
del metadata

__author__ = "AlibabaCloud IDaaS Team"
