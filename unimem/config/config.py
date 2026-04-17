"""Configuration module for the memory-augmented AI system."""

from dataclasses import dataclass

@dataclass
class MemoryConfig:
    """Core configuration for semantic retrieval and memory isolation."""
    top_k: int = 5
    dedup_threshold: float = 0.85
    weight_similarity: float = 0.6
    weight_recency: float = 0.3
    weight_frequency: float = 0.1
    max_memories_per_user: int = 500
    trust_storage_threshold: float = 0.1
    trust_retrieval_threshold: float = 0.5
    max_memory_per_minute: int = 5
    use_llm: bool = True
