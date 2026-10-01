import chromadb

from app.config import settings


class VectorStore:
    """
    Stores document chunks and metadata in ChromaDB.
    This makes the annual report searchable for future Research Agent work.
    """

    def __init__(self):
        self.client = chromadb.PersistentClient(path=str(settings.chroma_path))
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
        limit: int = 8,
    ) -> list[dict]:
        result = self.collection.query(
            query_texts=[query],
            n_results=limit,
            where={"document_id": document_id},
        )

        chunks = []

        for document, metadata in zip(
            result["documents"][0],
            result["metadatas"][0],
        ):
            chunks.append(
                {
                    "text": document,
                    "page": metadata["page"],
                    "metadata": metadata,
                }
            )

        return chunks