Review a specific Truss document for quality, completeness, and correctness.

The user wants a critical review of a document. If they provide a filename or ID as an argument, use that. Otherwise, ask which document to review.

Review process:

1. **Read the document** and all documents it references (assumes/evidence).

2. **Structural review**:
   - Is the frontmatter complete and correct?
   - Are all assumes entries pinned?
   - Do evidence links look valid?

3. **Content review**:
   - Does the body support the claims made?
   - For ground docs: are the facts specific and verifiable? Any vague claims that should be pinned down?
   - For hypothetical docs: does the reasoning follow from the assumes? Are there hidden assumptions not listed in assumes?
   - For generic docs: is the parameter well-defined? Would the claims hold for all instances of the parameter?

4. **Completeness**:
   - Are there aspects of the topic not covered that should be?
   - Should this document be split into multiple docs?
   - Are there existing documents that should be referenced but aren't?

5. **Suggest improvements**: Provide specific, actionable suggestions. Offer to implement them.

$ARGUMENTS
