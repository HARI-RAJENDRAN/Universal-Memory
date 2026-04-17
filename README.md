# Unimem: Memory-Augmented AI System

`unimem` is a research-grade, **memory-augmented generation layer** for LLM applications. Engineered using industry-standard open-source components—**FastAPI**, **PostgreSQL + pgvector**, **SQLAlchemy**, **sentence-transformers**, and **Ollama** (`llama2`)—this system enables strict per-user context augmentation to solve the "amnesia" problem inherent in base LLM models.

## Features

- **Semantic Retrieval API** (`POST /add`, `POST /chat`, `GET /memory/{user_id}`, `GET /explain`)
- **Multi-Tenant State Isolation** (Every query routes strictly to an isolated `user_id` vector space)
- **Context Tagging Topologies** (Automatically tags memories like `food:pizza` to natively isolate overlapping semantic scopes)
- **Security Hardening** (DDOS Rate Limits built-in natively, blocking `ignore previous...` Prompt Injection jailbreaks directly from mapping)
- **High-Dimensional Embedding Space** (pgvector, cosine distance utilizing `all-MiniLM-L6-v2`)
- **Dynamic Composite Ranking**: \(Weights configurable via `MemoryConfig`, default $0.6 \cdot \text{similarity} + 0.3 \cdot \text{recency} + 0.1 \cdot \text{frequency}$\)
- **Explainability Arrays**: Granular decoupling of Similarity, Recency, and Frequency metrics dynamically accessible via APIs or natively via `<debug=True>`.
- **Deduplication Engine**: Highly related user facts are dynamically merged to normalize the embedding cluster and log repetition.
- **Smart Response Caching**: Native offline Bypass loops mapping simple queries offline securely in 0.00ms (`use_llm=False` compatible).
- **Graceful Failover Semantics**: Hardened AI integrations that flawlessly fallback to structured raw semantic retrieval payloads in the event of timeouts.
- **Interactive Testing CLI**: A feature-rich `chatbot.py` interface featuring ANSI coloring, hot-swappable user scopes, and interactive debug rankings.

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

## Project Evolution & Version History

Our primary objective was to transform the original `unimem` concept into a **professional, production-ready, memory-augmented generation layer** for local LLMs (like Ollama). 

Here are the key upgrades we successfully engineered:
- **Clean Service Architecture Refactor:** We overhauled the codebase structure, splitting the monolithic logic into distinct, modular service layers: `MemoryService` (ingestion/deduplication), `RetrievalService` (semantic search/ranking), and `LLMService` (prompt generation/fallback logic). 
- **Dynamic Composite Ranking & Deduplication:** We advanced the vector search from basic similarity. The system now scores retrieved memories using a formula of **Similarity + Recency + Frequency**. Simultaneously, we integrated a deduplication engine that dynamically clusters and merges repetitive facts to keep the user's vector space clean.
- **Configuration & Diagnostics:** We added a robust configuration object (`MemoryConfig`) that allows you to easily dictate vector dimensions and retrieval thresholds. We also set up custom logging hooks for clean stdout diagnostics.
- **Resilient LLM Integration:** We enhanced the prompt engineering for more natural personalization. Furthermore, we built inside graceful failover mechanisms: if the local Ollama LLM times out or is offline, the backend seamlessly degrades to returning the raw semantic payloads instead of crashing.
- **Interactive UI (`chatbot.py`):** We rewrote the testing CLI, outfitting it with ANSI colors and built-in commands (`switch user <id>`, `show memory`, `clear memory`, `debug on`).

### Project Version Types

Based on the repository's history and structure, you will notice three distinct "versions" or states of the project within the filesystem:

#### 1. `package#UNIMOM` *(The Original Prototype)*
- **What it is:** The earliest working proof-of-concept.
- **Characteristics:** Contains a very basic implementation of the storage logic and the original legacy `chatbot.py` loop. It acts as the initial "rough draft" that proved we could connect PostgreSQL + pgvector + Ollama, though it lacks the advanced deduplication and clean architectures.

#### 2. `unimem_release_v1` *(The First Packaged Release)*
- **What it is:** The milestone 1 stable baseline.
- **Characteristics:** This directory represents when we successfully bundled the system into a publishable Python package. It contains the `dist` folder and the wheel files making it ready for someone to type `pip install unimem` and use it as a standard library, but prior to some of our latest architectural deep-cleaning.

#### 3. Root Workspace *(The Current Production Build)*
- **What it is:** The latest, fully upgraded, research-grade architecture.
- **Characteristics:** This is the active culmination of all the upgrades. It features the advanced service layers (`unimem/core`, `unimem/services`, `unimem/retrieval`), the dynamic algorithmic ranking, Docker readiness (`docker-compose.yml` for the postgres instance), and the feature-rich, colorful command-line chatbot you can run to visualize the AI's thought processes.

## License

Use and modify freely.
