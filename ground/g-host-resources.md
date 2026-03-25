---
kind: ground
id: g-host-resources
title: Bare-Metal Host Resource Inventory
created: 2026-03-25
evidence:
  - type: file
    ref: inventory/host-specs-2026-03-24.json
  - type: url
    ref: https://internal.example.com/infra/hosts/bm-pool-01
---

# Bare-Metal Host Resource Inventory

Target deployment host specifications as of 2026-03-24.

## Hardware

- CPU: AMD EPYC 9454 (48 cores / 96 threads, 2.75 GHz base)
- Memory: 384 GiB DDR5-4800 ECC
- Storage: 2x 3.84 TB NVMe (Samsung PM9A3), RAID-0 for VM storage
- Network: 2x 100 GbE (Mellanox ConnectX-6), bonded

## Current Allocation

- 12 cores reserved for host OS and management
- 36 cores available for VM workloads
- 320 GiB available for VM memory (64 GiB reserved for host + buffers)
- 6.5 TB usable storage after filesystem overhead

## Observed Limits

- Tested stable with 180 concurrent Firecracker microVMs (2 vCPU, 512 MiB each)
- Storage throughput: 6.2 GB/s sequential read, 3.1 GB/s sequential write
- Network throughput: 2x 98 Gbps measured with iperf3
