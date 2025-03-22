import logging
from typing import Dict, Any, List, Optional
from langchain.schema.language_model import BaseLanguageModel
from langchain.schema import Document
from langchain_community.vectorstores import Chroma
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableLambda, RunnablePassthrough, RunnableWithMessageHistory
from langchain_core.messages import SystemMessage, HumanMessage

from .chat_memory import SimpleChatMessageHistory

logger = logging.getLogger(__name__)

class RAGAgentFactory:
    """Factory for creating RAG-enabled agents."""
    
    @staticmethod
    def create_rag_agent(
        llm: BaseLanguageModel,
        vector_store: Chroma,
        config: Dict[str, Any]
    ) -> RunnableWithMessageHistory:
        """Create a RAG-enabled agent."""
        # Extract agent persona and other configs
        persona = config.get("persona", "You are a helpful assistant.")
        k = config.get("retrieval_k", 4)
        
        # Create the retriever with error handling
        try:
            retriever = vector_store.as_retriever(search_kwargs={"k": k})
        except Exception as e:
            logger.error(f"Error creating retriever: {str(e)}")
            # Fallback to a basic retriever
            retriever = vector_store.as_retriever()
        
        # Define a function to handle the history formatting
        def format_history(x):
            history = x.get("history", [])
            # If history is empty or not a list, return an empty list
            if not history or not isinstance(history, list):
                return []
            return history
        
        # Create the prompt template
        prompt = ChatPromptTemplate.from_messages([
            ("system", persona),
            MessagesPlaceholder(variable_name="history"),
            ("system", "Use the following context to help answer the question:\n\n{context}"),
            ("human", "{input}")
        ])
        
        # Create the retrieval chain with better error handling
        def get_context(x: Dict[str, Any]) -> str:
            try:
                # Use invoke instead of get_relevant_documents
                docs = retriever.invoke(x["input"])
                return "\n\n".join([doc.page_content for doc in docs])
            except Exception as e:
                logger.error(f"Error retrieving documents: {str(e)}")
                return "Error retrieving context."
        
        # Transform the inputs
        def transform_inputs(inputs: Dict[str, Any]) -> Dict[str, Any]:
            # Get the context
            context = get_context(inputs)
            # Format the history
            formatted_history = format_history(inputs)
            
            # Return the transformed inputs
            return {
                "context": context,
                "input": inputs["input"],
                "history": formatted_history
            }
        
        # Build the chain
        chain = (
            RunnableLambda(transform_inputs)
            | prompt 
            | llm
        )
        
        return chain
    
    @staticmethod
    def create_conversation_rag_agent(
        llm: BaseLanguageModel,
        vector_store: Chroma,
        config: Dict[str, Any]
    ) -> RunnableWithMessageHistory:
        """Create a RAG agent with conversation capabilities."""
        return RAGAgentFactory.create_rag_agent(llm, vector_store, config)