"""Tests for IDaaSPamAklessCredentialFactory."""

from unittest.mock import MagicMock, patch

from cloud_idaas.adapter.aws.pam.credential_factory import IDaaSPamAklessCredentialFactory
from cloud_idaas.adapter.aws.pam.credentials_provider import IDaaSPamAwsCredentialsProvider

FACTORY_MODULE = "cloud_idaas.adapter.aws.pam.credential_factory"


def _patch_factory_dependencies():
    """Patch IDaaSCredentialProviderFactory static methods used by the factory."""
    return [
        patch(
            f"{FACTORY_MODULE}.IDaaSCredentialProviderFactory.get_idaas_credential_provider",
            return_value=MagicMock(),
        ),
        patch(
            f"{FACTORY_MODULE}.IDaaSCredentialProviderFactory.get_developer_api_endpoint",
            return_value="https://pam.example.com",
        ),
        patch(
            f"{FACTORY_MODULE}.IDaaSCredentialProviderFactory.get_idaas_instance_id",
            return_value="test-instance-id",
        ),
    ]


class TestCredentialFactory:
    """Tests for factory method return types."""

    def test_get_aws_credentials_provider_returns_correct_type(self):
        patches = _patch_factory_dependencies()
        for patcher in patches:
            patcher.start()
        try:
            provider = IDaaSPamAklessCredentialFactory.get_aws_credentials_provider(role_arn="test-role-arn")
            assert isinstance(provider, IDaaSPamAwsCredentialsProvider)
        finally:
            for patcher in patches:
                patcher.stop()
