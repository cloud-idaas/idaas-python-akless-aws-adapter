"""Tests for IDaaSPamAwsCredentialsProvider — resolve_credentials, get_boto3_session, close."""

from unittest.mock import MagicMock, patch

from cloud_idaas.adapter.aws.pam.credentials_provider import (
    AwsSessionCredentials,
    IDaaSPamAwsCredentialsProvider,
)
from tests.conftest import (
    SAMPLE_ACCESS_KEY_ID,
    SAMPLE_EXPIRATION_DATETIME,
    SAMPLE_SECRET_ACCESS_KEY,
    SAMPLE_SESSION_TOKEN,
)


def _build_provider_with_mock_credential(credential):
    """Create a provider and inject a mock supplier that returns the given credential."""
    provider = IDaaSPamAwsCredentialsProvider(
        developer_api_endpoint="https://pam.example.com",
        idaas_instance_id="test-instance-id",
        oidc_token_provider=MagicMock(),
        role_arn="test-role-external-id",
    )
    mock_supplier = MagicMock()
    mock_supplier.get.return_value = credential
    provider._cached_result_supplier = mock_supplier
    return provider


class TestResolveCredentials:
    """Tests for resolve_credentials field mapping."""

    def test_fields_are_correctly_mapped(self, mock_credential_model):
        provider = _build_provider_with_mock_credential(mock_credential_model)
        credentials = provider.resolve_credentials()

        assert isinstance(credentials, AwsSessionCredentials)
        assert credentials.access_key_id == SAMPLE_ACCESS_KEY_ID
        assert credentials.secret_access_key == SAMPLE_SECRET_ACCESS_KEY
        assert credentials.session_token == SAMPLE_SESSION_TOKEN
        assert credentials.expiration == SAMPLE_EXPIRATION_DATETIME

    def test_expiration_is_none_when_credential_has_no_expiration(self):
        credential_no_exp = AwsSessionCredentials(
            access_key_id=SAMPLE_ACCESS_KEY_ID,
            secret_access_key=SAMPLE_SECRET_ACCESS_KEY,
            session_token=SAMPLE_SESSION_TOKEN,
        )
        provider = _build_provider_with_mock_credential(credential_no_exp)
        credentials = provider.resolve_credentials()

        assert credentials.expiration is None

    @patch("boto3.Session")
    def test_get_boto3_session_creates_session_with_credentials(self, mock_session_cls, mock_credential_model):
        provider = _build_provider_with_mock_credential(mock_credential_model)
        provider.get_boto3_session(region_name="us-east-1")

        mock_session_cls.assert_called_once_with(
            aws_access_key_id=SAMPLE_ACCESS_KEY_ID,
            aws_secret_access_key=SAMPLE_SECRET_ACCESS_KEY,
            aws_session_token=SAMPLE_SESSION_TOKEN,
            region_name="us-east-1",
        )
