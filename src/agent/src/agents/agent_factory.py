from typing import Dict, Any, Optional, List
from langchain.schema.language_model import BaseLanguageModel
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableWithMessageHistory
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
import os
import jinja2


class AgentFactory:
    """Factory class for creating agent instances based on configuration."""
    
    @staticmethod
    def create_conversation_agent(
        llm: BaseLanguageModel,
        config: Dict[str, Any]
    ) -> RunnableWithMessageHistory:
        """Create a conversation agent based on the provided configuration."""
        # Extract agent persona from config
        persona = config.get("persona", "You are a helpful assistant.")
        
        # Create the prompt with chat messages
        prompt = ChatPromptTemplate.from_messages([
            ("system", persona),
            MessagesPlaceholder(variable_name="history"),
            ("human", "{input}")
        ])
        
        # Create and return the chain
        return prompt | llm
    
    @staticmethod
    def create_agent_from_template(
        llm: BaseLanguageModel,
        config: Dict[str, Any],
        template_path: str = "src/templates/conversation.j2"
    ) -> RunnableWithMessageHistory:
        """Create an agent using a Jinja2 template file."""
        # Extract agent persona from config
        persona = config.get("persona", "You are a helpful assistant.")
        
        # Load template from file if it exists
        if os.path.exists(template_path):
            with open(template_path, 'r') as f:
                template_content = f.read()
                
            # Process the template with Jinja2
            env = jinja2.Environment(loader=jinja2.FileSystemLoader('.'))
            template = env.from_string(template_content)
            
            # Render the template with the persona
            system_message = template.render(persona=persona)
        else:
            # Fall back to default template
            system_message = persona
        
        # Create the prompt with chat messages
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_message),
            MessagesPlaceholder(variable_name="history"),
            ("human", "{input}")
        ])
        
        # Create and return the chain
        return prompt | llm