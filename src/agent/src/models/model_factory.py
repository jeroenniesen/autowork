from typing import Dict, Any, Optional
from langchain.schema.language_model import BaseLanguageModel
from langchain_ollama import OllamaLLM
from langchain_openai import ChatOpenAI, OpenAI
import logging
import os

logger = logging.getLogger(__name__)

class ModelFactory:
    """Factory class for creating LLM instances based on configuration."""
    
    @staticmethod
    def create_llm(config: Dict[str, Any]) -> BaseLanguageModel:
        """Create an LLM instance based on the provided configuration.
        
        Args:
            config: Dictionary containing model configuration
            
        Returns:
            An initialized language model
            
        Raises:
            ValueError: If the model provider is not supported
        """
        provider = config.get("provider", "").lower()
        model_name = config.get("name", "")
        temperature = config.get("temperature", 0.7)
        
        logger.info(f"Creating LLM with provider: {provider}, model: {model_name}")
        
        if provider == "ollama":
            return ModelFactory._create_ollama_model(model_name, config)
        elif provider == "openai":
            return ModelFactory._create_openai_model(model_name, config)
        elif provider == "anthropic":
            return ModelFactory._create_anthropic_model(model_name, config)
        elif provider == "local":
            return ModelFactory._create_local_model(model_name, config)
        else:
            logger.error(f"Unsupported model provider: {provider}")
            raise ValueError(f"Unsupported model provider: {provider}")
    
    @staticmethod
    def _create_ollama_model(model_name: str, config: Dict[str, Any]) -> BaseLanguageModel:
        """Create an Ollama model."""
        temperature = config.get("temperature", 0.7)
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        return OllamaLLM(
            model=model_name,
            temperature=temperature,
            base_url=base_url
        )
    
    @staticmethod
    def _create_openai_model(model_name: str, config: Dict[str, Any]) -> BaseLanguageModel:
        """Create an OpenAI model."""
        temperature = config.get("temperature", 0.7)
        api_key = config.get("api_key")
        
        if "gpt" in model_name.lower() or model_name.startswith("ft:gpt"):
            # For chat models like GPT-3.5, GPT-4
            return ChatOpenAI(
                model_name=model_name,
                temperature=temperature,
                api_key=api_key
            )
        else:
            # For completion models
            return OpenAI(
                model_name=model_name,
                temperature=temperature,
                api_key=api_key
            )
    
    @staticmethod
    def _create_anthropic_model(model_name: str, config: Dict[str, Any]) -> BaseLanguageModel:
        """Create an Anthropic model."""
        try:
            from langchain_anthropic import ChatAnthropic
            
            temperature = config.get("temperature", 0.7)
            api_key = config.get("api_key")
            
            return ChatAnthropic(
                model_name=model_name,
                temperature=temperature,
                anthropic_api_key=api_key
            )
        except ImportError:
            logger.error("langchain_anthropic is not installed")
            raise ImportError("langchain_anthropic is not installed")
    
    @staticmethod
    def _create_local_model(model_name: str, config: Dict[str, Any]) -> BaseLanguageModel:
        """Create a local model using various providers."""
        local_provider = config.get("local_provider", "").lower()
        
        if local_provider == "llama-cpp":
            try:
                from langchain_community.llms import LlamaCpp
                
                model_path = config.get("model_path", "")
                if not model_path:
                    raise ValueError("model_path must be provided for llama-cpp models")
                
                temperature = config.get("temperature", 0.7)
                max_tokens = config.get("max_tokens", 1000)
                
                return LlamaCpp(
                    model_path=model_path,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    n_ctx=config.get("n_ctx", 4096),
                    verbose=config.get("verbose", False)
                )
            except ImportError:
                logger.error("LlamaCpp is not installed")
                raise ImportError("LlamaCpp is not installed")
        else:
            logger.error(f"Unsupported local provider: {local_provider}")
            raise ValueError(f"Unsupported local provider: {local_provider}")
