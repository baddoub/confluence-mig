---
title: "API: Endpoint Name"
category: api
status: draft
owner: ""
tags: []
confluence_page_id: null
legacy_page_id: null
last_synced: null
created: YYYY-MM-DD
updated: YYYY-MM-DD
---

# API: Endpoint Name

## Overview

What this API does and who uses it.

## Base URL

```
https://api.example.com/v1
```

## Authentication

How to authenticate (API key, OAuth, Bearer token, etc.).

## Endpoints

### `GET /resource`

**Description**: Retrieve a list of resources.

**Parameters**:

| Name | Type | Required | Description |
|---|---|---|---|
| `limit` | integer | No | Max results (default 20) |
| `offset` | integer | No | Pagination offset |

**Response** (`200 OK`):

```json
{
  "data": [],
  "total": 0
}
```

**Errors**:

| Code | Description |
|---|---|
| 401 | Unauthorized |
| 404 | Not found |

### `POST /resource`

**Description**: Create a new resource.

**Request Body**:

```json
{
  "name": "string",
  "description": "string"
}
```

**Response** (`201 Created`):

```json
{
  "id": "string",
  "name": "string"
}
```

## Rate Limits

Describe any rate limiting policies.

## Related

- [Service Overview](../architecture/services/)
