# Pagination Types Reference

## Decision Guide

| API Behavior | CCP Paging Type |
|-------------|-----------------|
| Returns next/prev page URLs in headers | `LinkHeader` |
| Same as above, but cursor must persist across query windows | `PersistentLinkHeader` |
| Returns full next-page URL in response body | `NextPageUrl` |
| Returns a token/cursor for the next page | `NextPageToken` |
| Token persists server-side across requests | `PersistentToken` |
| Supports skip/offset parameter | `Offset` |
| Supports page number parameter | `CountBasedPaging` |
| Uses a results cookie for pagination | `NextPageToken` (extract cookie from JSON path) |

## LinkHeader / PersistentLinkHeader

Based on RFC 5988. API returns page links in `Link` header or response body.

`PersistentLinkHeader` persists cursor in backend storage across query windows. Useful when APIs don't support time-range parameters and use server-side cursors instead.

**Limitation:** PersistentLinkHeader allows only ONE concurrent query to avoid race conditions.

```json
"paging": {
    "pagingType": "LinkHeader",
    "linkHeaderTokenJsonPath": "$.metadata.links.next"
}
```
```json
"paging": {
    "pagingType": "PersistentLinkHeader",
    "pageSizeParameterName": "limit",
    "pageSize": 500
}
```

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| linkHeaderTokenJsonPath | No | string | JSONPath to next-page link in response body |
| pageSize | No | integer | Events per page |
| pageSizeParameterName | No | string | Query param name for page size |
| pagingInfoPlacement | No | string | `QueryString` or `RequestBody` |
| pagingQueryParamOnly | No | boolean | If true, omit all non-paging query params |

## NextPageUrl

API returns a complex next-page URL in the response body.

```json
"paging": {
    "pagingType": "NextPageUrl",
    "nextPageTokenJsonPath": "$.data.repository.pageInfo.endCursor",
    "hasNextFlagJsonPath": "$.data.repository.pageInfo.hasNextPage",
    "nextPageUrl": "https://api.github.com/graphql",
    "nextPageUrlQueryParametersTemplate": "{'query':'query{repository(owner:\"xyz\")}"
}
```

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| pageSize | No | integer | Events per page |
| pageSizeParameterName | No | string | Query param for page size |
| nextPageUrl | No | string | Base URL (for Coralogix API) |
| nextPageUrlQueryParameters | No | object | Custom query params for next-page requests |
| NextPageParaName | No | string | Next-page parameter name in request (Pascal-cased in schema) |
| hasNextFlagJsonPath | No | string | JSONPath to hasNextPage flag |
| nextPageRequestHeader | No | string | Next-page header name |
| nextPageUrlQueryParametersTemplate | No | string | Template for next-page params (Coralogix) |
| pagingInfoPlacement | No | string | `QueryString` or `RequestBody` |
| pagingQueryParamOnly | No | boolean | If true, omit all non-paging query params |

## NextPageToken / PersistentToken

Uses a token (hash or cursor) representing current page state.

`PersistentToken` persists server-side — the server remembers the last retrieved token.

```json
"paging": {
    "pagingType": "NextPageToken",
    "nextPageRequestHeader": "ETag",
    "nextPageTokenResponseHeader": "ETag"
}
```
```json
"paging": {
    "pagingType": "PersistentToken",
    "nextPageParaName": "gta",
    "nextPageTokenJsonPath": "$.alerts[-1:]._id"
}
```

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| pageSize | No | integer | Events per page |
| pageSizeParameterName | No | string | Query param for page size |
| nextPageTokenJsonPath | No | string | JSONPath to next-page token in body |
| nextPageTokenResponseHeader | No | string | Header containing token (if not in body) |
| NextPageParaName | No | string | Next-page parameter name in request (Pascal-cased in schema) |
| hasNextFlagJsonPath | No | string | JSONPath to hasNextPage flag |
| nextPageRequestHeader | No | string | Header name for next-page token in request |
| pagingInfoPlacement | No | string | `QueryString` or `RequestBody` |
| pagingQueryParamOnly | No | boolean | If true, omit all non-paging query params |

## Offset

Skip N records, retrieve next batch.

```json
"paging": {
    "pagingType": "Offset",
    "offsetParaName": "offset",
    "pageSize": 50,
    "pagingQueryParamOnly": true,
    "pagingInfoPlacement": "QueryString"
}
```

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| pageSize | No | integer | Events per page |
| pageSizeParameterName | No | string | Query param for page size |
| offsetParaName | No | string | Query param for offset value (CCF calculates: all_events + 1) |
| pagingInfoPlacement | No | string | `QueryString` or `RequestBody` |
| pagingQueryParamOnly | No | boolean | If true, omit all non-paging query params |

## CountBasedPaging

Specify number of items to return per page using a page number parameter.

```json
"paging": {
    "pagingType": "CountBasedPaging",
    "pageNumberParaName": "page",
    "pageSize": 10,
    "zeroBasedIndexing": true,
    "hasNextFlagJsonPath": "$.hasNext",
    "totalResultsJsonPath": "$.totalResults",
    "pageNumberJsonPath": "$.pageNumber",
    "pageCountJsonPath": "$.pageCount"
}
```

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| pageNumberParaName | Yes | string | Parameter name for page number |
| pageSize | No | integer | Events per page |
| zeroBasedIndexing | No | boolean | Is page numbering 0-based? |
| hasNextFlagJsonPath | No | string | JSONPath to hasMorePages flag |
| totalResultsJsonPath | No | string | JSONPath to total result count |
| pageNumberJsonPath | No | string | JSONPath to current page number (required if totalResultsJsonPath set) |
| pageCountJsonPath | No | string | JSONPath to total page count (required if totalResultsJsonPath set) |
| pagingInfoPlacement | No | string | `QueryString` or `RequestBody` |
| pagingQueryParamOnly | No | boolean | If true, omit all non-paging query params |

## Rate Limit Mitigation for Pagination Bursts

Pagination causes burst traffic — 10 pages fire in rapid succession even if baseline polling is infrequent.

Mitigations:
1. **Maximize page size** — reduce total pages per poll
2. **Increase `retryCount`** (max 6) — handle 429 responses
3. **Increase `timeoutInSeconds`** — allow retries to complete
4. **Stagger polling intervals** across connectors
5. **Increase `queryWindowInMin`** — poll less often (trades latency for reliability)
6. **Use `rateLimitConfig`** — read rate limit headers from responses:
```json
"rateLimitConfig": {
    "evaluation": { "checkMode": "OnlyWhen429" },
    "extraction": {
        "source": "CustomHeaders",
        "headers": {
            "limit": { "name": "X-RateLimit-Limit", "format": "Integer" },
            "remaining": { "name": "X-RateLimit-Remaining", "format": "Integer" },
            "reset": { "name": "X-RateLimit-RetryAfter", "format": "UnixTimeSeconds" }
        }
    },
    "retryStrategy": { "useResetOrRetryAfterHeaders": true }
}
```
