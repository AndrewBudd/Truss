---
layout: document
kind: generic
id: n-cow-storage-patterns
title: Copy-on-Write Storage Performance Characteristics
created: 2026-03-25
parameter: "block storage system using copy-on-write with snapshot cloning"
evidence:
  - type: citation
    ref: "Rodeh, Bacik, Mason. BTRFS: The Linux B-Tree Filesystem. ACM TOS, 2013."
  - type: citation
    ref: "Tarasov et al. The Logic of File Systems. ACM Computing Surveys, 2015."
---

# Copy-on-Write Storage Performance Characteristics

For any block storage system using copy-on-write (CoW) with snapshot cloning, the following properties hold.

## Read Performance

- Reads from a snapshot clone are indistinguishable from reads on the original in terms of latency, until CoW fragmentation accumulates
- Sequential read performance degrades proportionally to the number of CoW redirections in the block map
- Read amplification is bounded by the depth of the snapshot tree

## Write Performance

- First write to any block in a clone triggers a CoW operation: allocate new block, copy, write, update metadata
- CoW overhead is amortized for sequential writes (block allocator can pre-allocate contiguous extents)
- Random write patterns produce the worst CoW overhead due to metadata scatter

## Space Characteristics

- Initial clone is O(1) in space — only metadata is duplicated
- Space divergence is proportional to write volume, not time
- Deleting a snapshot may not free space if other snapshots share the same blocks (reference counting required)

## Fragmentation

- Long-lived clones with heavy write activity fragment progressively
- Defragmentation on CoW filesystems requires careful handling to avoid breaking shared references
- Periodic re-cloning from a fresh base mitigates fragmentation
