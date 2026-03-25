#!/usr/bin/env bash
# validate.sh — Validate Truss documents against kind-specific rules.
# Checks frontmatter structure, reference rules, and kind constraints.
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

errors=0
warnings=0
checked=0

error() { echo -e "  ${RED}ERROR:${NC} $1"; errors=$((errors + 1)); }
warn() { echo -e "  ${YELLOW}WARN:${NC} $1"; warnings=$((warnings + 1)); }
ok() { echo -e "  ${GREEN}OK:${NC} $1"; }

# Extract a frontmatter field value (simple single-line values only)
fm_field() {
    local file="$1"
    local field="$2"
    local in_fm=0
    local past_delim=0
    while IFS= read -r line; do
        if [[ "$line" == "---" ]]; then
            if [[ $past_delim -eq 0 ]]; then past_delim=1; in_fm=1; continue; fi
            break
        fi
        [[ $in_fm -eq 0 ]] && continue
        if [[ "$line" =~ ^${field}:[[:space:]]*(.+)$ ]]; then
            echo "${BASH_REMATCH[1]}"
            return
        fi
    done < "$file"
}

# Check if frontmatter contains a given block (assumes:, evidence:)
fm_has_block() {
    local file="$1"
    local block="$2"
    local in_fm=0
    local past_delim=0
    while IFS= read -r line; do
        if [[ "$line" == "---" ]]; then
            if [[ $past_delim -eq 0 ]]; then past_delim=1; in_fm=1; continue; fi
            break
        fi
        [[ $in_fm -eq 0 ]] && continue
        if [[ "$line" =~ ^${block}: ]]; then
            return 0
        fi
    done < "$file"
    return 1
}

# Check refs in a document — returns types of refs found
check_refs() {
    local file="$1"
    local kind="$2"
    local in_fm=0
    local past_delim=0
    local in_assumes=0
    local in_evidence=0

    while IFS= read -r line; do
        if [[ "$line" == "---" ]]; then
            if [[ $past_delim -eq 0 ]]; then past_delim=1; in_fm=1; continue; fi
            break
        fi
        [[ $in_fm -eq 0 ]] && continue

        # Track which block we're in
        if [[ "$line" =~ ^assumes: ]]; then in_assumes=1; in_evidence=0; continue; fi
        if [[ "$line" =~ ^evidence: ]]; then in_evidence=1; in_assumes=0; continue; fi
        if [[ "$line" =~ ^[a-z] && ! "$line" =~ ^[[:space:]] ]]; then in_assumes=0; in_evidence=0; fi

        # Check ref lines for rule violations
        if [[ "$line" =~ ref:[[:space:]]*(ground/|hypothetical/|generic/)(.+)$ ]]; then
            local ref_kind="${BASH_REMATCH[1]%/}"
            local ref_target="${BASH_REMATCH[1]}${BASH_REMATCH[2]}"
            ref_target="${ref_target%"${ref_target##*[![:space:]]}"}"

            # Ground documents cannot have assumes (internal refs)
            if [[ "$kind" == "ground" && $in_assumes -eq 1 ]]; then
                error "Ground document has assumes reference to $ref_target"
            fi

            # Ground documents should not reference internal docs as evidence
            if [[ "$kind" == "ground" && $in_evidence -eq 1 ]]; then
                error "Ground document references internal doc $ref_target as evidence"
            fi

            # Check that referenced file exists
            if [[ ! -f "$REPO_ROOT/$ref_target" ]]; then
                error "Referenced file does not exist: $ref_target"
            fi

            # Check pin exists for internal refs
            # (simplified: just check next line has pin)
        fi
    done < "$file"
}

echo "Validating Truss documents..."
echo ""

for dir in ground hypothetical generic; do
    dirpath="$REPO_ROOT/$dir"
    [[ -d "$dirpath" ]] || continue

    while IFS= read -r -d '' file; do
        relpath="${file#$REPO_ROOT/}"
        checked=$((checked + 1))
        echo "Checking: $relpath"

        # Check frontmatter exists
        first_line=$(head -1 "$file")
        if [[ "$first_line" != "---" ]]; then
            error "Missing YAML frontmatter"
            continue
        fi

        # Check kind field
        kind=$(fm_field "$file" "kind")
        if [[ -z "$kind" ]]; then
            error "Missing 'kind' field in frontmatter"
            continue
        fi

        # Check kind matches directory
        expected_kind="$dir"
        if [[ "$kind" != "$expected_kind" ]]; then
            error "Kind '$kind' does not match directory '$dir'"
        fi

        # Check required fields
        id=$(fm_field "$file" "id")
        title=$(fm_field "$file" "title")
        created=$(fm_field "$file" "created")

        [[ -z "$id" ]] && error "Missing 'id' field"
        [[ -z "$title" ]] && error "Missing 'title' field"
        [[ -z "$created" ]] && error "Missing 'created' field"

        # Kind-specific validation
        case "$kind" in
            ground)
                if ! fm_has_block "$file" "evidence"; then
                    warn "Ground document has no evidence block"
                fi
                if fm_has_block "$file" "assumes"; then
                    error "Ground document must not have 'assumes' block"
                fi
                ;;
            hypothetical)
                if ! fm_has_block "$file" "assumes"; then
                    warn "Hypothetical document has no assumes block"
                fi
                ;;
            generic)
                param=$(fm_field "$file" "parameter")
                if [[ -z "$param" ]]; then
                    warn "Generic document has no 'parameter' field"
                fi
                ;;
        esac

        # Check reference rules
        check_refs "$file" "$kind"

    done < <(find "$dirpath" -name '*.md' -print0 2>/dev/null)
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Checked: $checked documents"
echo -e "Errors:  ${RED}$errors${NC}"
echo -e "Warnings: ${YELLOW}$warnings${NC}"

if [[ $errors -gt 0 ]]; then
    echo -e "${RED}Validation failed.${NC}"
    exit 1
fi

echo -e "${GREEN}Validation passed.${NC}"
exit 0
