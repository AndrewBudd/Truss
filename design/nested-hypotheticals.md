# Nested Hypotheticals Framework

**Status:** Draft proposal
**Date:** 2026-03-26

## Motivation

The current Truss framework has three document kinds: ground, hypothetical, and generic. The "hypothetical" kind is really a conditional statement — "if A and B, then C." It derives a conclusion from assumptions. It does not model *scenarios*.

Real decision-making requires reasoning about entire possible futures: "What if we adopt microservices?" isn't one conditional — it spawns dozens of interrelated facts, inferences, and sub-decisions. The current framework has no way to group these, compare alternatives, or compose scenarios.

This proposal introduces **hypothetical scopes** — scenario containers that hold their own documents — and renames the current "hypothetical" kind to **conditional** to reflect what it actually is.

## Summary of Changes

1. **Rename** `hypothetical` to `conditional` (document kind and directory).
2. **Introduce** `hypothetical` as a new document kind representing a scenario scope.
3. **Add** `scope`, `role`, and `decision` fields to the document schema.
4. **Define** visibility rules for cross-scope references.
5. **Define** relationships between hypotheticals: dependency (DAG) and mutual exclusion (decision groups).

---

## The Rename: Hypothetical to Conditional

Current hypothetical documents are conditional statements. They assume some set of ground and generic documents and derive conclusions. The name "hypothetical" overpromises — these documents don't model hypothetical worlds, they model logical inferences.

- Directory: `hypothetical/` becomes `conditional/`
- Kind value: `hypothetical` becomes `conditional`
- ID prefix: `h-` becomes `c-`
- All existing behavior (assumes, pins, staleness) remains identical

The `h-` prefix is freed up for the new hypothetical scope kind.

---

## New Kind: Hypothetical (Scenario Scope)

A hypothetical defines a scenario — a possible future that can be reasoned about as a coherent unit. It is not a single inference but a *context* that contains its own ground, conditional, and generic documents.

### Frontmatter

```yaml
---
kind: hypothetical
id: h-use-kubernetes
title: "What if we use Kubernetes for orchestration?"
created: 2026-03-26
layout: document

depends_on:                              # other hypotheticals this scenario requires
  - ref: hypothetical/h-adopt-microservices.md
    pin: abc1234
    note: "This scenario assumes microservices are adopted"

decision: d-orchestration-platform       # optional: mutual exclusion group
status: ""
---
```

### Key Properties

**depends_on (DAG, not tree).** A hypothetical can depend on zero or more other hypotheticals. This forms a directed acyclic graph, not a tree. A scenario like "microservices with an expanded team" can depend on both "adopt microservices" and "hire 5 more engineers" simultaneously.

**decision (mutual exclusion).** Hypotheticals that share a `decision` value are alternatives — mutually exclusive answers to the same question. The framework validates that no hypothetical (or its transitive dependents) depends on two members of the same decision group, since that would be a contradiction.

**Contains documents.** A hypothetical scope has its own ground, conditional, and generic documents. These are regular Truss documents with an added `scope` field.

---

## Scoped Documents

Any ground, conditional, or generic document can belong to a hypothetical scope by declaring it in frontmatter:

```yaml
---
kind: ground
id: g-k8s-latency
title: "Expected Kubernetes orchestration latency"
created: 2026-03-26
scope: h-use-kubernetes
role: orchestration-latency              # optional
evidence:
  - type: stipulation
    ref: "Based on benchmarks from production clusters at similar scale"
---
```

### scope (required for non-root documents)

Which hypothetical this document belongs to. Omit for root-level documents (the current default). A document belongs to exactly one scope — no shared ownership.

### role (optional)

A semantic identifier for the structural slot this document fills. Two documents in alternative hypotheticals (same decision group) with the same role are structurally comparable and substitutable.

Roles enable:
- **Structured comparison** of alternative hypotheticals by diffing their role implementations
- **Impact analysis** when swapping alternatives — conditionals depending on roles where alternatives disagree are flagged stale; those where they agree are not
- **Clean promotion** — when a hypothetical comes true, role mappings guide how its documents replace the previous state

Roles are optional. Many documents within a hypothetical are unique to that scenario and have no counterpart in alternatives. Only documents that answer a question shared across alternatives need roles.

### Ground documents as stipulations

Ground documents in the root scope have external evidence (URLs, citations, observations). Ground documents inside a hypothetical scope are *stipulations* — facts assumed for the sake of the scenario. Use the evidence type `stipulation` to make this explicit:

```yaml
evidence:
  - type: stipulation
    ref: "Assumed: team adopts Kubernetes based on current evaluation criteria"
```

---

## Visibility Rules

A document in scope X can reference:

1. **Root documents** — always visible from any scope.
2. **Own-scope documents** — documents in the same hypothetical.
3. **Ancestor-scope documents** — documents in any hypothetical that X transitively `depends_on`.

A document **cannot** reference documents in:
- Sibling hypotheticals (alternatives in the same decision group)
- Unrelated hypotheticals (not in the transitive dependency chain)

This is lexical scoping for knowledge. Inner scopes see outward, never sideways.

---

## Reference Mechanisms

### Concrete references (existing)

The current `assumes:` mechanism continues to work unchanged. A concrete reference points to a specific document by path and pin:

```yaml
assumes:
  - ref: ground/g-team-size.md
    pin: abc1234
    scope: h-adopt-microservices        # optional: clarifies which scope
    note: "Depends on projected team size"
```

### Role-based references (new)

A conditional can reference a role within a specific hypothetical scope rather than a concrete document. This is useful when writing conditionals that are portable across alternatives:

```yaml
assumes:
  - role: orchestration-latency
    scope: h-use-kubernetes
    note: "Depends on whatever the orchestration latency turns out to be"
```

Role-based references resolve to the document in the specified scope that declares that role. The framework validates that exactly one document in the target scope fills the role.

Either mechanism is valid. Concrete references are the default for most use. Role-based references are available when the structural slot matters more than the specific document.

---

## Relationships Between Hypotheticals

### Dependency (depends_on)

A hypothetical can depend on other hypotheticals, forming a DAG. "Kubernetes with expanded team" depends on both "adopt microservices" and "hire engineers." Documents within the dependent scope can see everything in the ancestor scopes.

### Mutual Exclusion (decision)

Hypotheticals sharing a `decision` value are alternatives. Validation rules:

- No hypothetical may `depends_on` two members of the same decision group (contradiction).
- Alternative hypotheticals *should* implement the same roles (warning, not error — alternatives may have asymmetric structure).
- At most one member of a decision group may be promoted at a time.

### No Relationship (independent)

Hypotheticals with no `depends_on` or shared `decision` are independent scenarios. They cannot see each other's documents and have no interaction.

---

## Filesystem Layout

Scoped documents live under a `scoped/` directory, organized by hypothetical ID:

```
ground/                          # root ground docs
conditional/                     # root conditionals (renamed)
generic/                         # root generics
hypothetical/                    # hypothetical scope definitions
  h-adopt-microservices.md
  h-use-kubernetes.md
  h-use-nomad.md
  h-hire-engineers.md
  h-microservices-with-team.md
scoped/                          # documents inside hypothetical scopes
  h-adopt-microservices/
    ground/
    conditional/
    generic/
  h-use-kubernetes/
    ground/
    conditional/
    generic/
  h-use-nomad/
    ground/
    conditional/
    generic/
```

The `scope` field in frontmatter is the source of truth for scope membership. The directory structure mirrors it for human navigability.

---

## Staleness Propagation

Staleness now operates at two levels:

1. **Document-level** (existing): a document's `assumes:` pin is outdated because the referenced document changed.
2. **Scope-level** (new): a hypothetical's `depends_on` pin is outdated because the referenced hypothetical or its contents changed.

A change to a root ground document can ripple through multiple hypothetical scopes. A change to a hypothetical's internal document can make dependent hypotheticals stale. The staleness walker must traverse both the document dependency graph and the hypothetical dependency DAG.

---

## Promotion

When a hypothetical "comes true" — a decision is made, a system is built, an event occurs — its documents can be promoted to the parent context:

- Stipulated ground docs gain real evidence and move to root `ground/`.
- Scoped conditionals become root `conditional/` documents.
- The hypothetical scope definition is archived or marked with a status.
- If the hypothetical belongs to a decision group, the other alternatives are invalidated.

Promotion mechanics are deliberately left underspecified. The right workflow will emerge from use.

---

## Open Questions

These are recognized as important but intentionally deferred until usage patterns reveal the right answers:

- **Role granularity.** How specific should roles be? Are they freeform strings, or should there be a controlled vocabulary?
- **Conflict detection.** When a hypothetical depends on two others, their stipulations might contradict. What counts as a conflict? This is likely domain-specific.
- **Partial promotion.** Can you promote a subset of a hypothetical's documents? Or is promotion always atomic?
- **Role-based reference resolution.** Should role references be fully resolved by tooling, or remain advisory metadata for human comparison?
- **Cross-repo hypotheticals.** Can a hypothetical in one Truss repo depend on a hypothetical in another? The existing cross-repo reference mechanism (`@repo/path`) could extend, but the visibility rules become more complex.

---

## Migration Path

1. Rename `hypothetical/` directory to `conditional/`, update `kind:` fields.
2. Update ID prefixes from `h-` to `c-` in existing documents and all references.
3. Re-pin all affected `assumes:` entries.
4. Create `hypothetical/` directory for new scope definitions.
5. Create `scoped/` directory structure as needed.
6. Update `scripts/truss.py` validation, staleness detection, and scaffolding.
7. Update `CLAUDE.md` with revised schema documentation.
