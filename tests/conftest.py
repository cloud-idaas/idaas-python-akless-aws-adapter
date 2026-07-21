"""Shared test fixtures for the IDaaS AKless AWS adapter tests."""

import json
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from cloud_idaas.adapter.aws.pam.credentials_provider import AwsSessionCredentials

SAMPLE_ACCESS_KEY_ID = "test-access-key-id"
SAMPLE_SECRET_ACCESS_KEY = "test-secret-access-key"
SAMPLE_SESSION_TOKEN = "test-session-token"
SAMPLE_EXPIRATION_STR = "2099-12-31T23:59:59Z"
SAMPLE_EXPIRATION_DATETIME = datetime(2099, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
SAMPLE_OIDC_TOKEN = "test-oidc-token-value"


@pytest.fixture
def mock_credential_model():
    """A pre-built AwsSessionCredentials with sample AWS STS credential values."""
    return AwsSessionCredentials(
        access_key_id=SAMPLE_ACCESS_KEY_ID,
        secret_access_key=SAMPLE_SECRET_ACCESS_KEY,
        session_token=SAMPLE_SESSION_TOKEN,
        expiration=SAMPLE_EXPIRATION_DATETIME,
    )


@pytest.fixture
def mock_oidc_token_provider():
    """A mock OidcTokenProvider that returns a fixed OIDC token."""
    provider = MagicMock()
    provider.get_oidc_token.return_value = SAMPLE_OIDC_TOKEN
    return provider


@pytest.fixture
def sample_sts_response():
    """A sample successful PAM API response dictionary for AWS STS."""
    return {
        "cloudAccountRoleAccessCredential": {
            "awsStsToken": {
                "accessKeyId": SAMPLE_ACCESS_KEY_ID,
                "secretAccessKey": SAMPLE_SECRET_ACCESS_KEY,
                "sessionToken": SAMPLE_SESSION_TOKEN,
                "expiration": SAMPLE_EXPIRATION_STR,
            }
        }
    }


@pytest.fixture
def sample_sts_response_body(sample_sts_response):
    """The sample PAM API response serialized as a JSON string."""
    return json.dumps(sample_sts_response)
