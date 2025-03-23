import logging
from typing import Dict, Any, List, Optional, Callable
from langchain.schema.language_model import BaseLanguageModel
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableLambda, RunnablePassthrough, RunnableWithMessageHistory
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
import json
import asyncio

logger = logging.getLogger(__name__)

class ManagerAgentFactory:
    """Factory for creating manager agents that can delegate tasks to other agents."""
    
    @staticmethod
    def create_manager_agent(
        llm: BaseLanguageModel,
        config: Dict[str, Any],
        agent_invoker: Callable,
        profile_personas: Dict[str, str] = None  # New parameter to pass agent profile personas
    ) -> RunnableWithMessageHistory:
        """
        Create a manager agent that can delegate tasks to other agents.
        
        Args:
            llm: The language model to use
            config: The manager agent configuration
            agent_invoker: A function to invoke other agents with (text, profile_name, session_id)
            profile_personas: Dictionary mapping profile names to their personas
        """
        # Extract configuration
        persona = config.get("persona", "You are a manager agent who breaks down complex tasks and delegates them.")
        available_agents = config.get("available_agents", [])
        thinking_enabled = config.get("show_thinking", True)
        delegation_strategy = config.get("delegation_strategy", "automatic")
        
        # Initialize the profile_personas dict if not provided
        if profile_personas is None:
            profile_personas = {}
        
        # Define a function to process the user's input through the manager agent
        def process_with_manager(inputs: Dict[str, Any]) -> Dict[str, Any]:
            """Process the input with the manager agent logic"""
            user_input = inputs.get("input", "")
            history = inputs.get("history", [])
            session_id = inputs.get("session_id", "")
            
            # Add information about available agents to the inputs
            inputs["available_agents"] = available_agents
            inputs["delegation_strategy"] = delegation_strategy
            
            return inputs
        
        # Define a function that handles delegating tasks to other agents
        async def delegate_to_agents(manager_response, original_inputs):
            """
            Parse the manager's response and delegate tasks to other agents.
            This should be called after the manager agent has generated its plan.
            """
            thinking_output = ""
            try:
                # Extract the task plan from the manager's output using a simple marker-based approach
                task_plan_str = None
                if "TASK PLAN:" in manager_response:
                    parts = manager_response.split("TASK PLAN:")
                    if len(parts) > 1:
                        task_plan_str = parts[1].strip()
                
                # Check if we have actual tasks to delegate
                if not task_plan_str:
                    return f"{manager_response}\n\nNo specific tasks were identified for delegation."
                
                # Try to parse the task plan
                try:
                    # First, see if it's already valid JSON
                    task_plan = json.loads(task_plan_str)
                except:
                    # If not, try to extract JSON-like content
                    try:
                        # Look for content that might be between triple backticks
                        if "```json" in task_plan_str and "```" in task_plan_str.split("```json", 1)[1]:
                            json_content = task_plan_str.split("```json", 1)[1].split("```", 1)[0].strip()
                            task_plan = json.loads(json_content)
                        else:
                            # Just try to clean up and parse what we have
                            cleaned = task_plan_str.strip()
                            task_plan = json.loads(cleaned)
                    except:
                        return f"{manager_response}\n\nError: Could not parse the task plan. Please format tasks as proper JSON."
                
                # Validate that we have a list of tasks
                if not isinstance(task_plan, list):
                    return f"{manager_response}\n\nError: Task plan is not a list of tasks."
                
                # Process each task
                all_results = []
                for i, task in enumerate(task_plan):
                    if thinking_enabled:
                        thinking_output += f"\n\n## Task {i+1}: {task.get('task', 'Unnamed task')}\n"
                        thinking_output += f"Delegating to agent profile: {task.get('agent_profile', 'default')}\n"
                    
                    # Invoke the specified agent
                    try:
                        task_input = task.get('task')
                        agent_profile = task.get('agent_profile', 'default')
                        
                        # Skip if missing required fields
                        if not task_input or not agent_profile:
                            all_results.append({
                                "task": task.get('task', 'Undefined task'),
                                "agent_profile": agent_profile,
                                "status": "error",
                                "result": "Task missing required fields (task text or agent_profile)"
                            })
                            continue
                        
                        # Skip if agent profile not in available agents
                        if agent_profile not in available_agents:
                            all_results.append({
                                "task": task_input,
                                "agent_profile": agent_profile,
                                "status": "error",
                                "result": f"Agent profile '{agent_profile}' is not available to this manager"
                            })
                            continue
                        
                        # Invoke the agent (using the provided invoker function)
                        invoker_result = await agent_invoker(task_input, agent_profile, None)
                        
                        # Process result
                        if invoker_result and hasattr(invoker_result, 'response'):
                            result = invoker_result.response
                            if thinking_enabled:
                                thinking_output += f"Response: {result}\n"
                                
                            all_results.append({
                                "task": task_input,
                                "agent_profile": agent_profile,
                                "status": "success",
                                "result": result
                            })
                        else:
                            all_results.append({
                                "task": task_input,
                                "agent_profile": agent_profile,
                                "status": "error",
                                "result": "Failed to get response from agent"
                            })
                    except Exception as e:
                        logger.error(f"Error delegating task: {str(e)}")
                        all_results.append({
                            "task": task.get('task', 'Unknown task'),
                            "agent_profile": task.get('agent_profile', 'default'),
                            "status": "error",
                            "result": f"Error: {str(e)}"
                        })
                
                # Create a summary of all results for the manager to review
                final_response = manager_response
                
                # If thinking is enabled, show the delegation process
                if thinking_enabled and thinking_output:
                    final_response += "\n\n# Thinking Process\n" + thinking_output
                
                # Add the task results
                final_response += "\n\n# Task Results\n"
                for i, result in enumerate(all_results):
                    final_response += f"\n## Task {i+1}: {result['task']}\n"
                    final_response += f"Agent: {result['agent_profile']}\n"
                    final_response += f"Status: {result['status']}\n"
                    final_response += f"Result: {result['result']}\n"
                
                return final_response
                
            except Exception as e:
                logger.error(f"Error in delegation process: {str(e)}")
                return f"{manager_response}\n\nError occurred during task delegation: {str(e)}"
        
        # Define a chain that will execute the delegation after the manager responds
        def execute_delegation(inputs):
            # Get the manager's initial response (planning)
            # The response could be a string or a dictionary with 'output' key
            if isinstance(inputs, dict) and 'output' in inputs:
                manager_response = inputs['output']
            elif isinstance(inputs, str):
                manager_response = inputs
            else:
                return "Error: Invalid response format from manager agent"
            
            if not manager_response:
                return "Error: No response from manager agent"
            
            # Create a new event loop in this thread if one doesn't exist
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                # If there is no current event loop, create a new one
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            # Run the delegation in the event loop
            final_response = loop.run_until_complete(
                delegate_to_agents(manager_response, inputs)
            )
            
            return final_response
        
        # Create agent profile descriptions including their personas
        agent_profiles_info = []
        for agent_name in available_agents:
            persona_info = profile_personas.get(agent_name, "No persona information available")
            agent_profiles_info.append(f"- {agent_name}: {persona_info}")
        
        agent_profiles_description = "\n".join(agent_profiles_info) if agent_profiles_info else "No agent profiles available"
        
        # Create the prompt template for the manager with profile persona information
        system_template = f"""
        {persona}
        
        You are an orchestrator that breaks down complex tasks into smaller subtasks and delegates them to specialized agents.
        
        Available agent profiles for delegation with their specialties:
        {agent_profiles_description}
        
        When given a task, follow these steps:
        1. Analyze the request and break it down into manageable subtasks
        2. For each subtask, carefully consider which agent profile is best suited based on their persona and specialties
        3. Create a task plan in JSON format that lists each subtask and the agent profile to use
        4. I will execute your plan by sending each subtask to the appropriate agent
        5. I will show you the results from each agent
        
        Your task plan must follow this JSON format:
        ```json
        [
          {{{{
            "task": "The specific subtask description",
            "agent_profile": "profile_name"
          }}}},
          ...
        ]
        ```
        
        Always provide your reasoning first, then explicitly specify your task plan after the marker "TASK PLAN:".
        
        Delegation strategy: {delegation_strategy}
        """
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_template),
            MessagesPlaceholder(variable_name="history"),
            ("human", "{input}")
        ])
        
        # Create the chain with manager logic and delegation handling
        chain = (
            RunnableLambda(process_with_manager)
            | prompt
            | llm
            | RunnableLambda(execute_delegation)
        )
        
        return chain