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


def _build_chat_system_prompt(db: Session) -> str:
    if _wiki_pipeline_path() not in sys.path:
        sys.path.insert(0, _wiki_pipeline_path())

    # 1) chat_system.md 기본 프롬프트
    base_prompt = "You are a helpful wiki assistant."
    try:
        prompts_dir = os.path.join(_wiki_pipeline_path(), "wiki_pipeline", "prompts")
        chat_md = os.path.join(prompts_dir, "chat_system.md")
        if os.path.exists(chat_md):
            with open(chat_md, encoding="utf-8") as f:
                base_prompt = f.read()
    except Exception:
        pass

    # 2) 현재 활성 schema 주입
    schema_block = ""
    try:
        from app.models.schema_version import SchemaVersion
        latest = (
            db.query(SchemaVersion)
            .order_by(SchemaVersion.updated_at.desc())
            .first()
        )
        if latest and latest.content:
            schema_block = (
                "\n\n## Wiki Schema (active)\n"
                f"{latest.content}"
            )
    except Exception:
        pass

    # 3) 위키 컨텍스트
    wiki_context = ""
    try:
        from wiki_pipeline.wiki_repo import list_pages, read_page
        pages = list_pages()[:10]
        for p in pages:
            content = read_page(p)
            if content:
                wiki_context += f"\n\n### {p}\n{content[:500]}"
    except Exception:
        pass

    return (
        f"{base_prompt}{schema_block}\n\n"
        "## Wiki Content\n"
        f"{wiki_context}\n\n"
        "## Rules\n"
        "- Answer based on the wiki content above.\n"
        "- Cite pages with [[Page Title]] notation when referencing them.\n"
        "- Mark unverified claims with [UNVERIFIED].\n"
        "- If something isn't in the wiki, clearly state so."
    )


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

    system_content = _build_chat_system_prompt(db)
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

        # 응답에서 [[페이지명]] 추출 → citation 데이터 구성
        citations = []
        try:
            import re as _re
            from app.models.wiki import WikiPage as _WP
            from app.core.database import SessionLocal as _SL
            link_titles = list(dict.fromkeys(_re.findall(r"\[\[([^\]|]+?)(?:\|[^\]]+)?\]\]", full_response)))
            if link_titles:
                with _SL() as cdb:
                    for title in link_titles:
                        pg = cdb.query(_WP).filter_by(title=title.strip()).first()
                        if pg:
                            citations.append({"page_id": pg.id, "path": pg.path, "title": pg.title})
        except Exception:
            citations = []

        # Persist the assistant message in a fresh session.
        try:
            with SessionLocal() as save_db:
                assistant_msg = ChatMessage(
                    session_id=session_id,
                    role=ChatMessageRole.assistant,
                    content=full_response,
                    citations_json=citations or None,
                )
                save_db.add(assistant_msg)
                sess = save_db.get(ChatSession, session_id)
                if sess is not None:
                    sess.updated_at = datetime.now(timezone.utc)
                save_db.commit()
        except Exception:
            pass

        yield f"data: {json.dumps({'done': True, 'citations': citations})}\n\n"

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
