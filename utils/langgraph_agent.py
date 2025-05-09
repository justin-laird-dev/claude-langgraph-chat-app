import os
import logging
from typing import List, Dict, Generator, Any, Optional, TypedDict
import json
from dataclasses import dataclass
import traceback

# LangGraph and LangChain imports
from langgraph.graph import StateGraph, END
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
import anthropic

# Configure logging
logger = logging.getLogger(__name__)

# Define the agent state as a TypedDict
class AgentState(TypedDict):
    messages: List
    system: str

class ClaudeLangGraphAgent:
    """A utility class for interacting with Claude API via LangGraph with streaming support."""
    
    def __init__(self):
        """Initialize the Claude LangGraph agent with API key from environment variables."""
        logger.info("Initializing ClaudeLangGraphAgent (relying on env var for ChatAnthropic)...")
        
        # Ensure API key is in environment, as ChatAnthropic will need it
        api_key_env = os.getenv("ANTHROPIC_API_KEY")
        if not api_key_env:
            logger.error("CRITICAL: ANTHROPIC_API_KEY not found in environment for ChatAnthropic.")
            raise ValueError("ANTHROPIC_API_KEY not found in environment variables.")
        logger.info(f"ANTHROPIC_API_KEY is set in environment (first 10 chars): {api_key_env[:10]}...")

        self.model = os.getenv("CLAUDE_MODEL")
        if not self.model:
            logger.warning("CLAUDE_MODEL not found in .env, using claude-3-haiku-20240307 as default.")
            self.model = "claude-3-haiku-20240307"
        logger.info(f"Model Name: {self.model}")

        self.max_tokens = int(os.getenv("MAX_TOKENS", "4000"))

        # Test the API key and model with a direct client call first to be sure
        try:
            logger.info(f"Pre-validating API key and model '{self.model}' with direct anthropic.Anthropic client...")
            direct_client = anthropic.Anthropic(api_key=api_key_env.strip()) # Use the env key
            direct_response = direct_client.messages.create(
                model=self.model, 
                max_tokens=10, 
                messages=[{"role": "user", "content": "Hello for pre-validation"}]
            )
            logger.info(f"Direct pre-validation successful: {direct_response.content[0].text[:30]}...")
        except Exception as direct_e:
            logger.error(f"Direct pre-validation FAILED: {type(direct_e).__name__} - {str(direct_e)}")
            raise ValueError(f"Direct API pre-validation failed. Check key/model/credits. Error: {str(direct_e)}") from direct_e

        try:
            logger.info(f"Attempting to initialize ChatAnthropic with model: {self.model} (relying on env var for key)")
            self.llm = ChatAnthropic(
                model=self.model,                
                # anthropic_api_key=api_key, # REMOVED - Let ChatAnthropic find it from env
                max_tokens=self.max_tokens,
                streaming=True
            )
            logger.info(f"ChatAnthropic initialized successfully with model: {self.model}")
            
            self._build_agent()

        except anthropic.AuthenticationError as e:
            logger.error(f"AuthenticationError during ChatAnthropic init: {e.status_code} - {e.message}")
            logger.error(f"Response body if available: {e.response.text if hasattr(e, 'response') and e.response else 'N/A'}")
            raise ValueError(f"Failed to initialize ChatAnthropic due to AuthenticationError: {e.message}. ANTHROPIC_API_KEY in env may be incorrect or LangChain has an issue.") from e
        except Exception as e:
            logger.error(f"Unexpected error during ChatAnthropic init: {type(e).__name__} - {str(e)}")
            logger.error(traceback.format_exc())
            raise ValueError(f"Failed to initialize ChatAnthropic: {str(e)}") from e
            
    def _build_agent(self):
        """Build the LangGraph agent architecture."""
        logger.info("Building full LangGraph agent architecture...")
        builder = StateGraph(AgentState)
        
        def agent_node(state: AgentState) -> Dict:
            messages = state["messages"].copy()
            if state["system"]:
                messages.insert(0, SystemMessage(content=state["system"]))
            
            try:
                logger.info(f"LangGraph agent node: Sending request to Claude model: {self.model}")
                response = self.llm.invoke(messages)
                new_messages = state["messages"].copy() + [response]
                return {"messages": new_messages}
            except Exception as e:
                logger.error(f"Error in LangGraph agent_node: {type(e).__name__} - {e}")
                fallback_msg = AIMessage(content=f"I encountered an error processing your request: {e}")
                new_messages = state["messages"].copy() + [fallback_msg]
                return {"messages": new_messages}
        
        builder.add_node("agent", agent_node)
        builder.set_entry_point("agent")
        builder.add_edge("agent", END)
        self.graph = builder.compile()
        logger.info("Full LangGraph agent architecture built successfully.")

    def chat(self, history: List[Dict[str, str]], system_prompt: Optional[str] = None) -> str:
        logger.info(f"Chat method called. Model: {self.model}. History length: {len(history)}")
        if not hasattr(self, 'graph') or not self.graph:
            logger.error("Chat called, but graph not initialized.")
            return "Error: Agent graph not properly initialized."
        
        formatted_messages = self._format_messages_for_graph(history)
        initial_state: AgentState = {"messages": formatted_messages, "system": system_prompt or ""}
        
        try:
            final_state = self.graph.invoke(initial_state)
            response_message = final_state["messages"][-1]
            if hasattr(response_message, 'content'):
                return str(response_message.content)
            return str(response_message) 
        except Exception as e:
            logger.error(f"Error in chat request: {type(e).__name__} - {str(e)}")
            logger.error(traceback.format_exc())
            return f"Error communicating with Claude: {str(e)}"
    
    def chat_stream(self, history: List[Dict[str, str]], system_prompt: Optional[str] = None) -> Generator[str, None, None]:
        logger.info(f"Chat_stream method called. Model: {self.model}. History length: {len(history)}")
        if not hasattr(self, 'llm') or not self.llm:
            logger.error("Chat_stream called, but LLM not initialized.")
            yield "Error: LLM not properly initialized."
            return

        formatted_messages = self._format_messages_for_graph(history)
        messages_to_send = formatted_messages.copy()
        if system_prompt:
            messages_to_send.insert(0, SystemMessage(content=system_prompt))
        
        try:
            logger.info(f"Streaming from LLM. Message count: {len(messages_to_send)}")
            for chunk in self.llm.stream(messages_to_send):
                if chunk.content:
                    yield chunk.content
        except Exception as e:
            logger.error(f"Error in streaming chat request: {type(e).__name__} - {str(e)}")
            logger.error(traceback.format_exc())
            yield f"Error during streaming: {str(e)}"
        
    def _format_messages_for_graph(self, history: List[Dict[str, str]]) -> List:
        formatted_messages = []
        for msg in history:
            role = msg["role"]
            content = msg["text"]
            if role == "user":
                formatted_messages.append(HumanMessage(content=content))
            elif role == "assistant":
                formatted_messages.append(AIMessage(content=content))
        return formatted_messages 