---
kind: ground
id: g-firecracker-api
title: Firecracker API Surface (v1.6)
created: 2026-03-25
evidence:
  - type: url
    ref: https://github.com/firecracker-microvm/firecracker/blob/main/src/api_server/swagger/firecracker.yaml
  - type: url
    ref: https://github.com/firecracker-microvm/firecracker/releases/tag/v1.6.0
---

# Firecracker API Surface (v1.6)

Firecracker exposes a REST API over a Unix socket for VM lifecycle management.

## Key Endpoints

- `PUT /machine-config` — configure vCPUs, memory, HT
- `PUT /boot-source` — set kernel image and boot args
- `PUT /drives/{id}` — attach block devices (root and secondary)
- `PUT /network-interfaces/{id}` — attach tap devices
- `PUT /actions` — start (InstanceStart), stop, flush metrics
- `GET /` — instance info including state
- `PATCH /vm` — pause/resume
- `PUT /snapshot/create` and `PUT /snapshot/load` — snapshotting

## Constraints

- Single-process model: one Firecracker process per microVM
- API socket must be created before process start
- No hot-plug of devices after boot (drives and NICs must be configured before InstanceStart)
- Rate limiter can be applied per-drive and per-NIC
- Maximum 32 vCPUs, 256 GiB memory per VM
