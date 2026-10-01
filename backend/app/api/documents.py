from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_db
from app.models import Document, FinancialMetric, ResearchSession
from app.schemas import DocumentResponse, MetricResponse
from app.services.document_service import DocumentService

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.post("/upload", response_model=DocumentResponse)
def upload_document(
    session_id: int = Form(...),
    company_name: str = Form(""),
    fiscal_year: str = Form(""),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")

    session = db.get(ResearchSession, session_id)

    if not session:
        raise HTTPException(status_code=404, detail="Research session not found.")

    contents = file.file.read()
    maximum_size = settings.max_file_size_mb * 1024 * 1024

    if len(contents) > maximum_size:
        raise HTTPException(
            status_code=400,
            detail=f"PDF must be smaller than {settings.max_file_size_mb} MB.",
        )

    stored_filename = f"{uuid4()}_{file.filename}"
    file_path = settings.upload_path / stored_filename

    with open(file_path, "wb") as output_file:
        output_file.write(contents)

    document = Document(
        session_id=session_id,
        original_filename=file.filename,
        stored_filename=stored_filename,
        file_path=str(file_path),
        company_name=company_name.strip() or None,
        fiscal_year=fiscal_year.strip() or None,
        status="uploaded",
    )

    db.add(document)
    db.commit()
    db.refresh(document)

    DocumentService().process_document(db, document)

    return document


@router.get("/session/{session_id}", response_model=list[DocumentResponse])
def list_documents(session_id: int, db: Session = Depends(get_db)):
    return (
        db.query(Document)
        .filter(Document.session_id == session_id)
        .order_by(Document.created_at.desc())
        .all()
    )


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(document_id: int, db: Session = Depends(get_db)):
    document = db.get(Document, document_id)

    if not document:
        raise HTTPException(status_code=404, detail="Document not found.")

    return document


@router.get("/{document_id}/file")
def view_pdf(document_id: int, db: Session = Depends(get_db)):
    document = db.get(Document, document_id)

    if not document or not Path(document.file_path).exists():
        raise HTTPException(status_code=404, detail="PDF file not found.")

    return FileResponse(
        document.file_path,
        media_type="application/pdf",
        filename=document.original_filename,
    )


@router.get("/{document_id}/metrics", response_model=list[MetricResponse])
def get_metrics(document_id: int, db: Session = Depends(get_db)):
    return (
        db.query(FinancialMetric)
        .filter(FinancialMetric.document_id == document_id)
        .order_by(FinancialMetric.metric_name)
        .all()
    )


@router.post("/{document_id}/reprocess", response_model=DocumentResponse)
def reprocess_document(document_id: int, db: Session = Depends(get_db)):
    document = db.get(Document, document_id)

    if not document:
        raise HTTPException(status_code=404, detail="Document not found.")

    return DocumentService().process_document(db, document)
