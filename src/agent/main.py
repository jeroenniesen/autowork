import uuid
import yaml
import logging
import os
from fastapi import FastAPI, HTTPException, File, UploadFile, Form, Depends
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from typing import Dict, Any, List, Optional
from langchain_core.runnables import RunnableWithMessageHistory
import redis
from datetime import datetime

from src.config.loader import ConfigLoader
from src.models.model_factory import ModelFactory
from src.agents.agent_factory import AgentFactory
from src.agents.rag_agent import RAGAgentFactory
from src.utils.document_utils import DocumentProcessor
from src.utils.vector_store import VectorStoreManager
from src.schemas.api import (
    MessageRequest, MessageResponse, ProfileInfo, ProfilesListResponse,
    ProfileCreate, ProfileResponse, ProfileUpdateResponse,
    SessionInfo, SessionListResponse, ChatMessage, ChatHistoryResponse
)
from src.agents.chat_memory import RedisChatMessageHistory

# Load server configuration
def load_config() -> Dict[str, Any]:
    with open("config.yaml", "r") as f:
        return yaml.safe_load(f)

# Get configuration
server_config = load_config()

# Configure logging
logging_config = server_config.get("logging", {})
logging.basicConfig(
    level=getattr(logging, logging_config.get("level", "INFO").upper()),
    format=logging_config.get("format", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="LLM Agent API",
    description="A configurable LLM agent API with multiple profiles",
    version="0.1.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]  # Allow all response headers
)

# Initialize configuration loader using the profiles directory from config
profiles_dir = server_config.get("profiles", {}).get("directory", "profiles")
config_loader = ConfigLoader(profiles_dir=profiles_dir)

# Get Redis configuration
redis_url = os.getenv("REDIS_URL", "redis://redis:6379")
redis_ttl = int(os.getenv("REDIS_MEMORY_TTL", "3600"))  # 1 hour default TTL

# Create data directories
UPLOAD_DIR = "data/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Initialize vector store manager
vector_store_manager = VectorStoreManager(persist_directory="data/vector_store")

# Session storage for maintaining conversation state
sessions = {}

# Vector stores for RAG agents
vector_stores = {}

# Add Redis client for session metadata
redis_client = redis.from_url(redis_url)

@app.get("/")
async def root():
    """Root endpoint returning API information."""
    return {
        "name": "LLM Agent API",
        "version": "0.1.0",
        "status": "online"
    }

@app.get("/profiles", response_model=ProfilesListResponse)
async def list_profiles():
    """List all available agent profiles."""
    profile_names = config_loader.list_available_profiles()
    profiles = []
    
    for name in profile_names:
        try:
            profile_config = config_loader.get_profile(name)
            profiles.append(
                ProfileInfo(
                    name=name,
                    description=profile_config.get("description", f"Profile: {name}")
                )
            )
        except Exception as e:
            # Skip profiles with loading errors
            logger.warning(f"Error loading profile {name}: {str(e)}")
            continue
            
    return ProfilesListResponse(profiles=profiles)

@app.post("/profiles", response_model=ProfileResponse)
async def create_profile(profile: ProfileCreate):
    """Create a new agent profile."""
    try:
        # Convert the profile to a configuration dictionary
        config = {
            "name": profile.name,
            "description": profile.description,
            "model": profile.model,
            "agent": profile.agent,
        }
        if profile.memory:
            config["memory"] = profile.memory

        # Save the profile
        config_loader.save_profile(profile.name, config)
        
        return ProfileResponse(
            name=profile.name,
            description=profile.description,
            config=config
        )
    except Exception as e:
        logger.error(f"Error creating profile: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/profiles/{profile_name}", response_model=ProfileResponse)
async def get_profile(profile_name: str):
    """Get a specific profile configuration."""
    try:
        config = config_loader.get_profile(profile_name)
        return ProfileResponse(
            name=profile_name,
            description=config.get("description", f"Profile: {profile_name}"),
            config=config
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Profile '{profile_name}' not found")
    except Exception as e:
        logger.error(f"Error getting profile: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/profiles/{profile_name}", response_model=ProfileUpdateResponse)
async def update_profile(profile_name: str, profile: ProfileCreate):
    """Update an existing profile."""
    try:
        # Check if profile exists
        if profile_name != profile.name:
            raise HTTPException(status_code=400, detail="Profile name in URL must match profile data")
            
        # Convert the profile to a configuration dictionary
        config = {
            "name": profile.name,
            "description": profile.description,
            "model": profile.model,
            "agent": profile.agent,
        }
        if profile.memory:
            config["memory"] = profile.memory

        # Save the updated profile
        config_loader.save_profile(profile_name, config)
        
        return ProfileUpdateResponse(
            status="success",
            message=f"Profile '{profile_name}' updated successfully",
            profile=ProfileResponse(
                name=profile_name,
                description=profile.description,
                config=config
            )
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating profile: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/profiles/{profile_name}")
async def delete_profile(profile_name: str):
    """Delete a profile."""
    try:
        # Prevent deletion of default profile from filesystem
        if profile_name == "default" and os.path.exists(os.path.join(config_loader.profiles_dir, "default.yaml")):
            raise HTTPException(status_code=400, detail="Cannot delete the default profile")
            
        deleted = config_loader.delete_profile(profile_name)
        if not deleted:
            raise HTTPException(status_code=404, detail=f"Profile '{profile_name}' not found")
            
        return {"status": "success", "message": f"Profile '{profile_name}' deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting profile: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat", response_model=MessageResponse)
async def chat(request: MessageRequest):
    """Process a chat message using the specified agent profile."""
    try:
        # Get or create session ID
        session_id = request.session_id or str(uuid.uuid4())
        logger.debug(f"Processing chat request for session {session_id}")
        
        # Store or update session metadata in Redis
        if not redis_client.exists(f"session_metadata:{session_id}"):
            redis_client.hset(f"session_metadata:{session_id}", mapping={
                'profile_name': request.profile_name,
                'created_at': datetime.now().isoformat()
            })
            logger.debug(f"Created new session metadata for {session_id}")

        # Get profile configuration
        profile_config = config_loader.get_profile(request.profile_name)
        
        # Get or create agent for this session
        if session_id not in sessions:
            # Initialize a new agent for this session
            model_config = profile_config.get("model", {})
            agent_config = profile_config.get("agent", {})
            memory_config = profile_config.get("memory", {})
            agent_type = agent_config.get("type", "conversation")
            
            # Create LLM
            llm = ModelFactory.create_llm(model_config)
            
            # Create a message history factory using Redis
            def create_history():
                return RedisChatMessageHistory(
                    session_id=session_id,
                    redis_url=redis_url,
                    ttl=redis_ttl
                )

            if agent_type == "rag":
                # Create RAG agent
                kb_config = profile_config.get("knowledge_base", {})
                collection_name = kb_config.get("collections", [{}])[0].get("name", "default")
                
                # Try to load or create vector store
                try:
                    vector_store = vector_store_manager.load_vector_store(collection_name)
                    logger.info(f"Loaded existing vector store '{collection_name}'")
                except FileNotFoundError:
                    # Create an empty vector store if it doesn't exist
                    vector_store = vector_store_manager.create_vector_store([], collection_name)
                    logger.info(f"Created new empty vector store '{collection_name}'")
                
                # Store vector store for future reference
                vector_stores[collection_name] = vector_store
                
                # Create RAG agent with Redis-based conversation history
                chain = RAGAgentFactory.create_conversation_rag_agent(
                    llm=llm,
                    vector_store=vector_store,
                    config=agent_config
                )
            else:
                # Create regular conversation agent with Redis-based history
                chain = AgentFactory.create_agent_from_template(
                    llm=llm,
                    config=agent_config
                )
            
            # Wrap the chain with Redis-based message history
            agent = RunnableWithMessageHistory(
                chain,
                create_history,
                input_messages_key="input",
                history_messages_key="history"
            )
            
            logger.info(f"Created new {agent_type} agent session: {session_id} using profile {request.profile_name}")
            
            # Store the agent in the session
            sessions[session_id] = agent
        
        # Get the agent for this session
        agent = sessions[session_id]
        
        # Process the message using the new RunnableWithMessageHistory interface
        logger.debug(f"Processing message for session {session_id}: {request.text[:30]}...")
        
        response = await agent.ainvoke(
            {"input": request.text},
            config={"configurable": {"session_id": session_id}}
        )
        
        # Debug the response before converting
        logger.debug(f"Got raw response for session {session_id}: {response}")
        
        # Extract the response content properly
        if hasattr(response, 'content'):
            response_text = response.content
            logger.debug("Extracted response from content attribute")
        elif isinstance(response, dict) and 'output' in response:
            response_text = response['output']
            logger.debug("Extracted response from output field")
        elif isinstance(response, str):
            response_text = response
            logger.debug("Response was already a string")
        else:
            response_text = str(response)
            logger.debug("Converted response to string")
        
        # Clean up any potential formatting without losing content
        response_text = response_text.strip()
        
        logger.debug(f"Final response text for session {session_id}: {response_text[:50]}...")
        
        # Return the response
        return MessageResponse(
            response=response_text,
            session_id=session_id
        )
        
    except FileNotFoundError:
        logger.error(f"Profile not found: {request.profile_name}")
        raise HTTPException(status_code=404, detail=f"Profile '{request.profile_name}' not found")
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/upload-document/{collection_name}")
async def upload_document(
    collection_name: str,
    file: UploadFile = File(...),
    chunk_size: int = Form(1000),
    chunk_overlap: int = Form(200)
):
    """Upload a document to a vector store collection.
    
    Args:
        collection_name: Name of the collection to add the document to
        file: Document file to upload
        chunk_size: Size of document chunks
        chunk_overlap: Overlap between chunks
    """
    try:
        # Save the uploaded file
        file_path = os.path.join(UPLOAD_DIR, file.filename)
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # Load and process the document
        documents = DocumentProcessor.load_document(file_path)
        chunks = DocumentProcessor.split_documents(
            documents,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
        
        # Get or create vector store
        if collection_name not in vector_stores:
            try:
                vector_store = vector_store_manager.load_vector_store(collection_name)
                logger.info(f"Loaded existing vector store '{collection_name}'")
            except FileNotFoundError:
                # Create a new vector store
                vector_store = vector_store_manager.create_vector_store(chunks, collection_name)
                logger.info(f"Created new vector store '{collection_name}' with {len(chunks)} chunks")
                vector_stores[collection_name] = vector_store
                return {"status": "success", "message": f"Created new vector store with {len(chunks)} document chunks"}
        else:
            # Use existing vector store
            vector_store = vector_stores[collection_name]
            # Add documents to it
            vector_store_manager.add_documents(vector_store, chunks)
            logger.info(f"Added {len(chunks)} chunks to vector store '{collection_name}'")
        
        return {
            "status": "success",
            "message": f"Added {len(chunks)} document chunks to vector store '{collection_name}'"
        }
    except Exception as e:
        logger.error(f"Error uploading document: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/sessions", response_model=SessionListResponse)
async def list_sessions():
    """List all active chat sessions."""
    try:
        # Get all session keys from Redis
        session_keys = redis_client.keys("chat_history:*")
        sessions_info = []
        
        for key in session_keys:
            session_id = key.decode('utf-8').split(':')[1]
            # Get session metadata if it exists
            metadata = redis_client.hgetall(f"session_metadata:{session_id}")
            if metadata:
                sessions_info.append(SessionInfo(
                    session_id=session_id,
                    profile_name=metadata.get(b'profile_name', b'unknown').decode('utf-8'),
                    created_at=metadata.get(b'created_at', b'unknown').decode('utf-8')
                ))
        
        return SessionListResponse(sessions=sessions_info)
    except Exception as e:
        logger.error(f"Error listing sessions: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/sessions/{session_id}/history", response_model=ChatHistoryResponse)
async def get_session_history(session_id: str):
    """Get the chat history for a specific session."""
    try:
        logger.debug(f"Fetching chat history for session {session_id}")
        history = RedisChatMessageHistory(
            session_id=session_id,
            redis_url=redis_url,
            ttl=redis_ttl
        )
        
        # Get messages from Redis
        messages = history.messages
        logger.debug(f"Found {len(messages)} messages in history")
        
        # Convert LangChain messages to our API format
        chat_messages = []
        for msg in messages:
            if hasattr(msg, 'content'):
                is_user = hasattr(msg, 'type') and msg.type == 'human'
                logger.debug(f"Converting message: type={getattr(msg, 'type', 'unknown')}, content={msg.content[:50]}...")
                chat_messages.append(ChatMessage(
                    text=msg.content,
                    isUser=is_user
                ))
        
        logger.debug(f"Returning {len(chat_messages)} formatted messages")
        return ChatHistoryResponse(messages=chat_messages)
    except Exception as e:
        logger.error(f"Error getting chat history for session {session_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a specific chat session."""
    try:
        # Remove session from memory if it exists
        if session_id in sessions:
            del sessions[session_id]
        
        # Remove chat history from Redis
        redis_client.delete(f"chat_history:{session_id}")
        # Remove session metadata
        redis_client.delete(f"session_metadata:{session_id}")
        
        return {"status": "success", "message": f"Session {session_id} deleted"}
    except Exception as e:
        logger.error(f"Error deleting session {session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.on_event("startup")
async def startup():
    """Initialize the API on startup."""
    logger.info("Starting LLM Agent API")
    try:
        # Check if default profile exists
        config_loader.get_profile("default")
        logger.info("Default profile loaded successfully")
    except Exception as e:
        logger.warning(f"Default profile not available: {e}")

if __name__ == "__main__":
    # Get server settings from config
    server_settings = server_config.get("server", {})
    host = server_settings.get("host", "0.0.0.0")
    port = server_settings.get("port", 8000)
    debug = server_settings.get("debug", False)
    reload = server_settings.get("reload", False)
    
    # Run the API server
    logger.info(f"Starting server on {host}:{port}")
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=reload
    )