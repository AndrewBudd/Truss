#!/usr/bin/env bash
# detect-stale.sh — Identify documents whose pinned references are out of date.
# Output: .truss/stale.yaml and exit code (0 = no stale, 1 = stale found)
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
STALE_FILE="$REPO_ROOT/.truss/stale.yaml"

tmp_stale=$(mktemp)
trap 'rm -f "$tmp_stale"' EXIT

# Get the short git hash for a file at HEAD.
# Returns empty string if file doesn't exist in git.
file_hash_at_head() {
    local filepath="$1"
    git -C "$REPO_ROOT" log -1 --format='%h' -- "$filepath" 2>/dev/null || echo ""
}

# Check a single document for stale pins
check_document() {
    local file="$1"
    local relpath="${file#$REPO_ROOT/}"
    local in_frontmatter=0
    local past_first_delimiter=0
    local current_ref=""
    local current_pin=""
    local current_note=""

    while IFS= read -r line; do
        if [[ "$line" == "---" ]]; then
            if [[ $past_first_delimiter -eq 0 ]]; then
                past_first_delimiter=1
                in_frontmatter=1
                continue
            else
                break
            fi
        fi
        [[ $in_frontmatter -eq 0 ]] && continue

        # Match ref line
        if [[ "$line" =~ ^[[:space:]]*-?[[:space:]]*ref:[[:space:]]*(ground/|hypothetical/|generic/)(.+)$ ]]; then
            # If we had a previous ref+pin, check it first
            if [[ -n "$current_ref" && -n "$current_pin" ]]; then
                check_pin "$relpath" "$current_ref" "$current_pin" "$current_note"
            fi
            current_ref="${BASH_REMATCH[1]}${BASH_REMATCH[2]}"
            current_ref="${current_ref%"${current_ref##*[![:space:]]}"}"
            current_pin=""
            current_note=""
        fi

        # Match pin line
        if [[ "$line" =~ ^[[:space:]]*pin:[[:space:]]*([a-f0-9]+) ]]; then
            current_pin="${BASH_REMATCH[1]}"
        fi

        # Match note line
        if [[ "$line" =~ ^[[:space:]]*note:[[:space:]]*\"?(.+)\"?$ ]]; then
            current_note="${BASH_REMATCH[1]}"
            current_note="${current_note%\"}"
        fi
    done < "$file"

    # Check the last ref+pin pair
    if [[ -n "$current_ref" && -n "$current_pin" ]]; then
        check_pin "$relpath" "$current_ref" "$current_pin" "$current_note"
    fi
}

check_pin() {
    local doc="$1"
    local ref="$2"
    local pin="$3"
    local note="$4"

    local current_hash
    current_hash=$(file_hash_at_head "$ref")

    if [[ -z "$current_hash" ]]; then
        # Referenced file doesn't exist in git
        echo "MISSING $doc $ref $pin" >> "$tmp_stale"
    elif [[ "$current_hash" != "$pin"* && "$pin" != "$current_hash"* ]]; then
        # Pin doesn't match current hash (prefix match to handle short hashes)
        echo "STALE $doc $ref $pin $current_hash" >> "$tmp_stale"
    fi
}

# Scan hypothetical and generic documents (ground docs don't have assumes)
for dir in hypothetical generic; do
    dirpath="$REPO_ROOT/$dir"
    [[ -d "$dirpath" ]] || continue
    while IFS= read -r -d '' file; do
        check_document "$file"
    done < <(find "$dirpath" -name '*.md' -print0 2>/dev/null)
done

# Write stale.yaml
mkdir -p "$(dirname "$STALE_FILE")"
cat > "$STALE_FILE" <<'HEADER'
# .truss/stale.yaml (generated, do not edit)
# Documents with out-of-date pinned references
# Rebuilt by scripts/detect-stale.sh
HEADER

stale_count=0
if [[ -s "$tmp_stale" ]]; then
    echo "stale:" >> "$STALE_FILE"
    while IFS=' ' read -r status doc ref pin current_hash; do
        stale_count=$((stale_count + 1))
        echo "  - document: $doc" >> "$STALE_FILE"
        echo "    dependency: $ref" >> "$STALE_FILE"
        echo "    pinned_hash: $pin" >> "$STALE_FILE"
        if [[ "$status" == "MISSING" ]]; then
            echo "    current_hash: \"(missing)\"" >> "$STALE_FILE"
            echo "    status: missing" >> "$STALE_FILE"
        else
            echo "    current_hash: $current_hash" >> "$STALE_FILE"
            echo "    status: stale" >> "$STALE_FILE"
        fi
    done < "$tmp_stale"
else
    echo "stale: []" >> "$STALE_FILE"
fi

echo "Staleness check complete: $stale_count stale reference(s) found."
echo "Results written to $STALE_FILE"

if [[ $stale_count -gt 0 ]]; then
    echo ""
    echo "Stale documents:"
    while IFS=' ' read -r status doc ref pin current_hash; do
        echo "  $doc -> $ref (pinned: $pin, current: ${current_hash:-(missing)})"
    done < "$tmp_stale"
    exit 1
fi

exit 0
