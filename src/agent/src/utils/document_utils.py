import os
import logging
from typing import List, Dict, Any, Optional
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from langchain_community.document_loaders import (
    TextLoader,
    PyPDFLoader,
    CSVLoader,
    UnstructuredMarkdownLoader,
    UnstructuredHTMLLoader,
)

logger = logging.getLogger(__name__)

class DocumentProcessor:
    """Utility class for processing documents for RAG capabilities."""
    
    SUPPORTED_EXTENSIONS = {
        ".txt": TextLoader,
        ".pdf": PyPDFLoader,
        ".csv": CSVLoader,
        ".md": UnstructuredMarkdownLoader,
        ".html": UnstructuredHTMLLoader,
    }
    
    @staticmethod
    def load_document(file_path: str) -> List[Document]:
        """Load a document from the specified file path.
        
        Args:
            file_path: Path to the document file
            
        Returns:
            List of Document objects
            
        Raises:
            ValueError: If the file format is not supported
        """
        if not os.path.isfile(file_path):
            logger.error(f"File not found: {file_path}")
            raise FileNotFoundError(f"File not found: {file_path}")
            
        _, file_extension = os.path.splitext(file_path.lower())
        
        if file_extension not in DocumentProcessor.SUPPORTED_EXTENSIONS:
            supported = list(DocumentProcessor.SUPPORTED_EXTENSIONS.keys())
            logger.error(f"Unsupported file format: {file_extension}. Supported formats: {supported}")
            raise ValueError(f"Unsupported file format: {file_extension}. Supported formats: {supported}")
            
        loader_cls = DocumentProcessor.SUPPORTED_EXTENSIONS[file_extension]
        loader = loader_cls(file_path)
        
        try:
            logger.info(f"Loading document: {file_path}")
            return loader.load()
        except Exception as e:
            logger.error(f"Error loading document {file_path}: {str(e)}")
            raise
    
    @staticmethod
    def split_documents(
        documents: List[Document],
        chunk_size: int = 1000,
        chunk_overlap: int = 200
    ) -> List[Document]:
        """Split documents into smaller chunks.
        
        Args:
            documents: List of Document objects
            chunk_size: Maximum size of each chunk
            chunk_overlap: Overlap between chunks
            
        Returns:
            List of chunks as Document objects
        """
        logger.info(f"Splitting {len(documents)} documents into chunks (size={chunk_size}, overlap={chunk_overlap})")
        
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len
        )
        
        return text_splitter.split_documents(documents)
    
    @staticmethod
    def document_to_dict(document: Document) -> Dict[str, Any]:
        """Convert a Document to a dictionary representation.
        
        Args:
            document: Document object
            
        Returns:
            Dictionary representation of the Document
        """
        return {
            "page_content": document.page_content,
            "metadata": document.metadata
        }
        
    @staticmethod
    def dict_to_document(data: Dict[str, Any]) -> Document:
        """Convert a dictionary to a Document.
        
        Args:
            data: Dictionary representation of a Document
            
        Returns:
            Document object
        """
        return Document(
            page_content=data["page_content"],
            metadata=data.get("metadata", {})
        )