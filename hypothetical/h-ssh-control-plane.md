---
kind: hypothetical
id: h-ssh-control-plane
title: SSH as VM Control Plane
created: 2026-03-25
assumes:
  - ref: ground/g-firecracker-api.md
    pin: 9868d04
    note: "API socket model determines how control commands reach the VM"
  - ref: ground/g-host-resources.md
    pin: 9868d04
    note: "Available cores and network bandwidth constrain control plane throughput"
---

# SSH as VM Control Plane

If we use SSH as the primary control plane for managing Firecracker microVMs, we can achieve low-latency command dispatch while reusing standard authentication infrastructure.

## Architecture

The control plane SSH daemon runs on the host and dispatches commands to individual VM API sockets:

1. Incoming SSH connection authenticated via Tailscale identity
2. Command parsed and validated against allowed operations
3. Command translated to Firecracker API call over Unix socket
4. Response returned over SSH channel

## Throughput Estimate

Given 36 available cores and the lightweight nature of SSH session handling:
- Each SSH session consumes ~2 MB memory and negligible CPU when idle
- Command dispatch latency: ~5ms (SSH overhead) + ~2ms (Unix socket to Firecracker API)
- Estimated maximum concurrent sessions: 2,000+ (memory-bound, not CPU-bound)
- Burst command throughput: ~500 commands/second per core dedicated to control plane

## Trade-offs

**Advantages:**
- SSH is universally supported and well-understood
- Key-based auth integrates with existing PKI
- Built-in encryption, no additional TLS layer needed
- Multiplexing via SSH channels reduces connection overhead

**Disadvantages:**
- SSH connection setup is heavier than raw TCP (~50ms handshake)
- Per-VM SSH daemon would not scale; must use host-level multiplexer
- Binary protocol support requires custom subsystem or exec channels
