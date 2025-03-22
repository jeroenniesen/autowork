import os
import logging
import numpy as np
import re
from typing import List, Dict, Any, Optional
from langchain.schema import Document
from langchain_community.vectorstores import Chroma
from langchain.embeddings.base import Embeddings
from langchain_community.embeddings import FakeEmbeddings
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_openai import OpenAIEmbeddings

logger = logging.getLogger(__name__)

class VectorStoreManager:
    """Manager for vector stores used in RAG applications."""
    
    def __init__(
        self,
        embedding_model: Optional[Embeddings] = None,
        persist_directory: str = "data/vector_store"
    ):
        """Initialize the vector store manager.
        
        Args:
            embedding_model: Embedding model to use (creates default if None)
            persist_directory: Directory to persist the vector store
        """
        self.embedding_model = embedding_model or self._create_default_embedding_model()
        self.persist_directory = persist_directory
        
        # Ensure the persist directory exists
        os.makedirs(self.persist_directory, exist_ok=True)
    
    def _create_default_embedding_model(self) -> Embeddings:
        """Create a default embedding model.
        
        Returns:
            Default embedding model
        """
        # Try different embedding models with proper error handling
        try:
            # First try to load a local model if available
            logger.info("Attempting to use local HuggingFace embedding model")
            try:
                return HuggingFaceEmbeddings(
                    model_name="sentence-transformers/all-MiniLM-L6-v2"
                )
            except ImportError as e:
                logger.warning(f"Could not load HuggingFaceEmbeddings: {str(e)}")
                # If sentence-transformers is not installed, raise to try OpenAI
                raise
                
        except Exception as e1:
            # Next try OpenAI embeddings
            logger.info(f"Local embeddings failed, trying OpenAI embeddings")
            try:
                return OpenAIEmbeddings()
            except Exception as e2:
                logger.warning(f"OpenAI embeddings failed: {str(e2)}")
                
                # As a last resort, create a simple fallback embedding model
                logger.warning("Using simple fallback embedding model")
                return FakeEmbeddings(size=384)  # Using a reasonable embedding size
    
    def sanitize_collection_name(self, name: str) -> str:
        """Sanitize collection names to conform to Chroma requirements.
        
        Args:
            name: Original collection name
            
        Returns:
            Sanitized collection name meeting Chroma requirements
        """
        # Replace spaces with underscores
        sanitized = name.replace(" ", "_")
        
        # Replace any other invalid characters
        sanitized = re.sub(r'[^a-zA-Z0-9_\-]', '', sanitized)
        
        # Ensure name is between 3-63 characters
        if len(sanitized) < 3:
            sanitized = sanitized + "_" * (3 - len(sanitized))
        elif len(sanitized) > 63:
            sanitized = sanitized[:63]
        
        # Ensure it starts and ends with alphanumeric character
        if not sanitized[0].isalnum():
            sanitized = "x" + sanitized[1:]
        if not sanitized[-1].isalnum():
            sanitized = sanitized[:-1] + "x"
            
        return sanitized
    
    def create_vector_store(self, documents: List[Document], collection_name: str) -> Chroma:
        """Create a vector store from documents.
        
        Args:
            documents: List of documents to add to the store
            collection_name: Name of the collection in the store
            
        Returns:
            Initialized vector store
        """
        sanitized_name = self.sanitize_collection_name(collection_name)
        logger.info(f"Creating vector store with {len(documents)} documents in collection '{sanitized_name}' (original: '{collection_name}')")
        
        # Create the directory for this collection
        collection_dir = os.path.join(self.persist_directory, collection_name)
        os.makedirs(collection_dir, exist_ok=True)
        
        if not documents:
            # Handle empty document list by creating an empty Chroma collection
            logger.info(f"Creating empty vector store for collection '{sanitized_name}'")
            vector_store = Chroma(
                collection_name=sanitized_name,
                embedding_function=self.embedding_model,
                persist_directory=collection_dir
            )
            vector_store.persist()
            return vector_store
        else:
            # Create from documents if we have them
            return Chroma.from_documents(
                documents=documents,
                embedding=self.embedding_model,
                persist_directory=collection_dir,
                collection_name=sanitized_name
            )
    
    def load_vector_store(self, collection_name: str) -> Chroma:
        """Load an existing vector store.
        
        Args:
            collection_name: Name of the collection to load
            
        Returns:
            Loaded vector store
            
        Raises:
            FileNotFoundError: If the vector store doesn't exist
        """
        store_path = os.path.join(self.persist_directory, collection_name)
        sanitized_name = self.sanitize_collection_name(collection_name)
        
        if not os.path.exists(store_path):
            logger.error(f"Vector store not found at {store_path}")
            raise FileNotFoundError(f"Vector store not found at {store_path}")
        
        logger.info(f"Loading vector store from {store_path} with collection name '{sanitized_name}'")
        
        return Chroma(
            persist_directory=store_path,
            embedding_function=self.embedding_model,
            collection_name=sanitized_name
        )
    
    def add_documents(self, vector_store: Chroma, documents: List[Document]) -> None:
        """Add documents to an existing vector store.
        
        Args:
            vector_store: Vector store to add documents to
            documents: List of documents to add
        """
        if not documents:
            logger.warning("No documents to add to vector store")
            return

        try:
            # Ensure documents have proper IDs
            docs_to_add = []
            for i, doc in enumerate(documents):
                # Convert strings to Document objects if needed
                if isinstance(doc, str):
                    doc = Document(page_content=doc)
                # Add an ID if not present
                if 'id' not in doc.metadata:
                    doc.metadata['id'] = f"doc_{i}"
                docs_to_add.append(doc)

            logger.info(f"Adding {len(docs_to_add)} documents to vector store")
            vector_store.add_documents(docs_to_add)
            vector_store.persist()
        except Exception as e:
            logger.error(f"Error adding documents to vector store: {str(e)}")
            raise

    def get_all_documents(self, vector_store: Chroma) -> List[Document]:
        """Get all documents from a vector store.
        
        Args:
            vector_store: Vector store to get documents from
            
        Returns:
            List of documents
        """
        try:
            collection = vector_store._collection
            if not collection:
                return []
            
            # Get all embeddings and metadata
            result = collection.get()
            if not result or not result['documents']:
                return []

            # Create Document objects
            documents = []
            for i, (content, metadata) in enumerate(zip(result['documents'], result['metadatas'])):
                if not metadata:
                    metadata = {}
                if 'id' not in metadata:
                    metadata['id'] = f"doc_{i}"
                documents.append(Document(page_content=content, metadata=metadata))
            
            return documents
        except Exception as e:
            logger.error(f"Error retrieving documents from vector store: {str(e)}")
            return []

    def merge_vector_stores(self, target_store: Chroma, source_stores: List[Chroma]) -> None:
        """Merge multiple vector stores into a target store.
        
        Args:
            target_store: Vector store to merge into
            source_stores: List of vector stores to merge from
        """
        for source_store in source_stores:
            try:
                # Get all documents from source store
                docs = self.get_all_documents(source_store)
                if docs:
                    logger.info(f"Adding {len(docs)} documents from source store to target")
                    self.add_documents(target_store, docs)
            except Exception as e:
                logger.error(f"Error merging vector store: {str(e)}")
                continue

    def similarity_search(
        self,
        vector_store: Chroma,
        query: str,
        k: int = 4
    ) -> List[Document]:
        """Perform a similarity search on the vector store.
        
        Args:
            vector_store: Vector store to search
            query: Query text
            k: Number of results to return
            
        Returns:
            List of relevant documents
        """
        logger.debug(f"Searching for '{query}' in vector store")
        return vector_store.similarity_search(query, k=k)