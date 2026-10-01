from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ResearchSession
from app.schemas import SessionCreate, SessionResponse

router = APIRouter(prefix="/sessions", tags=["Research Sessions"])


@router.post("", response_model=SessionResponse)
def create_session(payload: SessionCreate, db: Session = Depends(get_db)):
    session = ResearchSession(
        name=payload.name,
        description=payload.description,
    )

    db.add(session)
    db.commit()
    db.refresh(session)

    return session


@router.get("", response_model=list[SessionResponse])
def list_sessions(db: Session = Depends(get_db)):
    return (
        db.query(ResearchSession)
        .order_by(ResearchSession.created_at.desc())
        .all()
    )


@router.get("/{session_id}", response_model=SessionResponse)
def get_session(session_id: int, db: Session = Depends(get_db)):
    session = db.get(ResearchSession, session_id)

    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    return session