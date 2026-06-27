import uuid
import json
from typing import List
from fastapi import APIRouter, Depends, status, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.redis import get_redis
from app.api.dependencies import get_current_user, has_permissions
from app.schemas.chat import ChatCreate, ChatResponse, ChatResponseWithMessages, QueryRequest
from app.services.chat_service import ChatService
from app.services.rag_service import RAGService
from app.models.user import User
from app.core.exceptions import AuthorizationException

router = APIRouter(prefix="/chats", tags=["chats"])

@router.post(
    "",
    response_model=ChatResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(has_permissions(["chat:write"]))]
)
async def create_chat(
    payload: ChatCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Start a new chat conversation session."""
    chat_service = ChatService(db)
    # Default to current user's department scope if not specified
    dept_id = payload.department_id or current_user.department_id
    return await chat_service.create_chat(
        user_id=current_user.id,
        title=payload.title,
        department_id=dept_id
    )

@router.get(
    "",
    response_model=List[ChatResponse],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(has_permissions(["chat:read"]))]
)
async def list_chats(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve chat history of current user."""
    chat_service = ChatService(db)
    return await chat_service.list_chats(user_id=current_user.id, skip=skip, limit=limit)

@router.get(
    "/{id}",
    response_model=ChatResponseWithMessages,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(has_permissions(["chat:read"]))]
)
async def get_chat_transcript(
    id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Fetch complete message history of a chat conversation. Restricts access to owner/Admin."""
    chat_service = ChatService(db)
    chat = await chat_service.get_chat(id)
    
    if chat.user_id != current_user.id and current_user.role_id != "ADMIN":
        raise AuthorizationException("Access denied. You cannot read other users' transcripts.")

    return chat

@router.delete(
    "/{id}",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(has_permissions(["chat:write"]))]
)
async def delete_chat(
    id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Purge a conversation session."""
    chat_service = ChatService(db)
    chat = await chat_service.get_chat(id)

    if chat.user_id != current_user.id and current_user.role_id != "ADMIN":
        raise AuthorizationException("Access denied. You cannot delete other users' transcripts.")

    await chat_service.delete_chat(id)
    return {"message": "Chat session purged successfully."}

@router.post(
    "/{id}/messages",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(has_permissions(["chat:write"]))]
)
async def submit_query(
    id: uuid.UUID,
    payload: QueryRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis = Depends(get_redis)
):
    """Submit a query to the RAG pipeline and receive a streamed SSE response (token chunks and citation envelope)."""
    chat_service = ChatService(db)
    chat = await chat_service.get_chat(id)
    
    if chat.user_id != current_user.id:
        raise AuthorizationException("Access denied. You cannot post messages to another user's session.")

    # 1. Save user query message to database
    await chat_service.save_message(chat_id=id, role="user", content=payload.content)

    # 2. Compile message history for reformulation
    history = []
    # Eager load messages
    for msg in chat.messages:
        history.append({"role": msg.role, "content": msg.content})

    async def sse_event_generator():
        rag_service = RAGService(db, redis)
        generated_response = []
        citations_data = []
        confidence = 0.0
        latency = 0
        related_qs = []

        try:
            # department scoping: use chat department scope or user department scope
            scope_dept_id = chat.department_id or current_user.department_id
            if not scope_dept_id:
                # Fallback safeguard
                yield f"data: {json.dumps({'type': 'token', 'content': 'Error: Department scope missing for user session.'})}\n\n"
                return

            async for event_str in rag_service.generate_response_stream(scope_dept_id, payload.content, history):
                event = json.loads(event_str)
                
                # Stream token
                if event.get("type") == "token":
                    content = event.get("content", "")
                    generated_response.append(content)
                    yield f"data: {event_str}\n\n"
                
                # Capture metadata packet
                elif event.get("type") == "metadata":
                    citations_data = event.get("citations", [])
                    confidence = event.get("confidence_score", 0.0)
                    latency = event.get("latency_ms", 0)
                    related_qs = event.get("related_questions", [])
                    yield f"data: {event_str}\n\n"

            # 3. Save assistant response payload to database once stream completes
            assistant_content = "".join(generated_response).strip()
            if assistant_content:
                await chat_service.save_message(
                    chat_id=id,
                    role="assistant",
                    content=assistant_content,
                    citations=citations_data,
                    confidence_score=confidence,
                    latency_ms=latency,
                    related_questions=related_qs
                )
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            logger.error(f"Error yielding SSE stream: {str(e)} | Details: {error_details}")
            err_payload = json.dumps({"type": "token", "content": f"\nError: A pipeline exception occurred: {str(e)}"})
            yield f"data: {err_payload}\n\n"

    return StreamingResponse(sse_event_generator(), media_type="text/event-stream")
