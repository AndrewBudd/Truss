---
kind: hypothetical
id: h-migration-from-docker
title: Migration Path from Docker to Firecracker
created: 2026-03-25
assumes:
  - ref: ground/g-host-resources.md
    pin: 9868d04
    note: "Current host capacity determines how many VMs can replace containers"
  - ref: ground/g-firecracker-api.md
    pin: 9868d04
    note: "Firecracker API constraints shape the migration tooling"
  - ref: hypothetical/h-ssh-control-plane.md
    pin: 0000000
    note: "Target architecture uses SSH control plane for VM management"
---

# Migration Path from Docker to Firecracker

If the current deployment uses Docker containers on the same bare-metal hosts, and the target is Firecracker microVMs managed via the SSH control plane, then the migration proceeds as follows.

## Phase 1: Parallel Operation (Weeks 1-4)

- Deploy Firecracker alongside Docker on the same hosts
- Reserve 25% of host resources for Firecracker VMs
- Migrate stateless, low-risk workloads first (batch jobs, CI runners)
- Validate: compare latency, resource usage, and failure rates

## Phase 2: Gradual Shift (Weeks 5-8)

- Increase Firecracker allocation to 50%
- Migrate stateful workloads with snapshot-based state transfer
- Convert Docker Compose definitions to Firecracker VM configs
- Build rootfs images from existing Docker images using docker2rootfs

## Phase 3: Cutover (Weeks 9-12)

- Drain remaining Docker workloads
- Reclaim Docker-reserved resources for Firecracker
- Decommission Docker daemon and container runtime
- Full SSH control plane management of all workloads

## Risk Factors

- Docker volumes with persistent data need explicit migration to VM block devices
- Network policies (iptables/nftables) must be translated to Tailscale ACL rules
- Monitoring and logging pipelines need new agents inside VM guests
- Rollback plan: keep Docker images and configs for 30 days post-cutover
