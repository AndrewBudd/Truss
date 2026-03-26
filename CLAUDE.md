# Truss — Knowledge Engineering Framework

This is a Truss repository: a structured knowledge base where documents are organized by epistemic type and linked via pinned git references.

## Key Concepts

- **Ground documents** (`ground/`) — observable facts with external evidence. Never reference other Truss docs in `assumes:`.
- **Hypothetical documents** (`hypothetical/`) — conditional reasoning that depends on ground, generic, or other hypothetical docs via `assumes:` with pinned commit hashes.
- **Generic documents** (`generic/`) — general principles parameterized over a class of things. Reference external evidence and other generics.
- **Pins** — every `assumes:` entry includes a `pin:` (short git commit hash from when the reference was valid). When the referenced doc changes, the dependent doc becomes **stale**.
- **Staleness** — propagates through the dependency graph. Resolve leaves first (topological order).

## CLI

All operations go through `python3 scripts/truss.py`:

```
validate       — check all docs against kind rules
build-deps     — regenerate .truss/deps.yaml (reverse dependency index)
detect-stale   — find stale pins, write .truss/stale.yaml
resolve        — interactive stale resolution workflow
new <kind> <id> <title> — scaffold a new document
init <name>    — create a new Truss repo from template
add-remote <name> <url> — register an external Truss repo
list-remotes   — show registered remotes
```

## Working With Documents

### Creating a new document

Use `/truss-new` or run `python3 scripts/truss.py new <kind> <id> <title>`. Ground doc IDs start with `g-`, hypothetical with `h-`, generic with `n-`.

### Frontmatter format

```yaml
---
kind: ground|hypothetical|generic
id: g-example
title: Human-Readable Title
created: 2026-03-25
layout: document          # for Jekyll rendering
evidence:                 # ground and generic docs
  - type: url|file|citation
    ref: "https://..."
assumes:                  # hypothetical docs (and generic cross-refs)
  - ref: ground/g-foo.md
    pin: abc1234
    note: "Why this dependency matters"
parameter: "..."          # generic docs only — what class of thing
status: ""                # empty, or "invalidated"
---
```

### Cross-repo references

Reference documents in other registered Truss repos:

```yaml
assumes:
  - ref: "@other-truss/ground/g-something.md"
    pin: abc1234
    repo: "https://github.com/org/other-truss"
    note: "Why this matters"
```

## Conventions

- Keep document bodies concise and structured with markdown headers.
- Every claim in a hypothetical should trace back to an `assumes:` entry.
- When updating a document, always re-pin dependents afterward: `python3 scripts/truss.py detect-stale`.
- Commit messages for document changes: `truss: <action> <doc-id> — <brief reason>`.
- Do not edit `.truss/deps.yaml` or `.truss/stale.yaml` by hand — they are generated.

## Slash Commands

Use these during conversation to work with the knowledge base:

- `/truss-new` — draft a new document (interactive)
- `/truss-research` — research a topic and draft ground documents from findings
- `/truss-validate` — validate all documents and report issues
- `/truss-status` — show overview of the knowledge base (counts, staleness, graph)
- `/truss-review` — review a specific document for quality and completeness
- `/truss-connect` — find and suggest connections between documents
