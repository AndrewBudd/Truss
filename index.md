---
layout: default
title: Home
---

# Truss Knowledge Base

A knowledge engineering framework for structuring, validating, and evolving interconnected knowledge artifacts.

Truss separates knowledge into three structurally distinct document types with explicit, pinned dependency references stored in git. When any document changes, staleness propagates automatically through the dependency graph.

## Document Kinds

| Kind | Directory | Answers | Key Field |
|------|-----------|---------|-----------|
| **[Ground](ground/)** | `ground/` | "What is the case?" | `evidence:` |
| **[Hypothetical](hypothetical/)** | `hypothetical/` | "What follows from what we know?" | `assumes:` |
| **[Generic](generic/)** | `generic/` | "What is generally true about things like this?" | `parameter:` |

## Reference Rules

- **Ground** documents reference only external evidence. No `assumes:`.
- **Hypothetical** documents reference ground, hypothetical, or generic docs via `assumes:` with pinned commit hashes.
- **Generic** documents reference external evidence and other generics.

## Dependency Graph

{% include dep-graph.html %}

## How Staleness Works

Every `assumes:` reference includes a `pin:` -- the git commit hash when the reference was established. When the referenced document changes, the pin no longer matches, and the dependent document is marked **stale**. Resolution proceeds in topological order (leaves first) with four possible outcomes: **confirm**, **update**, **invalidate**, or **split**.
