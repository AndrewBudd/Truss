Analyze the knowledge base and suggest connections between documents.

Look for missing links in the dependency graph — places where documents should reference each other but don't.

Steps:

1. Read ALL documents in ground/, hypothetical/, and generic/.

2. For each hypothetical document, check:
   - Are there ground documents it implicitly relies on but doesn't list in assumes?
   - Are there generic documents whose principles apply to its reasoning?
   - Are there other hypothetical documents that share assumptions or build on similar foundations?

3. For each generic document, check:
   - Are there ground documents that provide evidence for or against its claims?
   - Are there hypothetical documents that instantiate this generic principle?

4. Suggest new hypothetical documents that could bridge existing ground and generic docs.

5. Suggest new ground documents that would strengthen existing hypothetical reasoning.

Present findings as a prioritized list of suggested connections. For each suggestion:
- Which documents to connect
- Why the connection matters
- Whether it requires a new document or just adding an assumes entry

Offer to implement the top suggestions.

$ARGUMENTS
