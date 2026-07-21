# cloud-idaas-akless-aws-adapter

[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-Apache%202.0-green.svg)](LICENSE)
[![Development Status](https://img.shields.io/badge/status-Beta-orange)](https://pypi.org/project/cloud-idaas-akless-aws-adapter/)
[![Version](https://img.shields.io/badge/version-0.0.1b0-blue)](https://pypi.org/project/cloud-idaas-akless-aws-adapter/)

[简体中文](README_zh.md) | English

Python SDK for IDaaS (Identity as a Service) AKless AWS Adapter — Enables AK-free authentication for AWS services using IDaaS PAM (Privileged Access Management) to obtain AWS STS temporary credentials.

## How It Works

```
┌──────────┐    OIDC Token    ┌──────────────┐   AWS STS Credentials   ┌─────────────┐
│  IDaaS   │ ──────────────►  │  PAM          │ ──────────────────────► │  AWS        │
│  Core    │                  │  Developer    │   (accessKeyId,         │  Service    │
│  SDK     │                  │  API          │    secretAccessKey,     │  (S3, etc.) │
└──────────┘                  └──────────────┘    sessionToken)         └─────────────┘
```

1. The IDaaS Core SDK obtains an **OIDC Token** via machine-to-machine authentication
2. This adapter sends the OIDC Token to the **PAM Developer API** to obtain AWS STS temporary credentials
3. The temporary credentials are used to authenticate with **AWS services** (S3, DynamoDB, Lambda, EC2, SQS, etc.)
4. Credentials are **automatically cached and refreshed** before expiration

## Features

- **AK-free Authentication**: Eliminates the need for long-term AWS AccessKey, uses OIDC Token to obtain AWS STS temporary credentials via IDaaS PAM, reducing the risk of credential leakage
- **AWS SDK Compatible**: Provides `resolve_credentials()` and `get_boto3_session()`, can be used with all AWS service clients (S3, DynamoDB, Lambda, EC2, SQS, etc.)
- **Automatic Credential Refresh**: Built-in credential caching with stale-time and prefetch-time based automatic refresh, ensuring seamless credential rotation
- **Simple Integration**: Factory class provides one-line creation of credential providers, minimizing integration effort

## Requirements

- Python >= 3.9
- Dependencies:
  - cloud-idaas-core >= 0.0.5b0
  - boto3 >= 1.26.0 (optional, required only for `get_boto3_session()`)

## Installation

```bash
# Basic installation (resolve_credentials() only)
pip install cloud-idaas-akless-aws-adapter

# With boto3 support (for get_boto3_session())
pip install cloud-idaas-akless-aws-adapter[boto3]
```

## Prerequisites

This SDK depends on [cloud-idaas-core](https://pypi.org/project/cloud-idaas-core/). You need to complete the IDaaS Core SDK initialization before using this adapter.

1. Install and configure `cloud-idaas-core`, refer to [cloud-idaas-core README](https://github.com/aliyunidaas-lab/idaas-python-core-sdk/blob/main/README.md) for details.

2. In the configuration file, set the `scope` to the IDaaS built-in scope for PAM:

   ```json
   {
       "scope": "urn:cloud:idaas:pam|.all"
   }
   ```

3. Complete the IDaaS Core SDK initialization:

   ```python
   from cloud_idaas.core import IDaaSCredentialProviderFactory

   IDaaSCredentialProviderFactory.init()
   ```

## Quick Start

The simplest way to use this SDK is through the `IDaaSPamAklessCredentialFactory` factory class:

```python
from cloud_idaas.core import IDaaSCredentialProviderFactory
from cloud_idaas.adapter.aws.pam import IDaaSPamAklessCredentialFactory

# 1. Initialize IDaaS Core SDK
IDaaSCredentialProviderFactory.init()

# 2. Create an AWS credentials provider
provider = IDaaSPamAklessCredentialFactory.get_aws_credentials_provider(
    role_arn="your-role-arn"
)

# 3. Create a boto3 session and use any AWS service
session = provider.get_boto3_session(region_name="us-east-1")
s3 = session.client("s3")
print(s3.list_buckets())
```

## Usage Examples

### Amazon S3

```python
from cloud_idaas.core import IDaaSCredentialProviderFactory
from cloud_idaas.adapter.aws.pam import IDaaSPamAklessCredentialFactory

# Initialize
IDaaSCredentialProviderFactory.init()

# Create credentials provider
provider = IDaaSPamAklessCredentialFactory.get_aws_credentials_provider(
    role_arn="your-role-arn"
)

# Create boto3 session and S3 client
session = provider.get_boto3_session(region_name="us-east-1")
s3 = session.client("s3")

# List buckets
response = s3.list_buckets()
for bucket in response["Buckets"]:
    print(f"  {bucket['Name']} (created: {bucket['CreationDate']})")
```

### Amazon DynamoDB

```python
from cloud_idaas.core import IDaaSCredentialProviderFactory
from cloud_idaas.adapter.aws.pam import IDaaSPamAklessCredentialFactory

# Initialize
IDaaSCredentialProviderFactory.init()

# Create credentials provider
provider = IDaaSPamAklessCredentialFactory.get_aws_credentials_provider(
    role_arn="your-role-arn"
)

# Create boto3 session and DynamoDB client
session = provider.get_boto3_session(region_name="us-east-1")
dynamodb = session.client("dynamodb")

# List tables
response = dynamodb.list_tables()
for table in response["TableNames"]:
    print(f"  Table: {table}")
```

### Using resolve_credentials() Directly

For scenarios where you need raw credentials without boto3:

```python
from cloud_idaas.adapter.aws.pam import IDaaSPamAklessCredentialFactory

provider = IDaaSPamAklessCredentialFactory.get_aws_credentials_provider(
    role_arn="your-role-arn"
)

# Get raw credentials
creds = provider.resolve_credentials()
print(f"AccessKeyId: {creds.access_key_id}")
print(f"SecretAccessKey: {creds.secret_access_key}")
print(f"SessionToken: {creds.session_token}")
print(f"Expiration: {creds.expiration}")
```

### Using Context Manager

```python
from cloud_idaas.adapter.aws.pam import IDaaSPamAklessCredentialFactory

with IDaaSPamAklessCredentialFactory.get_aws_credentials_provider(
    role_arn="your-role-arn"
) as provider:
    session = provider.get_boto3_session(region_name="us-east-1")
    s3 = session.client("s3")
    print(s3.list_buckets())
```

### Advanced Configuration

If you need to customize the endpoint, timeouts, or provide your own OIDC Token provider, use the constructor directly:

```python
from cloud_idaas.adapter.aws.pam import IDaaSPamAwsCredentialsProvider

provider = IDaaSPamAwsCredentialsProvider(
    developer_api_endpoint="https://your-pam-endpoint.example.com",
    idaas_instance_id="your-instance-id",
    oidc_token_provider=oidc_token_provider,  # from Core SDK
    role_arn="your-role-arn",
    connect_timeout=3000,
    read_timeout=8000,
)
```

## API Reference

### IDaaSPamAklessCredentialFactory

Factory class providing a static method to create credential providers. Automatically reads configuration from the Core SDK.

| Method | Return Type | Description |
|--------|-------------|-------------|
| `get_aws_credentials_provider(role_arn)` | `IDaaSPamAwsCredentialsProvider` | Creates a provider using Core SDK Factory configuration |

### IDaaSPamAwsCredentialsProvider

Core credentials provider. Obtains AWS STS temporary credentials from the PAM Developer API using an OIDC Token, with automatic caching and refresh.

#### Constructor Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| developer_api_endpoint | str | Yes | - | PAM Developer API endpoint |
| idaas_instance_id | str | Yes | - | IDaaS instance ID |
| oidc_token_provider | OidcTokenProvider | Yes | - | OIDC Token provider from Core SDK |
| role_arn | str | Yes | - | Cloud Account Role ARN |
| connect_timeout | int | No | 5000 | Connection timeout in milliseconds |
| read_timeout | int | No | 10000 | Read timeout in milliseconds |

#### Methods

| Method | Return Type | Description |
|--------|-------------|-------------|
| `resolve_credentials()` | `AwsSessionCredentials` | Returns cached credentials (includes `access_key_id`, `secret_access_key`, `session_token`, `expiration`), auto-refreshes if expired |
| `get_boto3_session(**kwargs)` | `boto3.Session` | Creates a boto3 session with current credentials (static snapshot, does not auto-refresh) |
| `close()` | None | Releases resources |

### AwsSessionCredentials

Frozen dataclass returned by `resolve_credentials()`.

| Field | Type | Description |
|-------|------|-------------|
| `access_key_id` | str | AWS STS Access Key ID |
| `secret_access_key` | str | AWS STS Secret Access Key |
| `session_token` | str | AWS STS Session Token |
| `expiration` | Optional[datetime] | Credential expiration time (UTC) |

## Support and Feedback

- **Email**: cloudidaas@list.alibaba-inc.com
- **Issues**: Please submit an Issue for questions or suggestions

## License

This project is licensed under the [Apache License 2.0](LICENSE).
