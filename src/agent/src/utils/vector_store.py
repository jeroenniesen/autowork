import os
import logging
import numpy as np
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
    
    def create_vector_store(self, documents: List[Document], collection_name: str) -> Chroma:
        """Create a vector store from documents.
        
        Args:
            documents: List of documents to add to the store
            collection_name: Name of the collection in the store
            
        Returns:
            Initialized vector store
        """
        logger.info(f"Creating vector store with {len(documents)} documents in collection '{collection_name}'")
        
        return Chroma.from_documents(
            documents=documents,
            embedding=self.embedding_model,
            persist_directory=os.path.join(self.persist_directory, collection_name),
            collection_name=collection_name
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
        
        if not os.path.exists(store_path):
            logger.error(f"Vector store not found at {store_path}")
            raise FileNotFoundError(f"Vector store not found at {store_path}")
        
        logger.info(f"Loading vector store from {store_path}")
        
        return Chroma(
            persist_directory=store_path,
            embedding_function=self.embedding_model,
            collection_name=collection_name
        )
    
    def add_documents(self, vector_store: Chroma, documents: List[Document]) -> None:
        """Add documents to an existing vector store.
        
        Args:
            vector_store: Vector store to add documents to
            documents: List of documents to add
        """
        logger.info(f"Adding {len(documents)} documents to vector store")
        vector_store.add_documents(documents)
        vector_store.persist()
    
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