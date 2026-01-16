# rag/retriever.py
import json
from pathlib import Path
from typing import List, Dict


class RagRetriever:
    """
    Placeholder RAG retriever.
    Later: connect to a real vector store (e.g. Chroma / FAISS).
    """

    def __init__(self, index_path: str):
        """Store the index path for later retrieval setup."""
        self.index_path = index_path
        path = Path(index_path)
        index_file = path / "index.json" if path.is_dir() else path
        if index_file.is_file():
            with index_file.open("r", encoding="utf-8") as f:
                self.index = json.load(f)
        else:
            self.index = []

    def retrieve(self, query: str, k: int = 3) -> List[Dict]:
        """
        Returns a list of document dicts like:
        [{"id": "doc1", "text": "..."}]
        """

        # TODO: implement real retrieval logic.
        # For now we just return dummy docs.
        return [
            {"id": "doc1", "text": f"Dummy context for query: {query}"},
            {"id": "doc2", "text": "Another dummy document about harbor life."}
        ][:k]
