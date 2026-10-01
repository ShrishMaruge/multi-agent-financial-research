from sqlalchemy.orm import Session

from app.agents.document_agent import DocumentAgent
from app.agents.extraction_agent import ExtractionAgent
from app.models import Document, FinancialMetric
from app.rag.vector_store import VectorStore


class DocumentService:
    """
    Workflow:
    Document Agent -> Extraction Agent
    """

    def __init__(self):
        self.document_agent = DocumentAgent()
        self.extraction_agent = ExtractionAgent()
        self.vector_store = VectorStore()

    def process_document(self, db: Session, document: Document) -> Document:
        try:
            document.status = "parsing"
            document.error_message = None
            db.commit()

            pages = self.document_agent.parse_pdf(document.file_path)
            document.page_count = len(pages)

            document.status = "chunking"
            db.commit()

            chunks = self.document_agent.chunk_pages(
                pages=pages,
                document_id=document.id,
                session_id=document.session_id,
                company_name=document.company_name,
                fiscal_year=document.fiscal_year,
            )

            document.status = "indexing"
            db.commit()

            self.vector_store.delete_document_chunks(document.id)
            self.vector_store.add_chunks(chunks)
            document.chunk_count = len(chunks)

            document.status = "extracting"
            db.commit()

            db.query(FinancialMetric).filter(
                FinancialMetric.document_id == document.id
            ).delete()

            extracted_metrics = self.extraction_agent.run(
                file_path=document.file_path,
                fiscal_year=document.fiscal_year,
            )

            for metric in extracted_metrics:
                db.add(
                    FinancialMetric(
                        document_id=document.id,
                        metric_name=metric["metric_name"],
                        metric_value=metric["metric_value"],
                        period=metric["period"],
                        source_page=metric["source_page"],
                        evidence=metric["evidence"],
                        confidence=metric["confidence"],
                    )
                )

            document.status = "completed"
            db.commit()
            db.refresh(document)

            return document

        except Exception as error:
            document.status = "failed"
            document.error_message = str(error)
            db.commit()
            raise

