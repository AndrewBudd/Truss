#!/usr/bin/env bash
# build-deps.sh — Parse all Truss document frontmatter and build the reverse dependency index.
# Output: .truss/deps.yaml
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
DEPS_FILE="$REPO_ROOT/.truss/deps.yaml"

# Temporary files for collecting forward references
tmp_forward=$(mktemp)
trap 'rm -f "$tmp_forward"' EXIT

# Extract refs from YAML frontmatter of a single file.
# Looks for lines matching "- ref: <path>" inside assumes: or evidence: blocks,
# but only evidence refs that point to internal truss docs (ground/, hypothetical/, generic/).
extract_refs() {
    local file="$1"
    local relpath="${file#$REPO_ROOT/}"
    local in_frontmatter=0
    local past_first_delimiter=0

    while IFS= read -r line; do
        # Detect frontmatter boundaries
        if [[ "$line" == "---" ]]; then
            if [[ $past_first_delimiter -eq 0 ]]; then
                past_first_delimiter=1
                in_frontmatter=1
                continue
            else
                # End of frontmatter
                break
            fi
        fi
        [[ $in_frontmatter -eq 0 ]] && continue

        # Match ref lines: "    ref: ground/foo.md" or "    ref: hypothetical/bar.md"
        if [[ "$line" =~ ^[[:space:]]*-?[[:space:]]*ref:[[:space:]]*(ground/|hypothetical/|generic/)(.+)$ ]]; then
            local kind="${BASH_REMATCH[1]}"
            local rest="${BASH_REMATCH[2]}"
            local target="${kind}${rest}"
            # Strip any trailing whitespace
            target="${target%"${target##*[![:space:]]}"}"
            echo "$target $relpath"
        fi
    done < "$file"
}

# Scan all markdown files in the three kind directories
for dir in ground hypothetical generic; do
    dirpath="$REPO_ROOT/$dir"
    [[ -d "$dirpath" ]] || continue
    while IFS= read -r -d '' file; do
        extract_refs "$file" >> "$tmp_forward"
    done < <(find "$dirpath" -name '*.md' -print0 2>/dev/null)
done

# Build the reverse index: for each target, list all documents that reference it
mkdir -p "$(dirname "$DEPS_FILE")"
cat > "$DEPS_FILE" <<'HEADER'
# .truss/deps.yaml (generated, do not edit)
# Reverse dependency index: target -> list of documents that reference it
# Rebuilt by scripts/build-deps.sh
HEADER

if [[ -s "$tmp_forward" ]]; then
    # Sort by target, then emit YAML
    sort -k1,1 "$tmp_forward" | awk '
    BEGIN { current = "" }
    {
        target = $1
        source = $2
        if (target != current) {
            if (current != "") printf "\n"
            printf "%s:\n", target
            current = target
        }
        printf "  - %s\n", source
    }
    END { if (current != "") printf "\n" }
    ' >> "$DEPS_FILE"
else
    echo "# (no dependencies found)" >> "$DEPS_FILE"
fi

echo "Dependency index written to $DEPS_FILE"
