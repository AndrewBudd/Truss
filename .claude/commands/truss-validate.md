Validate the entire Truss knowledge base and provide a detailed report.

Run all validation checks and present results in a human-friendly format:

1. **Structural validation**: Run `python3 scripts/truss.py validate` and report results.

2. **Staleness check**: Run `python3 scripts/truss.py detect-stale` and report any stale pins. For each stale reference, explain what changed and suggest whether to confirm, update, or investigate.

3. **Dependency analysis**: Run `python3 scripts/truss.py build-deps` and read `.truss/deps.yaml`. Report:
   - Total document count by kind
   - Documents with no dependents (leaf nodes)
   - Documents with no dependencies (root nodes)
   - Most-referenced documents

4. **Content quality review** (quick pass):
   - Read each document and flag any that have TODO placeholders
   - Flag documents with very short bodies (< 5 lines of content)
   - Flag hypothetical docs whose body doesn't reference their assumes entries

5. **Summary**: Present an overall health score and prioritized list of things to fix.

No arguments needed — this always operates on the entire knowledge base.
