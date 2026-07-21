"""IDaaS PAM AKless credential factory for AWS.

Provides a convenient static factory method to create AWS credentials providers
with a single call.
"""

from cloud_idaas.adapter.aws.pam.credentials_provider import IDaaSPamAwsCredentialsProvider
from cloud_idaas.core.factory.idaas_credential_provider_factory import IDaaSCredentialProviderFactory


class IDaaSPamAklessCredentialFactory:
    """IDaaS PAM AKless credential factory for AWS.

    Provides a convenient static factory method that automatically obtains the
    OIDC Token Provider, Developer API Endpoint, and IDaaS Instance ID from
    ``IDaaSCredentialProviderFactory``, enabling one-line creation of
    AWS credentials providers.
    """

    @staticmethod
    def get_aws_credentials_provider(role_arn: str) -> IDaaSPamAwsCredentialsProvider:
        """Create an AWS credentials provider using Core SDK Factory configuration.

        Args:
            role_arn: Cloud Account Role ARN.

        Returns:
            An ``IDaaSPamAwsCredentialsProvider`` instance.
        """
        return IDaaSPamAwsCredentialsProvider(
            oidc_token_provider=IDaaSCredentialProviderFactory.get_idaas_credential_provider(),
            developer_api_endpoint=IDaaSCredentialProviderFactory.get_developer_api_endpoint(),
            idaas_instance_id=IDaaSCredentialProviderFactory.get_idaas_instance_id(),
            role_arn=role_arn,
        )
