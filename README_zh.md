# cloud-idaas-akless-aws-adapter

[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-Apache%202.0-green.svg)](LICENSE)
[![Development Status](https://img.shields.io/badge/status-Beta-orange)](https://pypi.org/project/cloud-idaas-akless-aws-adapter/)
[![Version](https://img.shields.io/badge/version-0.0.1b0-blue)](https://pypi.org/project/cloud-idaas-akless-aws-adapter/)

简体中文 | [English](README.md)

IDaaS（身份即服务）AKless AWS 适配器的 Python SDK —— 通过 IDaaS PAM（特权访问管理）获取 AWS STS 临时凭证，实现无 AccessKey 访问 AWS 服务。

## 工作原理

```
┌──────────┐    OIDC Token    ┌──────────────┐   AWS STS 临时凭证       ┌─────────────┐
│  IDaaS   │ ──────────────►  │  PAM          │ ──────────────────────► │  AWS        │
│  Core    │                  │  Developer    │   (accessKeyId,         │  服务       │
│  SDK     │                  │  API          │    secretAccessKey,     │  (S3 等)    │
└──────────┘                  └──────────────┘    sessionToken)         └─────────────┘
```

1. IDaaS Core SDK 通过机器对机器认证获取 **OIDC Token**
2. 本适配器将 OIDC Token 发送到 **PAM Developer API** 获取 AWS STS 临时凭证
3. 临时凭证用于 **AWS 服务** 认证（S3、DynamoDB、Lambda、EC2、SQS 等）
4. 凭证在过期前 **自动缓存和刷新**

## 功能特性

- **免 AK 认证**：无需长期 AWS AccessKey，使用 OIDC Token 通过 IDaaS PAM 获取 AWS STS 临时凭证，降低凭证泄露风险
- **AWS SDK 兼容**：提供 `resolve_credentials()` 和 `get_boto3_session()` 方法，可配合所有 AWS 服务客户端使用（S3、DynamoDB、Lambda、EC2、SQS 等）
- **自动凭证刷新**：内置凭证缓存，基于过期时间自动刷新（支持 staleTime 和 prefetchTime 机制），确保凭证无缝轮转
- **简单集成**：工厂类提供一行代码创建凭证提供器，最大程度降低集成成本

## 环境要求

- Python >= 3.9
- 依赖：
  - cloud-idaas-core >= 0.0.5b0
  - boto3 >= 1.26.0（可选，仅 `get_boto3_session()` 需要）

## 安装

```bash
# 基础安装（仅 resolve_credentials()）
pip install cloud-idaas-akless-aws-adapter

# 包含 boto3 支持（用于 get_boto3_session()）
pip install cloud-idaas-akless-aws-adapter[boto3]
```

## 前置准备

本 SDK 依赖 [cloud-idaas-core](https://pypi.org/project/cloud-idaas-core/)，使用本适配器前需要先完成 IDaaS Core SDK 的初始化。

1. 安装并配置 `cloud-idaas-core`，详情参见 [cloud-idaas-core README](https://github.com/aliyunidaas-lab/idaas-python-core-sdk/blob/main/README_zh.md)。

2. 在配置文件中，将 `scope` 设置为 IDaaS PAM 内置 scope：

   ```json
   {
       "scope": "urn:cloud:idaas:pam|.all"
   }
   ```

3. 完成 IDaaS Core SDK 初始化：

   ```python
   from cloud_idaas.core import IDaaSCredentialProviderFactory

   IDaaSCredentialProviderFactory.init()
   ```

## 快速开始

最简单的使用方式是通过 `IDaaSPamAklessCredentialFactory` 工厂类：

```python
from cloud_idaas.core import IDaaSCredentialProviderFactory
from cloud_idaas.adapter.aws.pam import IDaaSPamAklessCredentialFactory

# 1. 初始化 IDaaS Core SDK
IDaaSCredentialProviderFactory.init()

# 2. 创建 AWS 凭证提供器
provider = IDaaSPamAklessCredentialFactory.get_aws_credentials_provider(
    role_arn="your-role-arn"
)

# 3. 创建 boto3 Session 并访问任意 AWS 服务
session = provider.get_boto3_session(region_name="us-east-1")
s3 = session.client("s3")
print(s3.list_buckets())
```

## 使用示例

### Amazon S3

```python
from cloud_idaas.core import IDaaSCredentialProviderFactory
from cloud_idaas.adapter.aws.pam import IDaaSPamAklessCredentialFactory

# 初始化
IDaaSCredentialProviderFactory.init()

# 创建凭证提供器
provider = IDaaSPamAklessCredentialFactory.get_aws_credentials_provider(
    role_arn="your-role-arn"
)

# 创建 boto3 Session 和 S3 客户端
session = provider.get_boto3_session(region_name="us-east-1")
s3 = session.client("s3")

# 列出存储桶
response = s3.list_buckets()
for bucket in response["Buckets"]:
    print(f"  {bucket['Name']} (创建时间: {bucket['CreationDate']})")
```

### Amazon DynamoDB

```python
from cloud_idaas.core import IDaaSCredentialProviderFactory
from cloud_idaas.adapter.aws.pam import IDaaSPamAklessCredentialFactory

# 初始化
IDaaSCredentialProviderFactory.init()

# 创建凭证提供器
provider = IDaaSPamAklessCredentialFactory.get_aws_credentials_provider(
    role_arn="your-role-arn"
)

# 创建 boto3 Session 和 DynamoDB 客户端
session = provider.get_boto3_session(region_name="us-east-1")
dynamodb = session.client("dynamodb")

# 列出表
response = dynamodb.list_tables()
for table in response["TableNames"]:
    print(f"  表名: {table}")
```

### 使用 resolve_credentials() 直接获取凭证

无需 boto3 即可获取原始凭证：

```python
from cloud_idaas.adapter.aws.pam import IDaaSPamAklessCredentialFactory

provider = IDaaSPamAklessCredentialFactory.get_aws_credentials_provider(
    role_arn="your-role-arn"
)

# 获取原始凭证
creds = provider.resolve_credentials()
print(f"AccessKeyId: {creds.access_key_id}")
print(f"SecretAccessKey: {creds.secret_access_key}")
print(f"SessionToken: {creds.session_token}")
print(f"过期时间: {creds.expiration}")
```

### 使用上下文管理器

```python
from cloud_idaas.adapter.aws.pam import IDaaSPamAklessCredentialFactory

with IDaaSPamAklessCredentialFactory.get_aws_credentials_provider(
    role_arn="your-role-arn"
) as provider:
    session = provider.get_boto3_session(region_name="us-east-1")
    s3 = session.client("s3")
    print(s3.list_buckets())
```

### 高级配置

如果需要自定义端点、超时时间或使用自定义的 OIDC Token 提供器，可以直接使用构造函数：

```python
from cloud_idaas.adapter.aws.pam import IDaaSPamAwsCredentialsProvider

provider = IDaaSPamAwsCredentialsProvider(
    developer_api_endpoint="https://your-pam-endpoint.example.com",
    idaas_instance_id="your-instance-id",
    oidc_token_provider=oidc_token_provider,  # 从 Core SDK 获取
    role_arn="your-role-arn",
    connect_timeout=3000,
    read_timeout=8000,
)
```

## API 参考

### IDaaSPamAklessCredentialFactory

工厂类，自动从 Core SDK 读取配置。

| 方法 | 返回类型 | 描述 |
|------|----------|------|
| `get_aws_credentials_provider(role_arn)` | `IDaaSPamAwsCredentialsProvider` | 使用 Core SDK 工厂配置创建凭证提供器 |

### IDaaSPamAwsCredentialsProvider

核心凭证提供器，使用 OIDC Token 从 PAM Developer API 获取 AWS STS 临时凭证，自动缓存和刷新。

#### 构造函数参数

| 参数 | 类型 | 必填 | 默认值 | 描述 |
|------|------|------|--------|------|
| developer_api_endpoint | str | 是 | - | PAM Developer API 端点 |
| idaas_instance_id | str | 是 | - | IDaaS 实例 ID |
| oidc_token_provider | OidcTokenProvider | 是 | - | 来自 Core SDK 的 OIDC Token 提供器 |
| role_arn | str | 是 | - | 云账号角色 ARN |
| connect_timeout | int | 否 | 5000 | 连接超时时间（毫秒） |
| read_timeout | int | 否 | 10000 | 读取超时时间（毫秒） |

#### 方法

| 方法 | 返回类型 | 描述 |
|------|----------|------|
| `resolve_credentials()` | `AwsSessionCredentials` | 返回缓存的凭证（包含 `access_key_id`、`secret_access_key`、`session_token`、`expiration`），过期时自动刷新 |
| `get_boto3_session(**kwargs)` | `boto3.Session` | 使用当前凭证创建 boto3 Session（静态快照，不自动刷新） |
| `close()` | None | 释放资源 |

### AwsSessionCredentials

`resolve_credentials()` 返回的冻结数据类。

| 字段 | 类型 | 描述 |
|------|------|------|
| `access_key_id` | str | AWS STS Access Key ID |
| `secret_access_key` | str | AWS STS Secret Access Key |
| `session_token` | str | AWS STS Session Token |
| `expiration` | Optional[datetime] | 凭证过期时间（UTC） |

## 支持与反馈

- **邮箱**：cloudidaas@list.alibaba-inc.com
- **问题反馈**：如有问题或建议，请提交 Issue

## 许可证

本项目基于 [Apache License 2.0](LICENSE) 许可证授权。
