# Authentication Types Reference

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
