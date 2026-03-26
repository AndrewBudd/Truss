Research a topic and draft ground documents from findings.

The user wants to build the factual foundation of the knowledge base. Your job is to research the given topic and produce one or more **ground** documents capturing observable facts.

Steps:

1. **Understand the topic**: Parse the user's request. What system, API, technology, or domain are they asking about?

2. **Research**: Use web search and web fetch to gather factual information. Focus on:
   - Official documentation and specifications
   - API surfaces, constraints, and behaviors
   - Configuration options and limits
   - Version-specific details (pin to specific versions when possible)

3. **Structure findings**: Group facts into logical ground documents. Each document should cover one cohesive topic. Don't make them too broad.

4. **Draft documents**: For each ground document:
   - Generate an ID (g-* prefix, kebab-case)
   - Write a clear title
   - List all evidence sources (URLs, citations)
   - Write the body with structured sections and concrete details
   - Include specific numbers, limits, and constraints — not vague summaries

5. **Write files**: Save each document to `ground/` with proper frontmatter including `layout: document`.

6. **Validate**: Run `python3 scripts/truss.py validate` and `python3 scripts/truss.py build-deps`.

7. **Report**: Show the user what was created and suggest hypothetical documents that could build on these facts.

If the user provides a topic as an argument (e.g., `/truss-research firecracker vsock support`), start researching immediately.

$ARGUMENTS
