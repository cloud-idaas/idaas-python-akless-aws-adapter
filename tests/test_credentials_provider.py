"""Tests for IDaaSPamAwsCredentialsProvider."""

import json
from unittest.mock import MagicMock

import pytest

from cloud_idaas.adapter.aws.pam.credentials_provider import IDaaSPamAwsCredentialsProvider
from cloud_idaas.core import CredentialException
from cloud_idaas.core.http.http_response import HttpResponse
from tests.conftest import (
    SAMPLE_ACCESS_KEY_ID,
    SAMPLE_EXPIRATION_DATETIME,
    SAMPLE_EXPIRATION_STR,
    SAMPLE_OIDC_TOKEN,
    SAMPLE_SECRET_ACCESS_KEY,
    SAMPLE_SESSION_TOKEN,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_provider(
    *,
    oidc_token_provider=None,
    developer_api_endpoint="https://pam.example.com",
    idaas_instance_id="test-instance-id",
    role_arn="test-role-external-id",
    connect_timeout=None,
    read_timeout=None,
):
    """Create a provider with sensible defaults for testing."""
    if oidc_token_provider is None:
        oidc_token_provider = MagicMock()
        oidc_token_provider.get_oidc_token.return_value = SAMPLE_OIDC_TOKEN
    return IDaaSPamAwsCredentialsProvider(
        developer_api_endpoint=developer_api_endpoint,
        idaas_instance_id=idaas_instance_id,
        oidc_token_provider=oidc_token_provider,
        role_arn=role_arn,
        connect_timeout=connect_timeout,
        read_timeout=read_timeout,
    )


def _make_http_response(body: str) -> HttpResponse:
    """Create an HttpResponse with the given body."""
    return HttpResponse(status_code=200, body=body)


# ===========================================================================
# __init__ parameter validation tests
# ===========================================================================


class TestCredentialsProviderInit:
    """Tests for __init__ parameter validation and defaults."""

    def test_empty_developer_api_endpoint_raises_value_error(self):
        with pytest.raises(ValueError, match="developer_api_endpoint"):
            _build_provider(developer_api_endpoint="")

    def test_empty_idaas_instance_id_raises_value_error(self):
        with pytest.raises(ValueError, match="idaas_instance_id"):
            _build_provider(idaas_instance_id="")

    def test_none_oidc_token_provider_raises_value_error(self):
        with pytest.raises(ValueError, match="oidc_token_provider"):
            IDaaSPamAwsCredentialsProvider(
                developer_api_endpoint="https://pam.example.com",
                idaas_instance_id="test-instance-id",
                oidc_token_provider=None,
                role_arn="test-role",
            )

    def test_empty_role_arn_raises_value_error(self):
        with pytest.raises(ValueError, match="role_arn"):
            _build_provider(role_arn="")

    def test_default_connect_timeout(self):
        provider = _build_provider()
        assert provider.connect_timeout == 5000

    def test_default_read_timeout(self):
        provider = _build_provider()
        assert provider.read_timeout == 10000

    def test_custom_timeouts(self):
        provider = _build_provider(connect_timeout=3000, read_timeout=6000)
        assert provider.connect_timeout == 3000
        assert provider.read_timeout == 6000

    def test_developer_api_path_contains_instance_id(self):
        provider = _build_provider(idaas_instance_id="my-instance")
        assert "my-instance" in provider.developer_api_path

    def test_endpoint_is_preserved(self):
        provider = _build_provider(developer_api_endpoint="https://pam.example.com")
        assert provider.developer_api_endpoint == "https://pam.example.com"

    def test_endpoint_without_protocol_preserved(self):
        provider = _build_provider(developer_api_endpoint="pam.example.com")
        assert provider.developer_api_endpoint == "pam.example.com"


# ===========================================================================
# _get_new_session_credentials success path tests
# ===========================================================================


class TestCredentialsProviderSuccessPath:
    """Tests for successful AWS STS credential retrieval."""

    def test_successful_credential_retrieval(self, mock_oidc_token_provider, sample_sts_response):
        provider = _build_provider(oidc_token_provider=mock_oidc_token_provider)
        mock_client = MagicMock()
        mock_client.send.return_value = _make_http_response(json.dumps(sample_sts_response))

        result = provider._get_new_session_credentials(mock_client)

        credential = result.value
        assert credential.access_key_id == SAMPLE_ACCESS_KEY_ID
        assert credential.secret_access_key == SAMPLE_SECRET_ACCESS_KEY
        assert credential.session_token == SAMPLE_SESSION_TOKEN

    def test_stale_and_prefetch_times_are_before_expiration(self, mock_oidc_token_provider, sample_sts_response):
        provider = _build_provider(oidc_token_provider=mock_oidc_token_provider)
        mock_client = MagicMock()
        mock_client.send.return_value = _make_http_response(json.dumps(sample_sts_response))

        result = provider._get_new_session_credentials(mock_client)

        # staleTime = expiration - expiresIn/5 (4/5 of lifetime)
        # prefetchTime = expiration - expiresIn/3 (2/3 of lifetime)
        assert result.stale_time < SAMPLE_EXPIRATION_DATETIME
        assert result.prefetch_time < result.stale_time
        assert result.prefetch_time is not None

    def test_oidc_token_is_sent_in_authorization_header(self, mock_oidc_token_provider, sample_sts_response):
        provider = _build_provider(oidc_token_provider=mock_oidc_token_provider)
        mock_client = MagicMock()
        mock_client.send.return_value = _make_http_response(json.dumps(sample_sts_response))

        provider._get_new_session_credentials(mock_client)

        sent_request = mock_client.send.call_args[0][0]
        auth_header = sent_request.headers.get("Authorization", [""])[0]
        assert SAMPLE_OIDC_TOKEN in auth_header
        assert auth_header.startswith("Bearer ")

    def test_request_url_contains_instance_id(self, mock_oidc_token_provider, sample_sts_response):
        provider = _build_provider(
            oidc_token_provider=mock_oidc_token_provider,
            idaas_instance_id="inst-123",
        )
        mock_client = MagicMock()
        mock_client.send.return_value = _make_http_response(json.dumps(sample_sts_response))

        provider._get_new_session_credentials(mock_client)

        sent_request = mock_client.send.call_args[0][0]
        assert "inst-123" in sent_request.url


# ===========================================================================
# _get_new_session_credentials error path tests
# ===========================================================================


class TestCredentialsProviderErrorPaths:
    """Tests for error handling in credential retrieval."""

    def test_non_json_response_raises_credential_exception(self, mock_oidc_token_provider):
        provider = _build_provider(oidc_token_provider=mock_oidc_token_provider)
        mock_client = MagicMock()
        mock_client.send.return_value = _make_http_response("not-valid-json")

        with pytest.raises(CredentialException):
            provider._get_new_session_credentials(mock_client)

    def test_missing_top_level_key_raises_credential_exception(self, mock_oidc_token_provider):
        provider = _build_provider(oidc_token_provider=mock_oidc_token_provider)
        mock_client = MagicMock()
        mock_client.send.return_value = _make_http_response(json.dumps({"someOtherKey": {}}))

        with pytest.raises(CredentialException):
            provider._get_new_session_credentials(mock_client)

    def test_missing_sts_token_key_raises_credential_exception(self, mock_oidc_token_provider):
        provider = _build_provider(oidc_token_provider=mock_oidc_token_provider)
        response_data = {"cloudAccountRoleAccessCredential": {"otherField": "value"}}
        mock_client = MagicMock()
        mock_client.send.return_value = _make_http_response(json.dumps(response_data))

        with pytest.raises(CredentialException):
            provider._get_new_session_credentials(mock_client)

    def test_missing_access_key_id_raises_credential_exception(self, mock_oidc_token_provider):
        provider = _build_provider(oidc_token_provider=mock_oidc_token_provider)
        response_data = {
            "cloudAccountRoleAccessCredential": {
                "awsStsToken": {
                    "secretAccessKey": "secret",
                    "sessionToken": "token",
                    "expiration": SAMPLE_EXPIRATION_STR,
                }
            }
        }
        mock_client = MagicMock()
        mock_client.send.return_value = _make_http_response(json.dumps(response_data))

        with pytest.raises(CredentialException):
            provider._get_new_session_credentials(mock_client)

    def test_missing_secret_access_key_raises_credential_exception(self, mock_oidc_token_provider):
        provider = _build_provider(oidc_token_provider=mock_oidc_token_provider)
        response_data = {
            "cloudAccountRoleAccessCredential": {
                "awsStsToken": {
                    "accessKeyId": "key-id",
                    "sessionToken": "token",
                    "expiration": SAMPLE_EXPIRATION_STR,
                }
            }
        }
        mock_client = MagicMock()
        mock_client.send.return_value = _make_http_response(json.dumps(response_data))

        with pytest.raises(CredentialException):
            provider._get_new_session_credentials(mock_client)

    def test_missing_session_token_raises_credential_exception(self, mock_oidc_token_provider):
        provider = _build_provider(oidc_token_provider=mock_oidc_token_provider)
        response_data = {
            "cloudAccountRoleAccessCredential": {
                "awsStsToken": {
                    "accessKeyId": "key-id",
                    "secretAccessKey": "secret",
                    "expiration": SAMPLE_EXPIRATION_STR,
                }
            }
        }
        mock_client = MagicMock()
        mock_client.send.return_value = _make_http_response(json.dumps(response_data))

        with pytest.raises(CredentialException):
            provider._get_new_session_credentials(mock_client)

    def test_empty_response_body_raises_credential_exception(self, mock_oidc_token_provider):
        provider = _build_provider(oidc_token_provider=mock_oidc_token_provider)
        mock_client = MagicMock()
        mock_client.send.return_value = _make_http_response("")

        with pytest.raises(CredentialException):
            provider._get_new_session_credentials(mock_client)

    def test_null_response_map_raises_credential_exception(self, mock_oidc_token_provider):
        provider = _build_provider(oidc_token_provider=mock_oidc_token_provider)
        mock_client = MagicMock()
        mock_client.send.return_value = _make_http_response("null")

        with pytest.raises(CredentialException):
            provider._get_new_session_credentials(mock_client)


# ===========================================================================
# Provider properties tests
# ===========================================================================


class TestCredentialsProviderProperties:
    """Tests for provider property accessors."""

    def test_provider_name_returns_oidc_role_arn(self):
        provider = _build_provider()
        assert provider.provider_name == "oidc_role_arn"

    def test_oidc_token_updated_after_retrieval(self, mock_oidc_token_provider, sample_sts_response):
        provider = _build_provider(oidc_token_provider=mock_oidc_token_provider)
        mock_client = MagicMock()
        mock_client.send.return_value = _make_http_response(json.dumps(sample_sts_response))

        assert provider.oidc_token is None
        provider._get_new_session_credentials(mock_client)
        assert provider.oidc_token == SAMPLE_OIDC_TOKEN

    def test_expiration_updated_after_retrieval(self, mock_oidc_token_provider, sample_sts_response):
        provider = _build_provider(oidc_token_provider=mock_oidc_token_provider)
        mock_client = MagicMock()
        mock_client.send.return_value = _make_http_response(json.dumps(sample_sts_response))

        assert provider.expiration is None
        provider._get_new_session_credentials(mock_client)
        assert provider.expiration == SAMPLE_EXPIRATION_DATETIME

    def test_close_does_not_raise(self):
        provider = _build_provider()
        provider.close()
