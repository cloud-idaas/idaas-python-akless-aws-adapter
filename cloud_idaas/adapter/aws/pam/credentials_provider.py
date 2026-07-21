"""IDaaS PAM AWS credentials provider.

Obtains AWS STS temporary credentials from the PAM Developer API
using an OIDC Token, with automatic caching and expiration-based refresh.
Can be used directly with boto3 via ``get_boto3_session()``.
"""

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from urllib.parse import urlparse

from cloud_idaas.adapter.aws.domain.constants import (
    AWS_ACCESS_KEY_ID,
    AWS_EXPIRATION,
    AWS_SECRET_ACCESS_KEY,
    AWS_SESSION_TOKEN,
    AWS_STS_TOKEN,
    CLOUD_ACCOUNT_ROLE_ACCESS_CREDENTIAL,
    CLOUD_ACCOUNT_ROLE_EXTERNAL_ID,
    OBTAIN_ACCESS_CREDENTIAL_PATH,
)
from cloud_idaas.core import CredentialException, HttpConstants
from cloud_idaas.core.cache import RefreshResult, StaleValueBehavior
from cloud_idaas.core.http.default_http_client import DefaultHttpClient
from cloud_idaas.core.http.http_client import HttpClient
from cloud_idaas.core.http.http_method import HttpMethod
from cloud_idaas.core.http.http_request import HttpRequest
from cloud_idaas.core.implementation.abstract_refreshed_credential_provider import AbstractRefreshedCredentialProvider
from cloud_idaas.core.provider.oidc_token_provider import OidcTokenProvider
from cloud_idaas.core.util.request_util import RequestUtil


@dataclass(frozen=True)
class AwsSessionCredentials:
    """AWS STS session credentials.

    Attributes:
        access_key_id: STS Access Key ID.
        secret_access_key: STS Secret Access Key.
        session_token: STS Session Token.
        expiration: Credential expiration time (UTC), or ``None`` if unknown.
    """

    access_key_id: str
    secret_access_key: str
    session_token: str
    expiration: Optional[datetime] = None


class IDaaSPamAwsCredentialsProvider(AbstractRefreshedCredentialProvider["AwsSessionCredentials"]):
    """IDaaS PAM AWS credentials provider.

    Requests AWS STS temporary credentials from the PAM Developer API using an
    OIDC Token, with automatic caching and expiration-based refresh backed by
    :class:`AbstractRefreshedCredentialProvider`. Can be used directly with all
    AWS service clients (S3, DynamoDB, Lambda, EC2, SQS, etc.) via
    ``resolve_credentials()`` or ``get_boto3_session()``.

    Args:
        developer_api_endpoint: PAM Developer API endpoint.
        idaas_instance_id: IDaaS instance ID.
        oidc_token_provider: OIDC Token provider from Core SDK.
        role_arn: Cloud Account Role ARN.
        connect_timeout: Connection timeout in milliseconds. Defaults to 5000.
        read_timeout: Read timeout in milliseconds. Defaults to 10000.

    Raises:
        ValueError: If any required parameter is empty or None.
    """

    def __init__(
        self,
        *,
        developer_api_endpoint: str,
        idaas_instance_id: str,
        oidc_token_provider: OidcTokenProvider,
        role_arn: str,
        connect_timeout: Optional[int] = None,
        read_timeout: Optional[int] = None,
    ) -> None:
        if not developer_api_endpoint:
            raise ValueError("developer_api_endpoint cannot be empty.")
        if not idaas_instance_id:
            raise ValueError("idaas_instance_id cannot be empty.")
        if oidc_token_provider is None:
            raise ValueError("oidc_token_provider cannot be None.")
        if not role_arn:
            raise ValueError("role_arn cannot be empty.")

        super().__init__(stale_value_behavior=StaleValueBehavior.STRICT)

        self.role_arn: str = role_arn
        self.oidc_token_provider: OidcTokenProvider = oidc_token_provider
        self.connect_timeout: int = connect_timeout if connect_timeout is not None else 5000
        self.read_timeout: int = read_timeout if read_timeout is not None else 10000
        self.idaas_instance_id: str = idaas_instance_id

        self.developer_api_endpoint: str = developer_api_endpoint
        self.developer_api_path: str = OBTAIN_ACCESS_CREDENTIAL_PATH % self.idaas_instance_id

        self._oidc_token: Optional[str] = None
        self._expiration: Optional[datetime] = None

    @property
    def oidc_token(self) -> Optional[str]:
        """The most recently used OIDC Token."""
        return self._oidc_token

    @property
    def expiration(self) -> Optional[datetime]:
        """Expiration time of the current credentials (UTC)."""
        return self._expiration

    @property
    def provider_name(self) -> str:
        """Credentials provider name."""
        return "oidc_role_arn"

    def resolve_credentials(self) -> AwsSessionCredentials:
        """Resolve AWS session credentials.

        Returns cached credentials if they have not expired; otherwise
        triggers an automatic refresh via the PAM Developer API.

        Returns:
            An ``AwsSessionCredentials`` object containing accessKeyId,
            secretAccessKey, sessionToken, and expiration.
        """
        return self.get_cached_result_supplier().get()

    def get_boto3_session(self, **kwargs: Any) -> Any:
        """Create a ``boto3.Session`` with IDaaS PAM credentials.

        Convenience method that creates a new boto3 Session pre-configured
        with the current AWS STS credentials.

        .. note::

            The returned session holds a **static snapshot** of the current
            credentials. It will **not** automatically refresh when the
            credentials expire. For long-running workloads, call this method
            again to obtain a session with fresh credentials.

        Args:
            **kwargs: Additional keyword arguments passed to ``boto3.Session``
                (e.g., ``region_name``, ``profile_name``).

        Returns:
            A ``boto3.Session`` instance.
        """
        # Lazy import: boto3 is only needed when using this convenience method,
        # not when using resolve_credentials() directly.
        import boto3

        creds = self.resolve_credentials()
        return boto3.Session(
            aws_access_key_id=creds.access_key_id,
            aws_secret_access_key=creds.secret_access_key,
            aws_session_token=creds.session_token,
            **kwargs,
        )

    def _refresh_credential(self) -> RefreshResult[AwsSessionCredentials]:
        client = DefaultHttpClient(
            connect_timeout=self.connect_timeout,
            read_timeout=self.read_timeout,
        )
        return self._get_new_session_credentials(client)

    def _get_new_session_credentials(self, client: HttpClient) -> RefreshResult[AwsSessionCredentials]:
        """Obtain new AWS STS temporary credentials from the PAM Developer API."""
        token = self.oidc_token_provider.get_oidc_token()
        self._oidc_token = token

        queries = {CLOUD_ACCOUNT_ROLE_EXTERNAL_ID: self.role_arn}

        parsed = urlparse(self.developer_api_endpoint)
        protocol = parsed.scheme or "https"
        endpoint = parsed.netloc or self.developer_api_endpoint
        url = RequestUtil.compose_url(endpoint, self.developer_api_path, queries, protocol)

        headers = {
            HttpConstants.AUTHORIZATION_HEADER: [f"{HttpConstants.BEARER}{HttpConstants.SPACE}{token}"],
        }

        http_request = HttpRequest.builder().http_method(HttpMethod.GET).url(url).headers(headers).build()

        http_response = client.send(http_request)
        response_body = http_response.body

        try:
            response_map = json.loads(response_body)
        except (json.JSONDecodeError, TypeError) as exc:
            raise CredentialException(
                error_message=f"Error retrieving credentials from PAM result: {response_body}."
            ) from exc

        if not response_map or CLOUD_ACCOUNT_ROLE_ACCESS_CREDENTIAL not in response_map:
            raise CredentialException(error_message=f"Error retrieving credentials from PAM result: {response_body}.")

        access_credential = response_map[CLOUD_ACCOUNT_ROLE_ACCESS_CREDENTIAL]
        if not access_credential or AWS_STS_TOKEN not in access_credential:
            raise CredentialException(error_message=f"Error retrieving credentials from PAM result: {response_body}.")

        sts_token = access_credential[AWS_STS_TOKEN]
        if (
            AWS_ACCESS_KEY_ID not in sts_token
            or AWS_SECRET_ACCESS_KEY not in sts_token
            or AWS_SESSION_TOKEN not in sts_token
            or AWS_EXPIRATION not in sts_token
        ):
            raise CredentialException(error_message=f"Error retrieving credentials from PAM result: {response_body}.")

        expiration_str = sts_token[AWS_EXPIRATION]
        expiration_datetime = RequestUtil.get_utc_date(expiration_str)
        self._expiration = expiration_datetime

        now = datetime.now(timezone.utc)
        expires_in = expiration_datetime - now
        expires_in_secs = max(expires_in.total_seconds(), 0)

        credential = AwsSessionCredentials(
            access_key_id=sts_token[AWS_ACCESS_KEY_ID],
            secret_access_key=sts_token[AWS_SECRET_ACCESS_KEY],
            session_token=sts_token[AWS_SESSION_TOKEN],
            expiration=expiration_datetime,
        )

        # staleTime: 4/5 of lifetime, prefetchTime: 2/3 of lifetime
        # Consistent with IDaaSMachineCredentialProvider in core SDK.
        stale_time = expiration_datetime - timedelta(seconds=expires_in_secs / 5)
        prefetch_time = expiration_datetime - timedelta(seconds=expires_in_secs / 3)

        return RefreshResult(
            value=credential,
            stale_time=stale_time,
            prefetch_time=prefetch_time,
        )
