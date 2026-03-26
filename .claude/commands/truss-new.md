Draft a new Truss document interactively.

Ask the user what they want to document, then determine:

1. **Kind**: Is this an observable fact (ground), conditional reasoning (hypothetical), or a general principle (generic)?
2. **ID**: Generate an appropriate ID (g-*, h-*, or n-* prefix)
3. **Title**: Clear, descriptive title

Then:

1. Draft the full document with proper frontmatter and body content
2. For **ground** docs: identify and list external evidence (URLs, citations, files)
3. For **hypothetical** docs: identify which existing documents it depends on. Read the ground/ and hypothetical/ directories to find relevant docs. Set `assumes:` with proper `ref:` paths and `pin:` values (use `git log -1 --format=%h -- <filepath>` to get current pin for each dependency)
4. For **generic** docs: identify the parameter (what class of thing this applies to) and external evidence

Write the file to the appropriate directory using `python3 scripts/truss.py new <kind> <id> <title>` as a starting point, then overwrite with the full drafted content.

After creating the document:
- Run `python3 scripts/truss.py validate` to check it
- Run `python3 scripts/truss.py build-deps` to update the dependency index
- Show the user the final document and ask if they want to refine it

If the user provides a topic as an argument (e.g., `/truss-new the API rate limiting behavior`), use that as the starting point instead of asking.

$ARGUMENTS
