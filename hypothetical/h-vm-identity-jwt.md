---
layout: document
kind: hypothetical
id: h-vm-identity-jwt
title: JWT-Based VM Identity via Metadata Service
created: 2026-03-25
assumes:
  - ref: ground/g-tailscale-acl-model.md
    pin: 9868d04
    note: "Tag-based ACLs determine what scoped identity a VM needs"
  - ref: hypothetical/h-ssh-control-plane.md
    pin: 843a628
    note: "Control plane must provision identity tokens at VM boot"
---

# JWT-Based VM Identity via Metadata Service

If VMs receive their identity via short-lived JWTs served from a host-local metadata service, and the control plane (SSH-based) provisions these tokens at boot, then credential scoping works as follows.

## Token Flow

1. VM boots and Firecracker guest agent requests identity from MMDS (MicroVM Metadata Service)
2. Host-side control plane generates a JWT scoped to the VM's role
3. JWT contains: VM ID, assigned tags (matching Tailscale ACL tags), expiry (15 min)
4. VM uses JWT to authenticate to internal services via the forward proxy
5. Forward proxy validates JWT, maps sentinel tokens to real credentials based on JWT claims

## Scoping Rules

- Each JWT is bound to a single VM instance (subject = VM ID)
- Claims include allowed upstream services (audience field)
- Token refresh requires re-authentication through the control plane
- Revocation: control plane maintains a short-lived deny list, but primary mechanism is short expiry

## Security Properties

- VM cannot forge identity: JWT is signed by host CA, VM has no access to signing key
- Blast radius: compromised VM can only access services listed in its JWT audience
- Lateral movement: limited by Tailscale ACL tags — a `tag:worker` VM cannot reach `tag:control-plane` endpoints

## Dependencies

This design requires:
- The SSH control plane to be operational before any VM boots (ordering constraint)
- Tailscale ACL tags to be pre-configured for each VM role
- A forward proxy per VM (or per host with VM-aware routing)
