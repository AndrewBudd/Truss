#!/usr/bin/env bash
#
# truss-init.sh — Initialize a new Truss project from the template.
#
# Usage:
#   ./truss-init.sh <project-name>
#
# This creates a new directory with the Truss framework files (scripts/,
# .truss/config.yaml, .gitignore, README) but does NOT copy any sample
# documents. Kind directories are created with .gitkeep files only.

set -euo pipefail

if [ $# -lt 1 ]; then
    echo "Usage: $0 <project-name>"
    echo ""
    echo "Creates a new Truss project directory with the framework scaffolding."
    exit 1
fi

PROJECT_NAME="$1"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -d "$PROJECT_NAME" ]; then
    echo "Error: directory '$PROJECT_NAME' already exists."
    exit 1
fi

echo "Initializing new Truss project: $PROJECT_NAME"

# Create project structure
mkdir -p "$PROJECT_NAME"/{scripts,.truss,ground,hypothetical,generic}

# Copy the CLI script
cp "$SCRIPT_DIR/scripts/truss.py" "$PROJECT_NAME/scripts/truss.py"
chmod +x "$PROJECT_NAME/scripts/truss.py"

# Create .gitkeep files in kind directories (no sample docs)
touch "$PROJECT_NAME/ground/.gitkeep"
touch "$PROJECT_NAME/hypothetical/.gitkeep"
touch "$PROJECT_NAME/generic/.gitkeep"

# Create .truss/config.yaml
cat > "$PROJECT_NAME/.truss/config.yaml" << 'YAML'
# Truss project configuration
version: "1.0"

# Document kind directories
kinds:
  ground: ground/
  hypothetical: hypothetical/
  generic: generic/

# Generated artifact paths
generated:
  deps: .truss/deps.yaml
  stale: .truss/stale.yaml

# Remote Truss repositories
# Register with: python3 scripts/truss.py add-remote <name> <url>
remotes: {}

# Validation settings
validation:
  # Require evidence on ground documents
  require_ground_evidence: true
  # Require assumes on hypothetical documents
  require_hypothetical_assumes: true
  # Require parameter on generic documents
  require_generic_parameter: true
YAML

# Create .gitignore
cat > "$PROJECT_NAME/.gitignore" << 'GITIGNORE'
# Generated artifacts (rebuilt by scripts)
.truss/deps.yaml
.truss/stale.yaml
GITIGNORE

# Create README
cat > "$PROJECT_NAME/README.md" << README
# $PROJECT_NAME

A knowledge base built with the [Truss](https://github.com/your-org/Truss) framework.

## Quick Start

\`\`\`bash
# Create documents
python3 scripts/truss.py new ground g-example "Example Ground Document"
python3 scripts/truss.py new hypothetical h-example "Example Hypothesis"

# Validate all documents
python3 scripts/truss.py validate

# Build the reverse dependency index
python3 scripts/truss.py build-deps

# Detect stale references
python3 scripts/truss.py detect-stale
\`\`\`

## Document Kinds

| Kind | Directory | Answers |
|------|-----------|---------|
| **Ground** | \`ground/\` | "What is the case?" |
| **Hypothetical** | \`hypothetical/\` | "What follows from what we know?" |
| **Generic** | \`generic/\` | "What is generally true about things like this?" |
README

# Initialize git and make initial commit
cd "$PROJECT_NAME"
git init --quiet
git add .
git commit --quiet -m "Initialize Truss project"

echo ""
echo "Truss project created at: $(pwd)"
echo ""
echo "Next steps:"
echo "  cd $PROJECT_NAME"
echo "  python3 scripts/truss.py new ground g-example \"My First Ground Document\""
