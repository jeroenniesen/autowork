from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class MessageRequest(BaseModel):
    """Schema for incoming message requests."""
    text: str = Field(..., description="The user's message text")
    profile_name: str = Field(default="default", description="The agent profile to use")
    session_id: Optional[str] = Field(None, description="Session ID for conversation continuity")
    

class MessageResponse(BaseModel):
    """Schema for outgoing message responses."""
    response: str = Field(..., description="The agent's response text")
    session_id: str = Field(..., description="Session ID for conversation continuity")


class ProfileInfo(BaseModel):
    """Schema for profile information."""
    name: str = Field(..., description="Profile name")
    description: str = Field(..., description="Profile description")


class ProfilesListResponse(BaseModel):
    """Schema for listing available profiles."""
    profiles: List[ProfileInfo] = Field(..., description="List of available profiles")


class SessionInfo(BaseModel):
    """Schema for session information."""
    session_id: str = Field(..., description="Unique identifier for the session")
    profile_name: str = Field(..., description="Name of the profile used in this session")
    created_at: str = Field(..., description="ISO formatted timestamp when the session was created")


class SessionListResponse(BaseModel):
    """Schema for listing active sessions."""
    sessions: List[SessionInfo] = Field(..., description="List of active chat sessions")


class ChatMessage(BaseModel):
    """Schema for chat messages."""
    text: str = Field(..., description="The message text")
    isUser: bool = Field(..., description="Whether the message is from the user")


class ChatHistoryResponse(BaseModel):
    """Schema for chat history responses."""
    messages: List[ChatMessage] = Field(..., description="List of chat messages")


class ProfileCreate(BaseModel):
    """Schema for creating a new profile."""
    name: str = Field(..., description="Profile name")
    description: str = Field(..., description="Profile description")
    model: Dict[str, Any] = Field(..., description="Model configuration")
    agent: Dict[str, Any] = Field(..., description="Agent configuration")
    memory: Optional[Dict[str, Any]] = Field(None, description="Memory configuration")
    knowledge_sets: Optional[List[str]] = Field(default=[], description="List of knowledge set names assigned to this profile")


class ProfileResponse(BaseModel):
    """Schema for profile response."""
    name: str = Field(..., description="Profile name")
    description: str = Field(..., description="Profile description")
    config: Dict[str, Any] = Field(..., description="Complete profile configuration")


class ProfileUpdateResponse(BaseModel):
    """Schema for profile update response."""
    status: str = Field(..., description="Status of the update operation")
    message: str = Field(..., description="Message describing the result")
    profile: ProfileResponse = Field(..., description="Updated profile information")


class KnowledgeSetInfo(BaseModel):
    """Schema for knowledge set information."""
    name: str = Field(..., description="Name of the knowledge set")
    description: str = Field(..., description="Description of the knowledge set")
    document_count: int = Field(..., description="Number of documents in the knowledge set")
    created_at: datetime = Field(..., description="When the knowledge set was created")
    assigned_profiles: List[str] = Field(default=[], description="List of profile names using this knowledge set")


class KnowledgeSetCreate(BaseModel):
    """Schema for creating a knowledge set."""
    name: str = Field(..., description="Name of the knowledge set")
    description: str = Field(..., description="Description of the knowledge set")


class KnowledgeSetResponse(BaseModel):
    """Schema for knowledge set response."""
    name: str = Field(..., description="Name of the knowledge set")
    description: str = Field(..., description="Description of the knowledge set")
    document_count: int = Field(..., description="Number of documents in the knowledge set")
    created_at: datetime = Field(..., description="When the knowledge set was created")
    assigned_profiles: List[str] = Field(default=[], description="List of profile names using this knowledge set")


class KnowledgeSetsListResponse(BaseModel):
    """Schema for listing knowledge sets."""
    knowledge_sets: List[KnowledgeSetInfo] = Field(..., description="List of knowledge sets")