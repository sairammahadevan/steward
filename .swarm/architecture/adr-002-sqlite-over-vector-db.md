# ADR-002: Use SQLite Over Vector Database

## Status
Accepted

## Context
RAG Control Plane used Qdrant (vector DB) for semantic search over document chunks.
This required running a separate Qdrant server, managing embeddings, and handling
chunking strategies — significant complexity that contributed to the project stalling.

For STEWARD, the retrieval problem is different. The user has ~50-200 personal
documents (warranties, legal docs, service records). The question is not "find
the needle in 10,000 haystacks" — it's "find the right document from a known,
small, well-indexed collection."

## Decision
Use SQLite via Python's built-in `sqlite3` module as the sole data store.

Each ingested document produces one structured metadata card stored as a row.
Document retrieval for queries uses simple keyword and tag matching against
the SQLite index, not vector similarity search.

No embeddings. No vector store. No Qdrant. No ChromaDB.

## Consequences
**Good:**
- Zero additional infrastructure — SQLite is built into Python
- Instant startup, no server process to manage
- Database is a single file — easy to back up, inspect, and move
- Sufficient for the actual retrieval problem at personal document scale
- No chunking strategy decisions needed

**Bad:**
- Cannot do semantic/fuzzy search across document content
- If the collection grows beyond ~500 documents, keyword matching may feel limited
- No ranked relevance scoring — matching is boolean

**Neutral:**
- Vector search can be added in a future MVP if needed
- SQLite handles concurrent reads fine; write locking is acceptable at personal scale
