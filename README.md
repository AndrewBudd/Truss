# Truss

A knowledge engineering framework for structuring, validating, and evolving interconnected knowledge artifacts.

Truss separates knowledge into three structurally distinct document types — **ground** (what is), **hypothetical** (what follows), and **generic** (what is generally true) — with explicit, pinned dependency references stored in git. When any document changes, staleness propagates automatically through the dependency graph.

## Quick Start

```bash
# Create documents
python3 scripts/truss.py new ground g-api-shape "Current API Shape"
python3 scripts/truss.py new hypothetical h-migration "Migration Plan"
python3 scripts/truss.py new generic n-caching "Cache Invalidation Properties"

# Validate all documents
python3 scripts/truss.py validate

# Build the reverse dependency index
python3 scripts/truss.py build-deps

# Detect stale references
python3 scripts/truss.py detect-stale

# Interactively resolve stale documents
python3 scripts/truss.py resolve
```

## Document Kinds

| Kind | Directory | Answers | Key Field |
|------|-----------|---------|-----------|
| **Ground** | `ground/` | "What is the case?" | `evidence:` |
| **Hypothetical** | `hypothetical/` | "What follows from what we know?" | `assumes:` |
| **Generic** | `generic/` | "What is generally true about things like this?" | `parameter:` |

## Reference Rules

- **Ground** documents reference only external evidence. No `assumes:`.
- **Hypothetical** documents reference ground, hypothetical, or generic docs via `assumes:` with pinned commit hashes.
- **Generic** documents reference external evidence and other generics.

## How Staleness Works

Every `assumes:` reference includes a `pin:` — the git commit hash when the reference was established. When the referenced document changes, the pin no longer matches, and the dependent document is marked **stale**. Resolution proceeds in topological order (leaves first) with four possible outcomes: **confirm**, **update**, **invalidate**, or **split**.

## Repository Structure

```
project/
├── .truss/
│   ├── config.yaml       # project settings
│   ├── deps.yaml          # generated reverse dependency index
│   └── stale.yaml         # generated stale queue
├── ground/                # categorical judgments
├── hypothetical/          # conditional judgments
├── generic/               # universal judgments
└── scripts/
    └── truss.py           # CLI tool
```

## Requirements

- Python 3.9+
- Git
