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
