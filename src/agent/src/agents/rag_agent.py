import logging
from typing import Dict, Any, List, Optional
from langchain.schema.language_model import BaseLanguageModel
from langchain.schema import Document
from langchain_community.vectorstores import Chroma
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableLambda, RunnablePassthrough, RunnableWithMessageHistory
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
        
        # Create the retriever
        retriever = vector_store.as_retriever(search_kwargs={"k": k})
        
        # Create the prompt template
        prompt = ChatPromptTemplate.from_messages([
            ("system", persona),
            MessagesPlaceholder(variable_name="history"),
            ("system", "Use the following context to help answer the question:\n\n{context}"),
            ("human", "{input}")
        ])
        
        # Create the retrieval chain
        chain = (
            {
                "context": lambda x: "\n\n".join([doc.page_content for doc in retriever.get_relevant_documents(x["input"])]),
                "input": RunnablePassthrough(),
                "history": RunnablePassthrough()
            }
            | prompt 
            | llm
        )
        
        # Create a message history factory
        def create_history():
            return SimpleChatMessageHistory()
        
        # Wrap with message history
        return RunnableWithMessageHistory(
            chain,
            create_history,
            input_messages_key="input",
            history_messages_key="history"
        )
    
    @staticmethod
    def create_conversation_rag_agent(
        llm: BaseLanguageModel,
        vector_store: Chroma,
        config: Dict[str, Any]
    ) -> RunnableWithMessageHistory:
        """Create a RAG agent with conversation capabilities."""
        # Extract agent persona and configs
        persona = config.get("persona", "You are a helpful assistant.")
        k = config.get("retrieval_k", 4)
        
        # Create the retriever
        retriever = vector_store.as_retriever(search_kwargs={"k": k})
        
        # Create the prompt template with conversation history and context
        prompt = ChatPromptTemplate.from_messages([
            ("system", persona),
            MessagesPlaceholder(variable_name="history"),
            ("system", "Use the following context to help answer the question:\n\n{context}"),
            ("human", "{input}")
        ])
        
        # Create the retrieval chain
        chain = (
            {
                "context": lambda x: "\n\n".join([doc.page_content for doc in retriever.get_relevant_documents(x["input"])]),
                "input": RunnablePassthrough(),
                "history": RunnablePassthrough()
            }
            | prompt 
            | llm
        )
        
        # Return the chain - the history factory will be provided by the main application
        return chain