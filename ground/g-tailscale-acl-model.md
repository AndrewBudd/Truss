---
kind: ground
id: g-tailscale-acl-model
title: Tailscale ACL Model and Tag-Based Access
created: 2026-03-25
evidence:
  - type: url
    ref: https://tailscale.com/kb/1068/acl-tags
  - type: url
    ref: https://tailscale.com/kb/1018/acls
---

# Tailscale ACL Model and Tag-Based Access

Tailscale ACLs define which nodes can communicate with which other nodes and on which ports.

## Key Properties

- ACLs are defined in a JSON policy file (HuJSON format) in the admin console
- Default deny: no traffic flows unless explicitly allowed
- Tag-based access: nodes can be tagged (e.g., `tag:vm`, `tag:control-plane`) and ACLs reference tags
- Tags are owned by tag owners defined in the ACL file
- A tagged node loses its user identity — it acts as the tag

## Tag Assignment

- Tags can be assigned at node registration via `--advertise-tags`
- Pre-auth keys can be created with specific tags
- Tagged nodes cannot be re-tagged without admin action

## ACL Rule Structure

```json
{
  "action": "accept",
  "src": ["tag:control-plane"],
  "dst": ["tag:vm:22"]
}
```

This allows `tag:control-plane` nodes to reach `tag:vm` nodes on port 22 only.
