# Unimem: Memory-Augmented AI System

`unimem` is a research-grade, **memory-augmented generation layer** for LLM applications. Engineered using industry-standard open-source components—**FastAPI**, **PostgreSQL + pgvector**, **SQLAlchemy**, **sentence-transformers**, and **Ollama** (`llama2`)—this system enables strict per-user context augmentation to solve the "amnesia" problem inherent in base LLM models.

## Features

- **Semantic Retrieval API** (`POST /add`, `POST /chat`, `GET /memory/{user_id}`)
- **Multi-Tenant State Isolation** (every query routes strictly to an isolated `user_id` vector space)
- **High-Dimensional Embedding Space** (pgvector, cosine distance utilizing `all-MiniLM-L6-v2`)
- **Dynamic Composite Ranking**: \(Weights configurable via `MemoryConfig`, default $0.6 \cdot \text{similarity} + 0.3 \cdot \text{recency} + 0.1 \cdot \text{frequency}$\)
- **Deduplication Engine**: Highly related user facts are merged dynamically to normalize the embedding cluster and log temporal frequencies.
- **Context-Aware Generation**: Transparently injects the retrieved context via a seamless prompt engineered system utilizing a local LLM via Ollama (No API Keys required).
- **Graceful Failover Semantics**: Hardened LLM integrations that flawlessly fallback to raw semantic retrieval payloads in the event of LLM timeouts.

## System Architecture

```text
+----------------+      [HTTP API / FastAPI]      +------------------+
|   End User     |  <-------------------------->  |  MemoryClient    |
+----------------+                                +--------+---------+
                                                           |
                      +------------------------------------+-----------------------------------+
                      |                                    |                                   |
             [MemoryService]                      [RetrievalService]                     [LLMService]
             - Ingestion                          - Semantic Search                      - Prompt Gen
             - Deduplication                      - Recency Scaling                      - Fallback
             - Deletion                           - Composite Ranking                    - Ollama Call
                      |                                    |                                   |
                      +------------------+-----------------+                                   |
                                         |                                                     |
+----------------------+        +--------v---------+                               +-----------v----------+
| sentence-transformers|  <---> | PostgreSQL       |        [Local Ollama] <------>|  LocalLLMClient      |
| all-MiniLM-L6-v2     |        | with pgvector    |                               +----------------------+
+----------------------+        +------------------+
```

## Quick start

### 1) Initialize the Vector Database

```bash
docker compose up -d
```
Default connection (override with `DATABASE_URL`): `postgresql://mem0:mem0@localhost:5432/unimem`

### 2) Install Local Dependencies

```bash
pip install unimem
```

### 3) Model Caching

```bash
ollama pull llama2
```

### 4) Deployment Modes

**Run standard API**:
```bash
uvicorn unimem.api.app:app --reload --host 0.0.0.0 --port 8000
```
**Access via Library (`MemoryClient`)**:
The orchestration layer unites `RetrievalService`, `MemoryService` and `LLMService`.

```python
from unimem.db.session import init_engine, get_session_factory
from unimem.db.bootstrap import ensure_pgvector_extension, create_all_tables
from unimem.core.memory_client import MemoryClient
from unimem.config.config import MemoryConfig

init_engine()
ensure_pgvector_extension()
create_all_tables()

db = get_session_factory()()
try:
    client = MemoryClient(db, config=MemoryConfig(top_k=5))
    
    # Intelligently deduplicate and augment knowledge base
    client.add("I specialize in Python systems architecture.", user_id="dev_1")
    
    # Retrieve optimal semantic vectors and auto-generate via Ollama
    print(client.chat("What do I specialize in?", user_id="dev_1"))
    
    # Directly query the semantic engine
    print(client.search("Architecture", user_id="dev_1"))
finally:
    db.close()
```

## Logging and Configurations

A configuration hook `MemoryConfig` dictates vector thresholds. Structured diagnostics (including dynamic ranking tracking, merges, updates, and failover notifications) are pushed out via standard stdout hooks established in `logger.py`.

## License

Use and modify freely.
