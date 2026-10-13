from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.agents.comparison_agent import ComparisonAgent
from app.agents.report_agent import ReportAgent
from app.agents.research_agent import ResearchAgent
from app.database import get_db
from app.models import Document, FinancialMetric
from app.schemas import ResearchRequest
from app.utils.pdf_report import build_analyst_pdf


router = APIRouter(
    prefix="/analysis",
    tags=["Analysis Agents"],
)


class ComparisonRequest(BaseModel):
    document_ids: list[int] = Field(min_length=2)


def get_documents_or_404(
    db: Session,
    document_ids: list[int],
) -> list[Document]:
    unique_ids = list(set(document_ids))

    documents = (
        db.query(Document)
        .filter(Document.id.in_(unique_ids))
        .all()
    )

    if len(documents) != len(unique_ids):
        raise HTTPException(
            status_code=404,
            detail="One or more selected reports were not found.",
        )

    unfinished = [
        document.original_filename
        for document in documents
        if document.status != "completed"
    ]

    if unfinished:
        raise HTTPException(
            status_code=400,
            detail=(
                "Reports must finish processing before analysis: "
                + ", ".join(unfinished)
            ),
        )

    return documents


@router.post("/research")
def research(
    payload: ResearchRequest,
    db: Session = Depends(get_db),
):
    documents = get_documents_or_404(
        db,
        payload.document_ids,
    )

    if len({document.session_id for document in documents}) != 1:
        raise HTTPException(
            status_code=400,
            detail=(
                "Select reports from one research session for a "
                "single research conversation."
            ),
        )

    metrics = (
        db.query(FinancialMetric)
        .filter(
            FinancialMetric.document_id.in_(
                [document.id for document in documents]
            )
        )
        .all()
    )

    history = [
        {
            "role": item.role,
            "content": item.content,
        }
        for item in payload.history
    ]

    try:
        return ResearchAgent().answer(
            question=payload.question,
            documents=documents,
            metrics=metrics,
            history=history,
        )
    except Exception as error:
        raise HTTPException(
            status_code=503,
            detail=(
                "Research service is temporarily unavailable. "
                f"Details: {str(error)}"
            ),
        ) from error


@router.post("/compare")
def compare(
    payload: ComparisonRequest,
    db: Session = Depends(get_db),
):
    documents = get_documents_or_404(
        db,
        payload.document_ids,
    )

    if len({document.session_id for document in documents}) != 1:
        raise HTTPException(
            status_code=400,
            detail="Select reports from the same research session.",
        )

    metrics = (
        db.query(FinancialMetric)
        .filter(
            FinancialMetric.document_id.in_(
                [document.id for document in documents]
            )
        )
        .all()
    )

    return ComparisonAgent().compare(
        documents=documents,
        metrics=metrics,
    )


@router.get("/report/{document_id}")
def generate_report(
    document_id: int,
    db: Session = Depends(get_db),
):
    document = db.get(Document, document_id)

    if not document:
        raise HTTPException(
            status_code=404,
            detail="Document not found.",
        )

    return ReportAgent().generate(
        document=document,
        metrics=document.metrics,
        red_flags=document.red_flags,
    )


@router.get("/report/{document_id}/pdf")
def download_report_pdf(
    document_id: int,
    db: Session = Depends(get_db),
):
    document = db.get(Document, document_id)

    if not document:
        raise HTTPException(
            status_code=404,
            detail="Document not found.",
        )

    report = ReportAgent().generate(
        document=document,
        metrics=document.metrics,
        red_flags=document.red_flags,
    )

    pdf = build_analyst_pdf(report)

    filename_base = (
        document.company_name
        or document.original_filename.rsplit(".", 1)[0]
    )

    safe_filename = (
        filename_base.replace(" ", "_")
        .replace("/", "_")
        .replace("\\", "_")
    )

    return StreamingResponse(
        pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f'attachment; filename="{safe_filename}_analyst_report.pdf"'
            )
        },
    )