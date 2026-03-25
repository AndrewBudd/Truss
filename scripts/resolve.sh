#!/usr/bin/env bash
# resolve.sh — Interactive resolution workflow for stale Truss documents.
# Resolves stale documents in topological order (leaves first).
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
STALE_FILE="$REPO_ROOT/.truss/stale.yaml"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}Truss Resolution Workflow${NC}"
echo "========================="
echo ""

# First, detect current staleness
echo "Detecting stale documents..."
bash "$REPO_ROOT/scripts/detect-stale.sh" 2>/dev/null && {
    echo -e "${GREEN}No stale documents found. Nothing to resolve.${NC}"
    exit 0
}

echo ""
echo -e "${YELLOW}Beginning resolution in topological order...${NC}"
echo ""

# Parse stale.yaml to get list of stale documents and their deps
# We need to resolve in topological order: documents whose stale deps
# are themselves not stale should be resolved first.

# Collect unique stale documents
stale_docs=()
declare -A stale_deps

while IFS= read -r line; do
    if [[ "$line" =~ ^[[:space:]]*-[[:space:]]*document:[[:space:]]*(.+)$ ]]; then
        current_doc="${BASH_REMATCH[1]}"
        current_doc="${current_doc%"${current_doc##*[![:space:]]}"}"
    fi
    if [[ "$line" =~ ^[[:space:]]*dependency:[[:space:]]*(.+)$ ]]; then
        dep="${BASH_REMATCH[1]}"
        dep="${dep%"${dep##*[![:space:]]}"}"
        # Check if this doc is already in our list
        local found=0
        for d in "${stale_docs[@]+"${stale_docs[@]}"}"; do
            if [[ "$d" == "$current_doc" ]]; then
                found=1
                break
            fi
        done
        if [[ $found -eq 0 ]]; then
            stale_docs+=("$current_doc")
        fi
        stale_deps["$current_doc"]="${stale_deps[$current_doc]+"${stale_deps[$current_doc]} "}$dep"
    fi
done < "$STALE_FILE"

if [[ ${#stale_docs[@]} -eq 0 ]]; then
    echo -e "${GREEN}No stale documents to resolve.${NC}"
    exit 0
fi

# Simple topological sort: resolve docs whose dependencies are not themselves stale first
resolved=()
remaining=("${stale_docs[@]}")

resolve_round() {
    local next_remaining=()
    local resolved_this_round=0

    for doc in "${remaining[@]}"; do
        local deps_stale=0
        for dep in ${stale_deps[$doc]}; do
            # Check if the dependency is itself a stale document that hasn't been resolved
            for r in "${remaining[@]}"; do
                if [[ "$r" == "$dep" ]]; then
                    # Check it wasn't already resolved
                    local already_resolved=0
                    for done_doc in "${resolved[@]+"${resolved[@]}"}"; do
                        if [[ "$done_doc" == "$dep" ]]; then
                            already_resolved=1
                            break
                        fi
                    done
                    if [[ $already_resolved -eq 0 ]]; then
                        deps_stale=1
                        break
                    fi
                fi
            done
            [[ $deps_stale -eq 1 ]] && break
        done

        if [[ $deps_stale -eq 0 ]]; then
            resolve_document "$doc"
            resolved+=("$doc")
            resolved_this_round=1
        else
            next_remaining+=("$doc")
        fi
    done

    remaining=("${next_remaining[@]+"${next_remaining[@]}"}")
    return $([[ $resolved_this_round -eq 1 ]] && echo 0 || echo 1)
}

resolve_document() {
    local doc="$1"
    local filepath="$REPO_ROOT/$doc"

    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "Resolving: ${BLUE}$doc${NC}"
    echo -e "Stale dependencies: ${RED}${stale_deps[$doc]}${NC}"
    echo ""

    # Show diff for each stale dependency
    for dep in ${stale_deps[$doc]}; do
        local dep_path="$REPO_ROOT/$dep"
        if [[ -f "$dep_path" ]]; then
            echo -e "  ${YELLOW}Changes in $dep:${NC}"
            # Find the pinned hash for this dep in this doc
            local pin=""
            local in_fm=0
            local past_delim=0
            local found_ref=0
            while IFS= read -r line; do
                if [[ "$line" == "---" ]]; then
                    if [[ $past_delim -eq 0 ]]; then past_delim=1; in_fm=1; continue; fi
                    break
                fi
                [[ $in_fm -eq 0 ]] && continue
                if [[ "$line" =~ ref:.*"$dep" ]]; then found_ref=1; fi
                if [[ $found_ref -eq 1 && "$line" =~ pin:[[:space:]]*([a-f0-9]+) ]]; then
                    pin="${BASH_REMATCH[1]}"
                    found_ref=0
                fi
            done < "$filepath"

            if [[ -n "$pin" ]]; then
                echo -e "  (pinned at: $pin)"
                git -C "$REPO_ROOT" diff "$pin"..HEAD -- "$dep" 2>/dev/null || echo "  (cannot compute diff — pin may be too old)"
            fi
            echo ""
        else
            echo -e "  ${RED}$dep no longer exists!${NC}"
        fi
    done

    echo ""
    echo "Resolution options:"
    echo "  [c] Confirm — dependency change does not affect this document (re-pin only)"
    echo "  [u] Update  — revise this document (opens \$EDITOR)"
    echo "  [i] Invalidate — mark this document as invalidated"
    echo "  [s] Skip    — defer resolution to later"
    echo ""
    read -r -p "Choose action for $doc [c/u/i/s]: " action

    case "$action" in
        c|C)
            repin_document "$filepath"
            git -C "$REPO_ROOT" add "$filepath"
            git -C "$REPO_ROOT" commit -m "truss: confirm $doc (re-pin dependencies)"
            echo -e "${GREEN}Confirmed and re-pinned.${NC}"
            ;;
        u|U)
            echo "Opening $filepath for editing..."
            ${EDITOR:-vi} "$filepath"
            repin_document "$filepath"
            git -C "$REPO_ROOT" add "$filepath"
            git -C "$REPO_ROOT" commit -m "truss: update $doc (revised after dependency change)"
            echo -e "${GREEN}Updated and re-pinned.${NC}"
            ;;
        i|I)
            read -r -p "Reason for invalidation: " reason
            # Add invalidation notice to frontmatter
            sed -i "s/^---$/---\nstatus: invalidated\ninvalidation_reason: \"$reason\"/" "$filepath"
            # Only replace the first occurrence (opening delimiter)
            # Actually, let's do this more carefully
            local tmp=$(mktemp)
            awk -v reason="$reason" '
                BEGIN { count=0 }
                /^---$/ {
                    count++
                    if (count == 2) {
                        print "status: invalidated"
                        print "invalidation_reason: \"" reason "\""
                    }
                }
                { print }
            ' "$filepath" > "$tmp"
            mv "$tmp" "$filepath"
            git -C "$REPO_ROOT" add "$filepath"
            git -C "$REPO_ROOT" commit -m "truss: invalidate $doc — $reason"
            echo -e "${RED}Document invalidated.${NC}"
            ;;
        s|S)
            echo -e "${YELLOW}Skipped.${NC}"
            ;;
        *)
            echo -e "${RED}Unknown action, skipping.${NC}"
            ;;
    esac
    echo ""
}

# Re-pin all internal references in a document to current HEAD hashes
repin_document() {
    local filepath="$1"
    local tmp=$(mktemp)

    # Process the file: update pin lines that follow ref lines pointing to internal docs
    local pending_ref=""
    while IFS= read -r line; do
        # Track ref lines
        if [[ "$line" =~ ^([[:space:]]*-?[[:space:]]*)ref:[[:space:]]*(ground/|hypothetical/|generic/)(.+)$ ]]; then
            pending_ref="${BASH_REMATCH[2]}${BASH_REMATCH[3]}"
            pending_ref="${pending_ref%"${pending_ref##*[![:space:]]}"}"
            echo "$line" >> "$tmp"
            continue
        fi

        # If we have a pending ref and hit a pin line, update it
        if [[ -n "$pending_ref" && "$line" =~ ^([[:space:]]*)pin:[[:space:]]*[a-f0-9]+ ]]; then
            local indent="${BASH_REMATCH[1]}"
            local new_hash
            new_hash=$(git -C "$REPO_ROOT" log -1 --format='%h' -- "$pending_ref" 2>/dev/null || echo "0000000")
            echo "${indent}pin: $new_hash" >> "$tmp"
            pending_ref=""
            continue
        fi

        # Any other line clears pending ref
        if [[ ! "$line" =~ ^[[:space:]]*$ ]]; then
            pending_ref=""
        fi

        echo "$line" >> "$tmp"
    done < "$filepath"

    mv "$tmp" "$filepath"
}

# Main resolution loop
max_rounds=${#stale_docs[@]}
round=0
while [[ ${#remaining[@]} -gt 0 && $round -lt $max_rounds ]]; do
    round=$((round + 1))
    echo -e "${BLUE}Resolution round $round${NC}"
    resolve_round || break
done

if [[ ${#remaining[@]} -gt 0 ]]; then
    echo ""
    echo -e "${YELLOW}Unresolved documents remaining:${NC}"
    for doc in "${remaining[@]}"; do
        echo "  - $doc"
    done
fi

# Rebuild deps after resolution
echo ""
echo "Rebuilding dependency index..."
bash "$REPO_ROOT/scripts/build-deps.sh"

echo ""
echo -e "${GREEN}Resolution complete.${NC}"
