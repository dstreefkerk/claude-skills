# Authentication Types Reference

## CCF Source-File Placeholders vs Deployed ARM Parameters

There are two distinct quoting contexts for credential placeholders, and confusing them
causes silent schema-validation failures:

| Context | Placeholder syntax | Example |
|---------|--------------------|---------|
| **CCF source file** (`polling_config.json` used by the connector builder / `Test Connector` tooling, before ARM wrapping) | `{{placeholder}}` — and `ApiKey` MUST use the EXACT literal `"{{apiKey}}"` | `"ApiKey": "{{apiKey}}"` |
| **Deployed ARM template** (`mainTemplate.json` for content-hub deployment) | `[[parameters('name')]` (double bracket inside `ResourcesDataConnector` nested templates) | `"ApiKey": "[[parameters('apikey')]"` |

**Critical rule for CCF source files:** the `APIKey.ApiKey` value must be the literal string
`"{{apiKey}}"`. Do NOT substitute vendor-specific names like `"{{bearerToken}}"`,
`"{{githubToken}}"`, or `"{{1passwordToken}}"` — these will fail schema validation in the
connector tester and connector builder. Vendor-friendly UI labels go in the
`instructionSteps` Textbox `label`, not in the placeholder name.

For OTHER credentials the placeholder name is conventional (e.g. `{{username}}`,
`{{password}}`, `{{clientId}}`, `{{clientSecret}}`, `{{code}}`). The textbox `name` in
`instructionSteps` must match the placeholder exactly so parameter-consistency validation
passes — see `ui-definitions.md`.

## Public / unauthenticated APIs

**CCF does not support unauthenticated connectors.** Every CCF polling configuration must
declare `properties.auth` with a type of `Basic`, `APIKey`, `OAuth2`, or `JwtToken`. If a
vendor API truly has no authentication, the user cannot build a CCF connector for it
without putting a proxy in front that adds an auth header.

## Auth method must come from API docs

When the user proposes an auth method that contradicts the vendor documentation, follow
the documentation. APIs frequently support multiple auth methods (Basic + OAuth2, APIKey
with multiple header conventions); the choice is between *documented* options. User input
selects from documented options — it does not override them.

## Basic Auth
```json
"auth": {
    "type": "Basic",
    "UserName": "[[parameters('username')]",
    "Password": "[[parameters('password')]"
}
```
| Field | Required | Type |
|-------|----------|------|
| UserName | Yes | string |
| Password | Yes | string |

## APIKey Auth
```json
"auth": {
    "type": "APIKey",
    "ApiKey": "[[parameters('apikey')]",
    "ApiKeyName": "X-Auth-Header",
    "ApiKeyIdentifier": "Bearer",
    "IsApiKeyInPostPayload": false
}
```
| Field | Required | Type | Default | Description |
|-------|----------|------|---------|-------------|
| ApiKey | Yes | string | — | The secret key value |
| ApiKeyName | No | string | `Authorization` | Header name for the key |
| ApiKeyIdentifier | No | string | `token` | Prefix before the key value |
| IsApiKeyInPostPayload | No | boolean | false | Send in POST body instead of header |

### Result Header Examples
- Default: `Authorization: token {apikey}`
- With `ApiKeyName: "X-Auth"`, `ApiKeyIdentifier: "Bearer"`: `X-Auth: Bearer {apikey}`
- With `ApiKeyName: ""`: `Authorization: {apikey}` (no identifier prefix)

### ApiKeyIdentifier — match the vendor's exact casing

The `ApiKeyIdentifier` is the prefix before the token value in the Authorization header:
`Authorization: {ApiKeyIdentifier} {ApiKey}`. Use the EXACT identifier from the API docs —
do not assume `Bearer` is always correct.

| Documentation says               | ApiKeyIdentifier | Result header                           |
|----------------------------------|------------------|-----------------------------------------|
| `Authorization: Bearer <token>`  | `"Bearer"`       | `Authorization: Bearer abc123`          |
| `Authorization: token <token>`   | `"token"`        | `Authorization: token abc123`           |
| `Authorization: Token <token>`   | `"Token"`        | `Authorization: Token abc123`           |
| `Authorization: SSWS <token>`    | `"SSWS"`         | `Authorization: SSWS abc123`            |
| `X-API-Key: <token>` (no prefix) | `""`             | Uses `ApiKeyName: "X-API-Key"` directly |

### Handling APIs Requiring Multiple Auth Headers
CCP's APIKey type handles only one header natively. For a second auth header, pass it as a custom request header:
```json
"request": {
    "headers": {
        "X-Second-Auth": "[[parameters('secondKey')]"
    }
}
```

## OAuth2 Auth

### Client Credentials Grant
```json
"auth": {
    "type": "OAuth2",
    "ClientId": "[[parameters('appId')]",
    "ClientSecret": "[[parameters('appSecret')]",
    "GrantType": "client_credentials",
    "TokenEndpoint": "https://login.microsoftonline.com/{tenantId}/oauth2/v2.0/token",
    "TokenEndpointHeaders": {
        "Content-Type": "application/x-www-form-urlencoded"
    },
    "TokenEndpointQueryParameters": {},
    "Scope": "https://api.example.com/.default"
}
```

### Authorization Code Grant
```json
"auth": {
    "type": "OAuth2",
    "ClientId": "[[parameters('appId')]",
    "ClientSecret": "[[parameters('appSecret')]",
    "GrantType": "authorization_code",
    "AuthorizationCode": "[[parameters('authCode')]",
    "TokenEndpoint": "https://login.microsoftonline.com/{tenantId}/oauth2/v2.0/token",
    "AuthorizationEndpoint": "https://login.microsoftonline.com/{tenantId}/oauth2/v2.0/authorize",
    "AuthorizationEndpointQueryParameters": { "prompt": "consent" },
    "RedirectUri": "https://portal.azure.com/TokenAuthorize/ExtensionName/Microsoft_Azure_Security_Insights",
    "Scope": "openid offline_access {scopes}",
    "TokenEndpointHeaders": {
        "Accept": "application/json",
        "Content-Type": "application/x-www-form-urlencoded"
    }
}
```

### OAuth2 Properties
| Field | Required | Type | Description |
|-------|----------|------|-------------|
| ClientId | Yes | string | App/client ID |
| ClientSecret | Yes | string | Client secret |
| GrantType | Yes | string | `authorization_code` or `client_credentials` |
| AuthorizationCode | Yes (auth_code) | string | Code from auth server |
| Scope | Yes (auth_code) | string | Space-separated scopes |
| RedirectUri | Yes (auth_code) | string | Must be the portal URL above |
| TokenEndpoint | Yes | string | Token exchange URL |
| AuthorizationEndpoint | Yes (auth_code) | string | User consent URL |
| TokenEndpointHeaders | No | object | Custom headers for token request |
| TokenEndpointQueryParameters | No | object | Custom query params for token request |
| AuthorizationEndpointHeaders | No | object | Custom headers for auth request |
| AuthorizationEndpointQueryParameters | No | object | Custom query params for auth request |

**Limitation:** OAuth2 does NOT support client certificate credentials.

## JWT Token Auth

### Credentials in POST Body (default)
```json
"auth": {
    "type": "JwtToken",
    "userName": { "key": "username", "value": "[[parameters('UserName')]" },
    "password": { "key": "password", "value": "[[parameters('Password')]" },
    "TokenEndpoint": "https://api.example.com/token",
    "IsJsonRequest": true,
    "JwtTokenJsonPath": "$.access_token"
}
```

### Credentials in Headers (Basic Auth style)
```json
"auth": {
    "type": "JwtToken",
    "userName": { "key": "client_id", "value": "[[parameters('ClientId')]" },
    "password": { "key": "client_secret", "value": "[[parameters('ClientSecret')]" },
    "TokenEndpoint": "https://api.example.com/oauth/token",
    "IsCredentialsInHeaders": true,
    "IsJsonRequest": true,
    "JwtTokenJsonPath": "$.access_token",
    "RequestTimeoutInSeconds": 30
}
```

### User Token Flow
```json
"auth": {
    "type": "JwtToken",
    "UserToken": "[[parameters('userToken')]",
    "UserTokenPrepend": "Bearer",
    "TokenEndpoint": "https://api.example.com/oauth/token",
    "TokenEndpointHttpMethod": "GET",
    "NoAccessTokenPrepend": true,
    "JwtTokenJsonPath": "$.systemToken"
}
```

### JWT Properties
| Field | Required | Type | Default | Description |
|-------|----------|------|---------|-------------|
| type | Yes | string | — | Must be `JwtToken` |
| userName | Yes* | object | — | `{key, value}` pair (*unless userToken used) |
| password | Yes* | object | — | `{key, value}` pair (*unless userToken used) |
| userToken | Yes* | string | — | Pre-existing token (*unless userName used) |
| UserTokenPrepend | No | string | — | Text before token (e.g., `Bearer`) |
| NoAccessTokenPrepend | No | boolean | false | Don't prepend anything to token |
| TokenEndpoint | Yes | string | — | URL to obtain JWT |
| TokenEndpointHttpMethod | No | string | POST | `Get` or `Post` |
| IsCredentialsInHeaders | No | boolean | false | Basic Auth header vs POST body |
| IsJsonRequest | No | boolean | false | JSON vs form-encoded body |
| JwtTokenJsonPath | No | string | — | JSONPath to extract token (e.g., `$.access_token`) |
| JwtTokenInResponseHeader | No | boolean | false | Extract from header vs body |
| JwtTokenHeaderName | No | string | `Authorization` | Header name when token in header |
| JwtTokenIdentifier | No | string | — | Identifier to extract JWT from prefixed string |
| QueryParameters | No | object | — | Custom query params for token endpoint |
| Headers | No | object | — | Custom headers for token endpoint |
| RequestTimeoutInSeconds | No | integer | 100 | Timeout (max 180) |

### JWT Flow
1. Send credentials to TokenEndpoint (Basic Auth header or POST body)
2. Extract token via JwtTokenJsonPath or from response header
3. Use token in subsequent API requests

### JWT Limitations
- Requires username/password for token acquisition
- Does not support API key-based token requests
- Custom header auth (without username/password) not supported

## Less-Common Auth Types

CCF supports four additional auth types beyond Basic/APIKey/OAuth2/JwtToken. These appear
in the `rest_api_poller.schema.json` `auth` discriminator and are valid for production use,
but documentation is sparse. Use the auth-type `const` value verbatim — the schema
rejects any other casing.

### AliCloudSlsV1 — Alibaba Cloud Log Service

```json
"auth": {
    "type": "AliCloudSlsV1",
    "AccessKeyId": "[[parameters('accessKeyId')]",
    "AccessKeySecret": "[[parameters('accessKeySecret')]"
}
```
Required: `AccessKeyId`, `AccessKeySecret`. No other properties accepted.

### Oracle — Oracle Cloud Infrastructure PEM-key auth

```json
"auth": {
    "type": "Oracle",
    "pemFile": "[[parameters('pemFile')]",
    "publicFingerprint": "[[parameters('publicFingerprint')]",
    "tenantId": "[[parameters('tenantId')]",
    "userId": "[[parameters('userId')]",
    "passPhrase": "[[parameters('passPhrase')]"
}
```
Required: `pemFile`, `publicFingerprint`, `tenantId`, `userId`. Optional: `passPhrase`
(when the PEM key is passphrase-protected). Used by the OCI connector kind.

### Push — Entra app-based push auth

```json
"auth": {
    "type": "Push",
    "AppId": "[[parameters('appId')]",
    "ServicePrincipalId": "[[parameters('servicePrincipalId')]"
}
```
Required: `AppId`, `ServicePrincipalId`. This is the auth schema for the `Push` connector
kind — the connector validates that the inbound caller's Entra app matches these values,
rather than initiating an outbound auth flow. See `push-connectors.md`.

### VisaXpayToken — Visa Xpay API

```json
"auth": {
    "type": "VisaXpayToken",
    "ApiKey": "[[parameters('apiKey')]",
    "ApiSecret": "[[parameters('apiSecret')]",
    "ApiKeyName": "X-Pay-Token",
    "ApiKeyIdentifier": "",
    "ApiSecretName": "X-Pay-Secret",
    "IsApiKeyInPostPayload": false
}
```
Required: `ApiKey`, `ApiSecret`. Optional: `ApiKeyName`, `ApiKeyIdentifier`,
`ApiSecretName`, `IsApiKeyInPostPayload`. Two-credential variant of APIKey for vendors
that require separate key+secret headers (one in `ApiKeyName`, the other in
`ApiSecretName`).

## UI Configuration for Auth

### For OAuth2 flows
```json
"instructions": [{
    "type": "OAuthForm",
    "parameters": {
        "UsernameLabel": "Client ID",
        "PasswordLabel": "Client Secret",
        "connectButtonLabel": "Connect",
        "disconnectButtonLabel": "Disconnect"
    }
}]
```

### For APIKey / Basic (use OAuthForm or Textbox)
```json
"instructions": [
    { "type": "Textbox", "parameters": { "label": "API Key ID", "type": "text", "name": "username" } },
    { "type": "Textbox", "parameters": { "label": "API Secret", "type": "password", "name": "password" } },
    { "type": "ConnectionToggleButton", "parameters": { "connectLabel": "Connect", "name": "toggle" } }
]
```

Use `OAuthForm` even for non-OAuth API key + secret auth — it provides the right UI elements with customizable labels.

## Always Use securestring
```json
"apikey": {
    "defaultValue": "",
    "type": "securestring",
    "minLength": 1,
    "metadata": { "description": "Enter the API key." }
}
```
Values are unreadable after deployment.
