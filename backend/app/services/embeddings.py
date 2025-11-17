"""
Embedding Service - Generates embeddings for code using sentence-transformers.

Uses a pre-trained model optimized for code understanding.
"""

from typing import List, Union
from sentence_transformers import SentenceTransformer
import numpy as np


class EmbeddingService:
    """Generate embeddings for code snippets and queries."""

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        """
        Initialize the embedding service.

        Args:
            model_name: Name of the sentence-transformers model to use.
                       Default is a lightweight model good for general text.
                       For code, consider: "microsoft/codebert-base"
        """
        print(f"Loading embedding model: {model_name}")
        self.model = SentenceTransformer(model_name)
        print(f"Model loaded successfully")

    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector as list of floats
        """
        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding.tolist()

    def generate_embeddings(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in batches.

        Args:
            texts: List of texts to embed
            batch_size: Number of texts to process in each batch

        Returns:
            List of embedding vectors
        """
        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            convert_to_numpy=True,
            show_progress_bar=True
        )
        return [emb.tolist() for emb in embeddings]

    def prepare_code_text(self, code_node) -> str:
        """
        Prepare text from a code node for embedding.

        Combines signature, docstring, and code in a way that's good for embedding.

        Args:
            code_node: CodeNode object from AST parser

        Returns:
            Formatted text for embedding
        """
        parts = []

        # Add signature (most important)
        if code_node.signature:
            parts.append(code_node.signature)

        # Add docstring if available
        if code_node.docstring:
            parts.append(code_node.docstring)

        # Add a snippet of the code (first few lines)
        if code_node.code:
            code_lines = code_node.code.split('\n')
            # Take first 10 lines or full code if shorter
            code_snippet = '\n'.join(code_lines[:min(10, len(code_lines))])
            parts.append(code_snippet)

        # Add file path context
        parts.append(f"File: {code_node.file_path}")

        return '\n'.join(parts)

    def get_embedding_dimension(self) -> int:
        """Get the dimension of embeddings produced by this model."""
        # Generate a dummy embedding to get the dimension
        dummy_embedding = self.generate_embedding("test")
        return len(dummy_embedding)
