import uuid
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from app.models.chat import Chat, Message
from app.repositories.base import BaseRepository

class ChatRepository(BaseRepository[Chat]):
    """Repository wrapping data access operations for Chat sessions and Message history."""
    
    def __init__(self, db: AsyncSession):
        super().__init__(Chat, db)

    async def list_by_user(self, user_id: uuid.UUID, skip: int = 0, limit: int = 50) -> List[Chat]:
        """Fetch list of user conversations ordered by last update."""
        query = (
            select(Chat)
            .where(Chat.user_id == user_id)
            .order_by(Chat.updated_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_chat_with_messages(self, chat_id: uuid.UUID) -> Optional[Chat]:
        """Fetch chat session profile along with all transcripts loaded."""
        query = (
            select(Chat)
            .where(Chat.id == chat_id)
            .options(selectinload(Chat.messages))
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def create_message(self, message: Message) -> Message:
        """Persist a message log inside a conversation."""
        self.db.add(message)
        await self.db.flush()
        return message
