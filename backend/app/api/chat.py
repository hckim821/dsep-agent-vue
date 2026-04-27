import json
import os
import sys
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import SessionLocal, get_db
from app.core.deps import get_current_user
from app.models.chat import ChatMessage, ChatMessageRole, ChatSession
from app.models.ingest import IngestPost, IngestPostType
from app.models.user import User
from app.schemas.chat import (
    ChatMessageCreate,
    ChatMessageOut,
    ChatSessionCreate,
    ChatSessionOut,
)

router = APIRouter(prefix="/api/chat", tags=["chat"])


def _wiki_pipeline_path() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


@router.get("/sessions", response_model=list[ChatSessionOut])
def list_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(ChatSession)
        .filter_by(user_id=current_user.id)
        .order_by(ChatSession.updated_at.desc())
        .all()
    )


@router.post("/sessions", response_model=ChatSessionOut)
def create_session(
    body: ChatSessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = ChatSession(user_id=current_user.id, title=body.title)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.get("/sessions/{session_id}/messages", response_model=list[ChatMessageOut])
def get_messages(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    chat_session = db.get(ChatSession, session_id)
    if not chat_session or chat_session.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Session not found")
    return (
        db.query(ChatMessage)
        .filter_by(session_id=session_id)
        .order_by(ChatMessage.created_at)
        .all()
    )


def _build_chat_system_prompt() -> str:
    if _wiki_pipeline_path() not in sys.path:
        sys.path.insert(0, _wiki_pipeline_path())
    try:
        from wiki_pipeline.wiki_repo import list_pages, read_page

        pages = list_pages()[:10]
        wiki_context = ""
        for p in pages:
            content = read_page(p)
            if content:
                wiki_context += f"\n\n## {p}\n{content[:500]}"
        return (
            "You are a wiki assistant. Answer based on the following wiki content:"
            f"\n{wiki_context}\n\n"
            "Always cite pages with [[Page Title]] notation. "
            "Mark unverified claims with [UNVERIFIED]."
        )
    except Exception:
        return "You are a helpful wiki assistant."


@router.post("/sessions/{session_id}/messages")
async def send_message(
    session_id: int,
    body: ChatMessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    chat_session = db.get(ChatSession, session_id)
    if not chat_session or chat_session.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Session not found")

    user_msg = ChatMessage(
        session_id=session_id, role=ChatMessageRole.user, content=body.content
    )
    db.add(user_msg)
    db.commit()

    history = (
        db.query(ChatMessage)
        .filter_by(session_id=session_id)
        .order_by(ChatMessage.created_at)
        .all()
    )
    messages = [{"role": m.role.value, "content": m.content} for m in history]

    system_content = _build_chat_system_prompt()
    full_messages = [{"role": "system", "content": system_content}] + messages

    async def generate():
        full_response = ""
        try:
            if _wiki_pipeline_path() not in sys.path:
                sys.path.insert(0, _wiki_pipeline_path())
            from wiki_pipeline.llm_client import get_llm_client

            llm = get_llm_client()
            for chunk in llm.stream(full_messages, task="chat"):
                full_response += chunk
                yield f"data: {json.dumps({'delta': chunk})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

        # Persist the assistant message in a fresh session (request session
        # closes once the generator completes).
        try:
            with SessionLocal() as save_db:
                assistant_msg = ChatMessage(
                    session_id=session_id,
                    role=ChatMessageRole.assistant,
                    content=full_response,
                )
                save_db.add(assistant_msg)
                sess = save_db.get(ChatSession, session_id)
                if sess is not None:
                    sess.updated_at = datetime.now(timezone.utc)
                save_db.commit()
        except Exception:
            pass

        yield f"data: {json.dumps({'done': True})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.post("/sessions/{session_id}/to-ingest")
def session_to_ingest(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    chat_session = db.get(ChatSession, session_id)
    if not chat_session or chat_session.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Session not found")

    messages = (
        db.query(ChatMessage)
        .filter_by(session_id=session_id)
        .order_by(ChatMessage.created_at)
        .all()
    )
    conversation = "\n\n".join(
        f"**{m.role.value}**: {m.content}" for m in messages
    )

    if _wiki_pipeline_path() not in sys.path:
        sys.path.insert(0, _wiki_pipeline_path())

    summary = f"# Chat Session Summary\n\n{conversation}"
    try:
        from wiki_pipeline.llm_client import get_llm_client

        llm = get_llm_client()
        resp = llm.complete(
            [
                {
                    "role": "system",
                    "content": "Summarize this conversation as a wiki knowledge document in Korean markdown format.",
                },
                {"role": "user", "content": conversation},
            ],
            task="ingest",
        )
        summary = resp.content
    except Exception:
        pass

    title_base = chat_session.title or f"Session {session_id}"
    post = IngestPost(
        author_id=current_user.id,
        title=f"Chat Summary: {title_base}",
        body_md=summary,
        type=IngestPostType.chat_summary,
        unverified=True,
    )
    db.add(post)
    db.commit()
    db.refresh(post)
    return {"post_id": post.id, "title": post.title}
