import chromadb

from app.config import settings


class VectorStore:
    """
    Persistent ChromaDB storage for annual-report chunks.
    """

    def __init__(self):
        self.client = chromadb.PersistentClient(
            path=str(settings.chroma_path)
        )

        self.collection = self.client.get_or_create_collection(
            name="financial_document_chunks"
        )

    def delete_document_chunks(self, document_id: int) -> None:
        records = self.collection.get(
            where={"document_id": document_id}
        )

        if records["ids"]:
            self.collection.delete(ids=records["ids"])

    def add_chunks(self, chunks: list[dict]) -> None:
        if not chunks:
            return

        self.collection.add(
            ids=[chunk["chunk_id"] for chunk in chunks],
            documents=[chunk["text"] for chunk in chunks],
            metadatas=[
                {
                    "document_id": chunk["document_id"],
                    "session_id": chunk["session_id"],
                    "page": chunk["page"],
                    "company_name": chunk["company_name"],
                    "fiscal_year": chunk["fiscal_year"],
                }
                for chunk in chunks
            ],
        )

    def search_document(
        self,
        document_id: int,
        query: str,
        limit: int = 5,
    ) -> list[dict]:
        result = self.collection.query(
            query_texts=[query],
            n_results=limit,
            where={"document_id": document_id},
        )

        documents = result.get("documents", [[]])[0] or []
        metadatas = result.get("metadatas", [[]])[0] or []

        return [
            {
                "text": document,
                "page": metadata["page"],
                "document_id": metadata["document_id"],
                "metadata": metadata,
            }
            for document, metadata in zip(documents, metadatas)
        ]

    def search_session(
        self,
        session_id: int,
        query: str,
        limit: int = 10,
    ) -> list[dict]:
        result = self.collection.query(
            query_texts=[query],
            n_results=limit,
            where={"session_id": session_id},
        )

        documents = result.get("documents", [[]])[0] or []
        metadatas = result.get("metadatas", [[]])[0] or []

        return [
            {
                "text": document,
                "page": metadata["page"],
                "document_id": metadata["document_id"],
                "metadata": metadata,
            }
            for document, metadata in zip(documents, metadatas)
        ]