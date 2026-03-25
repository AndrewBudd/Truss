#!/usr/bin/env bash
# new-doc.sh — Create a new Truss document with proper frontmatter.
# Usage: new-doc.sh <kind> <id> <title>
# Example: new-doc.sh ground g-api-shape "Current API Response Shape"
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"

usage() {
    echo "Usage: $0 <kind> <id> <title>"
    echo ""
    echo "Kinds: ground, hypothetical, generic"
    echo ""
    echo "Examples:"
    echo "  $0 ground g-api-shape \"Current API Response Shape\""
    echo "  $0 hypothetical h-migration-plan \"Migration Plan to New API\""
    echo "  $0 generic n-cow-patterns \"Copy-on-Write Storage Patterns\""
    exit 1
}

[[ $# -lt 3 ]] && usage

kind="$1"
id="$2"
shift 2
title="$*"
date=$(date +%Y-%m-%d)

case "$kind" in
    ground)
        dir="$REPO_ROOT/ground"
        cat > "$dir/$id.md" <<EOF
---
kind: ground
id: $id
title: $title
created: $date
evidence:
  - type: url
    ref: TODO
---

# $title

TODO: Document the observable facts here.
EOF
        ;;
    hypothetical)
        dir="$REPO_ROOT/hypothetical"
        cat > "$dir/$id.md" <<EOF
---
kind: hypothetical
id: $id
title: $title
created: $date
assumes:
  - ref: ground/TODO.md
    pin: 0000000
    note: "TODO: why this dependency matters"
---

# $title

TODO: Document the conditional reasoning here.
EOF
        ;;
    generic)
        dir="$REPO_ROOT/generic"
        cat > "$dir/$id.md" <<EOF
---
kind: generic
id: $id
title: $title
created: $date
parameter: "TODO: what kind of thing this applies to"
evidence:
  - type: citation
    ref: "TODO"
---

# $title

TODO: Document the general principle here.
EOF
        ;;
    *)
        echo "Unknown kind: $kind"
        echo "Must be one of: ground, hypothetical, generic"
        exit 1
        ;;
esac

echo "Created $dir/$id.md"
