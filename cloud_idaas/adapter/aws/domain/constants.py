"""IDaaS AKless AWS Adapter constants.

Defines credential field keys and PAM Developer API request constants
for AWS STS credential retrieval.
"""

# --- Credential Constants ---
# JSON response credential field paths

CLOUD_ACCOUNT_ROLE_ACCESS_CREDENTIAL = "cloudAccountRoleAccessCredential"
"""Top-level key for the cloud account role access credential in the response JSON."""

AWS_STS_TOKEN = "awsStsToken"
"""Key for the AWS STS Token object within the credential structure."""

AWS_ACCESS_KEY_ID = "accessKeyId"
"""Key for the Access Key ID in the STS Token."""

AWS_SECRET_ACCESS_KEY = "secretAccessKey"
"""Key for the Secret Access Key in the STS Token."""

AWS_SESSION_TOKEN = "sessionToken"
"""Key for the Session Token in the STS Token."""

AWS_EXPIRATION = "expiration"
"""Key for the expiration time in the STS Token."""

# --- Request Constants ---
# PAM Developer API request constants

OBTAIN_ACCESS_CREDENTIAL_PATH = "/v2/%s/cloudAccountRoles/_/actions/obtainAccessCredential"
"""API path template for obtaining access credentials. ``%s`` is the IDaaS instance ID."""

CLOUD_ACCOUNT_ROLE_EXTERNAL_ID = "cloudAccountRoleExternalId"
"""Query parameter key for the role external ID."""
