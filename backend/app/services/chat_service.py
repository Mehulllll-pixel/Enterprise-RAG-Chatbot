import uuid
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.chat import Chat, Message
from app.repositories.chat_repository import ChatRepository
from app.core.exceptions import EntityNotFoundException
from app.utils.logger import logger

class ChatService:
    """Business service layer coordinating conversation sessions and messaging logs."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.chat_repo = ChatRepository(db)

    async def create_chat(self, user_id: uuid.UUID, title: str, department_id: Optional[uuid.UUID] = None) -> Chat:
        """Create a new chat conversation session."""
        chat = Chat(
            title=title,
            user_id=user_id,
            department_id=department_id
        )
        created = await self.chat_repo.create(chat)
        await self.db.commit()
        logger.info(f"Created new conversation session {created.id} for user {user_id}")
        return created

    async def get_chat(self, chat_id: uuid.UUID) -> Chat:
        """Fetch chat session by ID, loading messages."""
        chat = await self.chat_repo.get_chat_with_messages(chat_id)
        if not chat:
            raise EntityNotFoundException(f"Chat session {chat_id} not found.")
        return chat

    async def list_chats(self, user_id: uuid.UUID, skip: int = 0, limit: int = 50) -> List[Chat]:
        """Fetch list of user conversations."""
        return await self.chat_repo.list_by_user(user_id, skip, limit)

    async def save_message(
        self,
        chat_id: uuid.UUID,
        role: str,
        content: str,
        citations: Optional[List[Dict[str, Any]]] = None,
        confidence_score: Optional[float] = None,
        latency_ms: Optional[int] = None,
        related_questions: Optional[List[str]] = None
    ) -> Message:
        """Persist a message and trigger chat updated timestamps."""
        chat = await self.chat_repo.get(chat_id)
        if not chat:
            raise EntityNotFoundException(f"Chat session {chat_id} not found.")

        message = Message(
            chat_id=chat_id,
            role=role,
            content=content,
            citations=citations,
            confidence_score=confidence_score,
            latency_ms=latency_ms,
            related_questions=related_questions
        )
        
        # Save message
        saved = await self.chat_repo.create_message(message)
        
        # Update chat updated_at timestamp
        # Passing empty dict to update calls default onupdate hooks in SQLAlchemy
        await self.chat_repo.update(chat, {})
        await self.db.commit()
        
        logger.debug(f"Saved {role} message {saved.id} inside chat {chat_id}")
        return saved

    async def delete_chat(self, chat_id: uuid.UUID) -> None:
        """Purge a conversation session and all its messages."""
        chat = await self.chat_repo.get(chat_id)
        if not chat:
            raise EntityNotFoundException(f"Chat session {chat_id} not found.")
        await self.chat_repo.delete(chat.id)
        await self.db.commit()
        logger.info(f"Purged conversation session {chat_id} from database.")
