Show a quick overview of the Truss knowledge base.

Provide a concise status dashboard:

1. Run `python3 scripts/truss.py build-deps` and `python3 scripts/truss.py detect-stale` (capture output, don't fail on stale).

2. Count documents by kind (list the ground/, hypothetical/, generic/ directories).

3. Read `.truss/deps.yaml` and summarize the dependency graph:
   - How many cross-references exist
   - Which documents are most referenced
   - Any orphan documents (no incoming or outgoing refs)

4. Report staleness: how many stale refs, which documents affected.

5. Show a text-based dependency graph using indentation or ASCII art. Keep it compact.

Format the output as a clean dashboard the user can scan in 10 seconds.
