"""
Semantic Code Index - Uses ChromaDB for vector-based semantic search.

Combines AST parsing, embeddings, and vector search to find relevant code.
"""

from typing import List, Optional
from dataclasses import dataclass
from pathlib import Path
import chromadb
from chromadb.config import Settings

from app.services.ast_parser import ASTParser, CodeNode
from app.services.embeddings import EmbeddingService


@dataclass
class SearchResult:
    """Represents a search result with relevance score."""
    code_node: CodeNode
    score: float  # Similarity score (higher is better)
    rank: int


class SemanticCodeIndex:
    """
    Semantic code index using ChromaDB for vector search.

    Provides high-quality context for LLMs by finding the most relevant code.
    """

    def __init__(self, workspace_path: str, collection_name: str = "code_index"):
        """
        Initialize the semantic code index.

        Args:
            workspace_path: Path to the code repository
            collection_name: Name for the ChromaDB collection
        """
        self.workspace_path = workspace_path
        self.collection_name = collection_name

        # Initialize services
        self.ast_parser = ASTParser()
        self.embedding_service = EmbeddingService()

        # Initialize ChromaDB (in-memory for simplicity, can be persistent)
        self.client = chromadb.Client(Settings(
            anonymized_telemetry=False,
            allow_reset=True
        ))

        # Create or get collection
        try:
            self.collection = self.client.get_collection(name=collection_name)
            print(f"Loaded existing collection: {collection_name}")
        except Exception:
            self.collection = self.client.create_collection(
                name=collection_name,
                metadata={"description": "Code embeddings for semantic search"}
            )
            print(f"Created new collection: {collection_name}")

        # Storage for code nodes (ChromaDB has limited metadata storage)
        self.code_nodes: List[CodeNode] = []

    def build_index(self) -> None:
        """
        Build the semantic index by parsing the workspace and generating embeddings.

        This is the main method to call after initialization.
        """
        print(f"Building semantic index for workspace: {self.workspace_path}")

        # Step 1: Parse all Python files using AST
        print("Step 1: Parsing code with tree-sitter...")
        self.code_nodes = self.ast_parser.parse_workspace(self.workspace_path)
        print(f"Found {len(self.code_nodes)} code nodes")

        if not self.code_nodes:
            print("Warning: No code nodes found in workspace")
            return

        # Step 2: Prepare texts for embedding
        print("Step 2: Preparing texts for embedding...")
        texts = [self.embedding_service.prepare_code_text(node) for node in self.code_nodes]

        # Step 3: Generate embeddings
        print("Step 3: Generating embeddings...")
        embeddings = self.embedding_service.generate_embeddings(texts)

        # Step 4: Store in ChromaDB
        print("Step 4: Storing in ChromaDB...")
        ids = [f"node_{i}" for i in range(len(self.code_nodes))]

        # Create metadata for each node
        metadatas = []
        for node in self.code_nodes:
            metadatas.append({
                "type": node.type,
                "name": node.name,
                "file_path": node.file_path,
                "start_line": node.start_line,
                "end_line": node.end_line,
            })

        # Add to collection
        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=texts,  # Store the text for reference
            metadatas=metadatas
        )

        print(f"Index built successfully with {len(self.code_nodes)} nodes")

    def search(self, query: str, max_results: int = 10, min_score: float = 0.0) -> List[SearchResult]:
        """
        Search for relevant code using semantic similarity.

        Args:
            query: Natural language query or bug description
            max_results: Maximum number of results to return
            min_score: Minimum similarity score (0-1, higher is better)

        Returns:
            List of SearchResult objects, sorted by relevance
        """
        if not self.code_nodes:
            print("Warning: Index is empty. Call build_index() first.")
            return []

        # Generate embedding for query
        query_embedding = self.embedding_service.generate_embedding(query)

        # Search in ChromaDB
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=max_results
        )

        # Parse results
        search_results = []
        if results and results['ids'] and len(results['ids']) > 0:
            ids = results['ids'][0]
            distances = results['distances'][0]

            for rank, (id_str, distance) in enumerate(zip(ids, distances), 1):
                # Extract index from id
                idx = int(id_str.split('_')[1])

                # Convert distance to similarity score (ChromaDB returns L2 distance)
                # Lower distance = higher similarity
                # We convert to 0-1 scale where 1 is most similar
                score = 1.0 / (1.0 + distance)

                if score >= min_score:
                    search_results.append(SearchResult(
                        code_node=self.code_nodes[idx],
                        score=score,
                        rank=rank
                    ))

        print(f"Found {len(search_results)} results for query: {query[:50]}...")
        return search_results

    def get_context(self, query: str, max_results: int = 5) -> str:
        """
        Get formatted context for LLM from search results.

        Args:
            query: Query string
            max_results: Maximum number of code snippets to include

        Returns:
            Formatted context string ready for LLM
        """
        results = self.search(query, max_results=max_results)

        if not results:
            return "No relevant code found."

        context_parts = []
        for i, result in enumerate(results, 1):
            node = result.code_node
            context_parts.append(
                f"### Result {i} (relevance: {result.score:.2f}): "
                f"{node.type.capitalize()} '{node.name}' in {node.file_path}\n"
                f"Lines {node.start_line}-{node.end_line}\n"
                f"```python\n{node.code}\n```"
            )

        return "\n\n".join(context_parts)

    def get_stats(self) -> dict:
        """Get statistics about the index."""
        return {
            "total_nodes": len(self.code_nodes),
            "functions": sum(1 for n in self.code_nodes if n.type == 'function'),
            "classes": sum(1 for n in self.code_nodes if n.type == 'class'),
            "imports": sum(1 for n in self.code_nodes if n.type == 'import'),
            "module_level": sum(1 for n in self.code_nodes if n.type == 'module_level'),
            "methods": sum(1 for n in self.code_nodes if n.type == 'method'),
            "collection_count": self.collection.count() if self.collection else 0
        }
