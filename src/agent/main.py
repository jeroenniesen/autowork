import uuid
import yaml
import json
import logging
import os
from fastapi import FastAPI, HTTPException, File, UploadFile, Form, Depends
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from typing import Dict, Any, List, Optional
from langchain_core.runnables import RunnableWithMessageHistory
import redis
from datetime import datetime
from langchain_community.vectorstores import Chroma  # Add the missing import here
from src.config.loader import ConfigLoader
from src.models.model_factory import ModelFactory
from src.agents.agent_factory import AgentFactory
from src.agents.rag_agent import RAGAgentFactory
from src.agents.manager_agent import ManagerAgentFactory  # Import the new manager agent factory
from src.utils.document_utils import DocumentProcessor
from src.utils.vector_store import VectorStoreManager
from src.schemas.api import (
    MessageRequest, MessageResponse, ProfileInfo, ProfilesListResponse,
    ProfileCreate, ProfileResponse, ProfileUpdateResponse,
    SessionInfo, SessionListResponse, ChatMessage, ChatHistoryResponse,
    KnowledgeSetInfo, KnowledgeSetCreate, KnowledgeSetResponse, KnowledgeSetsListResponse
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
        
        # Add knowledge_sets if they exist
        if profile.knowledge_sets:
            config["knowledge_sets"] = profile.knowledge_sets
            
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
            
        # Add knowledge_sets if they exist
        if profile.knowledge_sets:
            config["knowledge_sets"] = profile.knowledge_sets
            
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
            
            # Create a Redis-based message history
            history = RedisChatMessageHistory(
                session_id=session_id,
                redis_url=redis_url,
                ttl=redis_ttl
            )
            
            # Create a message history factory
            def get_session_history():
                return history
            
            # Handle different agent types
            if agent_type == "manager":
                # Create a Manager agent that can delegate tasks to other agents
                
                # Collect persona information for available agent profiles
                profile_personas = {}
                for profile_name in agent_config.get('available_agents', []):
                    try:
                        agent_profile_config = config_loader.get_profile(profile_name)
                        # Extract persona from agent configuration
                        if agent_profile_config and 'agent' in agent_profile_config:
                            profile_personas[profile_name] = agent_profile_config['agent'].get('persona', 
                                                                                             f"Profile: {profile_name}")
                    except Exception as e:
                        logger.warning(f"Could not get persona for profile '{profile_name}': {str(e)}")
                
                # Function to invoke other agents from the manager
                async def invoke_agent(text, profile_name, sub_session_id=None):
                    """Helper to invoke other agents from the manager agent"""
                    logger.info(f"Manager delegating task to agent profile: {profile_name}")
                    
                    try:
                        # Create a new message request for the delegated task
                        delegated_request = MessageRequest(
                            text=text,
                            profile_name=profile_name,
                            session_id=sub_session_id  # Using None will create a new session
                        )
                        
                        # Process the delegated request through the chat endpoint
                        # But we need to handle it directly to avoid endpoint recursion
                        sub_response = await process_chat_request(delegated_request)
                        return sub_response
                    except Exception as e:
                        logger.error(f"Error delegating task to {profile_name}: {str(e)}")
                        return MessageResponse(
                            response=f"Error delegating task: {str(e)}",
                            session_id=sub_session_id or str(uuid.uuid4())
                        )
                
                # Create manager agent chain
                chain = ManagerAgentFactory.create_manager_agent(
                    llm=llm,
                    config=agent_config,
                    agent_invoker=invoke_agent,
                    profile_personas=profile_personas  # Pass the collected personas
                )
                
                logger.info(f"Created new manager agent with available profiles: {agent_config.get('available_agents', [])}")
                logger.debug(f"Provided persona information for {len(profile_personas)} profiles")
                
            elif agent_type == "rag":
                # Create RAG agent
                knowledge_sets = profile_config.get("knowledge_sets", [])
                if not knowledge_sets:
                    logger.warning(f"No knowledge sets configured for RAG agent in profile {request.profile_name}")
                    knowledge_sets = ["default"]

                # Load all configured vector stores
                vector_stores_list = []
                for collection_name in knowledge_sets:
                    try:
                        vector_store = vector_store_manager.load_vector_store(collection_name)
                        vector_stores_list.append(vector_store)
                        vector_stores[collection_name] = vector_store
                        logger.info(f"Loaded vector store '{collection_name}' for RAG agent")
                    except FileNotFoundError:
                        logger.warning(f"Vector store '{collection_name}' not found, skipping")
                        continue
                    except Exception as e:
                        logger.error(f"Error loading vector store '{collection_name}': {str(e)}")
                        continue

                if not vector_stores_list:
                    logger.warning("No vector stores loaded, creating empty default store")
                    vector_store = vector_store_manager.create_vector_store([], "default")
                    vector_stores_list.append(vector_store)
                    vector_stores["default"] = vector_store

                # Merge multiple vector stores if needed
                if len(vector_stores_list) > 1:
                    # Use the first store as base and merge others into it
                    main_store = vector_stores_list[0]
                    vector_store_manager.merge_vector_stores(main_store, vector_stores_list[1:])
                    vector_store = main_store
                else:
                    vector_store = vector_stores_list[0]

                # Create RAG agent chain
                chain = RAGAgentFactory.create_conversation_rag_agent(
                    llm=llm,
                    vector_store=vector_store,
                    config=agent_config
                )
            else:
                # Create regular conversation agent chain
                chain = AgentFactory.create_agent_from_template(
                    llm=llm,
                    config=agent_config
                )
            
            # Create the agent with message history properly configured for each agent type
            agent = RunnableWithMessageHistory(
                chain,
                get_session_history,  # Use the Redis-based history
                input_messages_key="input",
                history_messages_key="history",
                output_messages_key="output"
            )
            
            logger.info(f"Created new {agent_type} agent session: {session_id} using profile {request.profile_name}")
            sessions[session_id] = agent
        
        # Get the agent for this session
        agent = sessions[session_id]
        
        # Process the message
        logger.debug(f"Processing message for session {session_id}: {request.text[:30]}...")
        
        # Invoke the chain with the message
        response = await agent.ainvoke(
            {"input": request.text},
            config={"configurable": {"session_id": session_id}}
        )
        
        # Extract the response content
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
        
        # Clean up response
        response_text = response_text.strip()
        logger.debug(f"Final response text for session {session_id}: {response_text[:50]}...")
        
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

# Helper function to process chat requests directly (used by manager agents)
async def process_chat_request(request: MessageRequest) -> MessageResponse:
    """Process a chat request directly without going through the endpoint."""
    return await chat(request)

# Knowledge Set Management Endpoints
@app.get("/knowledge-sets", response_model=KnowledgeSetsListResponse)
async def list_knowledge_sets():
    """List all available knowledge sets."""
    try:
        # Get all knowledge sets from Redis
        knowledge_sets = []
        for key in redis_client.keys("knowledge_set:*"):
            name = key.decode('utf-8').split(':')[1]
            data = redis_client.hgetall(f"knowledge_set:{name}")
            if data:
                # Get document count from vector store
                doc_count = 0
                try:
                    # Use sanitized collection name for Chroma
                    sanitized_name = vector_store_manager.sanitize_collection_name(name)
                    vs_path = os.path.join(vector_store_manager.persist_directory, name)
                    if os.path.exists(vs_path):
                        vs = Chroma(
                            persist_directory=vs_path,
                            embedding_function=vector_store_manager.embedding_model,
                            collection_name=sanitized_name
                        )
                        doc_count = vs._collection.count()
                except Exception as e:
                    logger.warning(f"Error getting document count for {name}: {str(e)}")
                    pass

                # Get assigned profiles
                assigned_profiles = []
                for profile_key in redis_client.keys("profile:*"):
                    profile_name = profile_key.decode('utf-8').split(':')[1]
                    profile_data = redis_client.get(profile_key)
                    if profile_data:
                        profile_config = json.loads(profile_data)
                        if name in profile_config.get('knowledge_sets', []):
                            assigned_profiles.append(profile_name)

                knowledge_sets.append(KnowledgeSetInfo(
                    name=name,
                    description=data.get(b'description', b'').decode('utf-8'),
                    document_count=doc_count,
                    created_at=datetime.fromisoformat(data.get(b'created_at', b'2024-01-01T00:00:00').decode('utf-8')),
                    assigned_profiles=assigned_profiles
                ))

        return KnowledgeSetsListResponse(knowledge_sets=knowledge_sets)
    except Exception as e:
        logger.error(f"Error listing knowledge sets: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/knowledge-sets", response_model=KnowledgeSetResponse)
async def create_knowledge_set(knowledge_set: KnowledgeSetCreate):
    """Create a new knowledge set."""
    try:
        # Check if knowledge set already exists
        if redis_client.exists(f"knowledge_set:{knowledge_set.name}"):
            raise HTTPException(status_code=400, detail=f"Knowledge set '{knowledge_set.name}' already exists")

        # Create empty vector store for the knowledge set
        vector_store_manager.create_vector_store([], knowledge_set.name)

        # Store metadata in Redis
        redis_client.hmset(f"knowledge_set:{knowledge_set.name}", {
            'description': knowledge_set.description,
            'created_at': datetime.now().isoformat()
        })

        return KnowledgeSetResponse(
            name=knowledge_set.name,
            description=knowledge_set.description,
            document_count=0,
            created_at=datetime.now(),
            assigned_profiles=[]
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating knowledge set: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/knowledge-sets/{name}", response_model=KnowledgeSetResponse)
async def get_knowledge_set(name: str):
    """Get information about a specific knowledge set."""
    try:
        # Check if knowledge set exists
        if not redis_client.exists(f"knowledge_set:{name}"):
            raise HTTPException(status_code=404, detail=f"Knowledge set '{name}' not found")

        # Get metadata from Redis
        data = redis_client.hgetall(f"knowledge_set:{name}")

        # Get document count from vector store
        doc_count = 0
        try:
            vs = vector_store_manager.load_vector_store(name)
            doc_count = vs._collection.count()
        except FileNotFoundError:
            pass

        # Get assigned profiles
        assigned_profiles = []
        for profile_key in redis_client.keys("profile:*"):
            profile_name = profile_key.decode('utf-8').split(':')[1]
            profile_data = redis_client.get(profile_key)
            if profile_data:
                profile_config = json.loads(profile_data)
                if name in profile_config.get('knowledge_sets', []):
                    assigned_profiles.append(profile_name)

        return KnowledgeSetResponse(
            name=name,
            description=data.get(b'description', b'').decode('utf-8'),
            document_count=doc_count,
            created_at=datetime.fromisoformat(data.get(b'created_at', b'2024-01-01T00:00:00').decode('utf-8')),
            assigned_profiles=assigned_profiles
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting knowledge set: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/knowledge-sets/{name}", response_model=KnowledgeSetResponse)
async def update_knowledge_set(name: str, knowledge_set: KnowledgeSetCreate):
    """Update a knowledge set."""
    try:
        # Check if knowledge set exists
        if not redis_client.exists(f"knowledge_set:{name}"):
            raise HTTPException(status_code=404, detail=f"Knowledge set '{name}' not found")

        # Only update description (name changes not allowed)
        redis_client.hset(f"knowledge_set:{name}", 'description', knowledge_set.description)

        # Return updated knowledge set
        return await get_knowledge_set(name)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating knowledge set: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/knowledge-sets/{name}")
async def delete_knowledge_set(name: str):
    """Delete a knowledge set."""
    try:
        # Check if knowledge set exists
        if not redis_client.exists(f"knowledge_set:{name}"):
            raise HTTPException(status_code=404, detail=f"Knowledge set '{name}' not found")

        # Check if knowledge set is assigned to any profiles
        for profile_key in redis_client.keys("profile:*"):
            profile_data = redis_client.get(profile_key)
            if profile_data:
                profile_config = json.loads(profile_data)
                if name in profile_config.get('knowledge_sets', []):
                    raise HTTPException(
                        status_code=400,
                        detail=f"Cannot delete knowledge set '{name}' as it is assigned to one or more profiles"
                    )

        # Delete vector store
        vs_path = os.path.join(vector_store_manager.persist_directory, name)
        if os.path.exists(vs_path):
            import shutil
            shutil.rmtree(vs_path)

        # Delete metadata from Redis
        redis_client.delete(f"knowledge_set:{name}")

        return {"status": "success", "message": f"Knowledge set '{name}' deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting knowledge set: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Modify the existing upload-document endpoint
@app.post("/upload-document/{collection_name}")
async def upload_document(
    collection_name: str,
    file: UploadFile = File(...),
    chunk_size: int = Form(1000),
    chunk_overlap: int = Form(200)
):
    """Upload a document to a knowledge set (collection)."""
    try:
        # Check if knowledge set exists
        if not redis_client.exists(f"knowledge_set:{collection_name}"):
            raise HTTPException(status_code=404, detail=f"Knowledge set '{collection_name}' not found")
            
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
        try:
            vector_store = vector_store_manager.load_vector_store(collection_name)
            logger.info(f"Loaded existing vector store '{collection_name}'")
            # Add documents to existing store
            vector_store_manager.add_documents(vector_store, chunks)
            vector_store.persist()  # Make sure to persist after adding documents
            logger.info(f"Added and persisted {len(chunks)} chunks to vector store '{collection_name}'")
        except FileNotFoundError:
            # Create a new vector store
            vector_store = vector_store_manager.create_vector_store(chunks, collection_name)
            vector_store.persist()  # Make sure to persist the new store
            logger.info(f"Created and persisted new vector store '{collection_name}' with {len(chunks)} chunks")
        
        # Store vector store for future reference
        vector_stores[collection_name] = vector_store
        
        # Get updated document count
        doc_count = vector_store._collection.count()
        
        return {
            "status": "success",
            "message": f"Added {len(chunks)} document chunks to knowledge set '{collection_name}'",
            "total_documents": doc_count
        }
    except Exception as e:
        logger.error(f"Error uploading document: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Clean up uploaded file
        if os.path.exists(file_path):
            os.remove(file_path)

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

# Debugging endpoint to get knowledge set info from Redis and disk
@app.get("/debug/knowledge-sets")
async def debug_knowledge_sets():
    """Debug endpoint to help diagnose knowledge set issues."""
    try:
        # Get Redis info
        redis_keys = redis_client.keys("knowledge_set:*")
        redis_knowledge_sets = []
        for key in redis_keys:
            name = key.decode('utf-8').split(':')[1]
            data = redis_client.hgetall(f"knowledge_set:{name}")
            redis_knowledge_sets.append({
                "name": name,
                "data": {k.decode('utf-8'): v.decode('utf-8') for k, v in data.items()} if data else {}
            })
        
        # Get disk info
        vector_store_dir = vector_store_manager.persist_directory
        disk_knowledge_sets = []
        if os.path.exists(vector_store_dir):
            for item in os.listdir(vector_store_dir):
                item_path = os.path.join(vector_store_dir, item)
                if os.path.isdir(item_path):
                    # Check if this looks like a Chroma directory
                    has_chroma_db = os.path.exists(os.path.join(item_path, "chroma.sqlite3"))
                    disk_knowledge_sets.append({
                        "name": item,
                        "path": item_path,
                        "looks_like_chroma": has_chroma_db
                    })
        
        return {
            "redis_knowledge_sets": redis_knowledge_sets,
            "disk_knowledge_sets": disk_knowledge_sets
        }
    except Exception as e:
        logger.error(f"Error in debug endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))  # Fixed closing parenthesis

# Add this new endpoint to register vector stores as knowledge sets
@app.post("/fix/knowledge-sets")
async def fix_knowledge_sets():
    """Fix knowledge set synchronization between disk and Redis."""
    try:
        # Get all vector store directories from disk
        vector_store_dir = vector_store_manager.persist_directory
        disk_knowledge_sets = []
        added_count = 0
        
        if os.path.exists(vector_store_dir):
            for item in os.listdir(vector_store_dir):
                item_path = os.path.join(vector_store_dir, item)
                if os.path.isdir(item_path) and os.path.exists(os.path.join(item_path, "chroma.sqlite3")):
                    disk_knowledge_sets.append(item)
                    
                    # Check if this knowledge set is registered in Redis
                    if not redis_client.exists(f"knowledge_set:{item}"):
                        # Register it with default metadata
                        redis_client.hmset(f"knowledge_set:{item}", {
                            'description': f"Auto-registered knowledge set: {item}",
                            'created_at': datetime.now().isoformat()
                        })
                        added_count += 1
                        logger.info(f"Auto-registered knowledge set from disk: {item}")
        
        return {
            "status": "success",
            "message": f"Synchronized knowledge sets between disk and Redis",
            "found_on_disk": disk_knowledge_sets,
            "newly_registered": added_count
        }
    except Exception as e:
        logger.error(f"Error fixing knowledge sets: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))  # Fixed the unclosed parenthesis

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