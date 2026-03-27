---
title: "Module Name"
category: architecture
status: draft
module: ""
owner: ""
tags: []
confluence_page_id: null
legacy_page_id: null
last_synced: null
created: YYYY-MM-DD
updated: YYYY-MM-DD
---

# Module Name

## Purpose

What this module does and which business domain it owns.

## Boundaries

What this module is responsible for — and what it is NOT responsible for.

## Public Interface

How other modules interact with this one (exported functions, events, shared contracts).

## Internal Structure

Key internal components, patterns used (e.g., repository pattern, domain events).

## Data Ownership

Tables/entities owned by this module. No other module should query these directly.

## Dependencies

| Module | Direction | How |
|---|---|---|
| Auth | Depends on | Calls `auth.verify_token()` |
| Billing | Depended by | Emits `OrderCompleted` event |

## Configuration

Module-specific environment variables or feature flags.

## Related Docs

- [System Architecture](../overview.md)
- [Module API](../../api/endpoints/)
- [Module Runbook](../../runbooks/)
