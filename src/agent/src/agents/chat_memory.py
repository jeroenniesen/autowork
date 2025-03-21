from typing import List, Optional
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import BaseMessage, messages_from_dict, messages_to_dict, HumanMessage, AIMessage
import redis
import msgpack
import os
import logging

logger = logging.getLogger(__name__)

class RedisChatMessageHistory(BaseChatMessageHistory):
    """Redis-backed implementation of chat message history."""
    
    def __init__(self, session_id: str, redis_url: Optional[str] = None, ttl: Optional[int] = None) -> None:
        """Initialize with a session ID and optional Redis settings."""
        self.session_id = session_id
        self.redis_url = redis_url or "redis://localhost:6379"
        self.ttl = ttl
        self._redis_client = redis.from_url(self.redis_url)

    def _get_key(self) -> str:
        """Get the Redis key for the current session."""
        return f"chat_history:{self.session_id}"

    def add_message(self, message: BaseMessage) -> None:
        """Add a message to the history."""
        key = self._get_key()
        messages = self.messages
        messages.append(message)
        
        # Convert messages to dict, ensuring type is preserved
        messages_data = []
        for msg in messages:
            msg_dict = {
                "content": msg.content,
                "type": "human" if isinstance(msg, HumanMessage) else "ai"
            }
            messages_data.append(msg_dict)
        
        # Store in Redis
        self._redis_client.set(
            key,
            msgpack.packb(messages_data),
            ex=self.ttl
        )
        logger.debug(f"Added message to Redis: {message.content[:50]}... type={message.__class__.__name__}")

    def clear(self) -> None:
        """Clear the message history."""
        self._redis_client.delete(self._get_key())

    async def aget_messages(self) -> List[BaseMessage]:
        """Get message history asynchronously."""
        return self.messages

    @property
    def messages(self) -> List[BaseMessage]:
        """Get all messages from Redis."""
        key = self._get_key()
        messages_bytes = self._redis_client.get(key)
        if not messages_bytes:
            return []
        
        messages_data = msgpack.unpackb(messages_bytes)
        messages = []
        
        for msg_dict in messages_data:
            if msg_dict["type"] == "human":
                messages.append(HumanMessage(content=msg_dict["content"]))
            else:
                messages.append(AIMessage(content=msg_dict["content"]))
        
        logger.debug(f"Retrieved {len(messages)} messages from Redis for session {self.session_id}")
        return messages

class SimpleChatMessageHistory(BaseChatMessageHistory):
    """A simple in-memory implementation of chat message history (kept for backwards compatibility)."""
    
    def __init__(self) -> None:
        """Initialize with empty message list."""
        self.messages: List[BaseMessage] = []

    def add_message(self, message: BaseMessage) -> None:
        """Add a message to the history.
        
        Args:
            message: Message to add
        """
        self.messages.append(message)

    def clear(self) -> None:
        """Clear the message history."""
        self.messages = []

    async def aget_messages(self) -> List[BaseMessage]:
        """Get message history asynchronously."""
        return self.messages