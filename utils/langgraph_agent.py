import os
import logging
from typing import List, Dict, Generator, Any, Optional, TypedDict
import json
from dataclasses import dataclass
import traceback
import uuid

# LangGraph and LangChain imports
from langgraph.graph import StateGraph, END
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

# Import our checkpointer
from utils.mongo_checkpointer import MongoCheckpointer

# Configure logging
logger = logging.getLogger(__name__)

# Define the agent state as a TypedDict
class AgentState(TypedDict):
    messages: List
    system: str

class ClaudeLangGraphAgent:
    """A utility class for interacting with Claude API via LangGraph with streaming support."""
    
    def __init__(self, use_mongo_checkpointer: bool = True):
        """
        Initialize the Claude LangGraph agent with API key from environment variables.
        
        Args:
            use_mongo_checkpointer: Whether to use MongoDB for checkpointing agent state.
                                   If True, MONGODB_URI must be set in environment variables.
        """
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

        try:
            logger.info(f"Attempting to initialize ChatAnthropic with model: {self.model} (relying on env var for key)")
            self.llm = ChatAnthropic(
                model=self.model,                
                max_tokens=self.max_tokens
            )
            logger.info(f"ChatAnthropic initialized successfully with model: {self.model}")
            
            # Initialize MongoDB checkpointer if requested
            self.checkpointer = None
            if use_mongo_checkpointer:
                try:
                    logger.info("Initializing MongoDB checkpointer...")
                    self.checkpointer = MongoCheckpointer()
                    logger.info("MongoDB checkpointer initialized successfully")
                except Exception as e:
                    logger.error(f"Failed to initialize MongoDB checkpointer: {type(e).__name__} - {str(e)}")
                    logger.warning("Continuing without MongoDB checkpointing")
            
            self._build_agent()

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
        
        # Compile the graph (without a MongoDB checkpointer - we'll handle that ourselves)
        self.graph = builder.compile()
            
        logger.info("Full LangGraph agent architecture built successfully.")

    def chat(self, history: List[Dict[str, str]], system_prompt: Optional[str] = None, thread_id: Optional[str] = None) -> str:
        """
        Send a request to Claude and get a complete response using LangGraph.
        
        Args:
            history: List of message objects with role and text keys
            system_prompt: Optional system prompt
            thread_id: Optional thread ID for conversation persistence
            
        Returns:
            The complete text response from Claude
        """
        logger.info(f"Chat method called. Model: {self.model}. History length: {len(history)}")
        if not hasattr(self, 'graph') or not self.graph:
            logger.error("Chat called, but graph not initialized.")
            return "Error: Agent graph not properly initialized."
        
        formatted_messages = self._format_messages_for_graph(history)
        initial_state: AgentState = {"messages": formatted_messages, "system": system_prompt or ""}
        
        try:
            # Try to get previous state from MongoDB if thread_id provided
            previous_state = None
            if thread_id and self.checkpointer:
                config = self.checkpointer.get_config(thread_id)
                previous_checkpoint = self.checkpointer.get_checkpoint(config)
                if previous_checkpoint and "messages" in previous_checkpoint:
                    # Log that we're using a checkpoint
                    logger.info(f"Using checkpoint for thread_id {thread_id}")
                    previous_state = previous_checkpoint
                    # Merge current conversation with previous state
                    if formatted_messages:
                        previous_state["messages"].extend(formatted_messages)
                        initial_state = previous_state
            
            # Invoke the graph
            final_state = self.graph.invoke(initial_state)
            
            # Save to MongoDB if requested
            if thread_id and self.checkpointer:
                # Create a checkpoint with an ID
                checkpoint_id = str(uuid.uuid4())
                checkpoint = {
                    "ts": "2024-01-01T00:00:00.000Z",  # This is a placeholder, MongoDB checkpointer fills it in
                    "id": checkpoint_id,
                    "messages": final_state["messages"],
                    "system": final_state.get("system", "")
                }
                # Save the checkpoint
                config = self.checkpointer.get_config(thread_id)
                self.checkpointer.save_checkpoint(config, checkpoint)
            
            # Extract the response
            response_message = final_state["messages"][-1]
            if hasattr(response_message, 'content'):
                return str(response_message.content)
            return str(response_message) 
        except Exception as e:
            logger.error(f"Error in chat request: {type(e).__name__} - {str(e)}")
            logger.error(traceback.format_exc())
            return f"Error communicating with Claude: {str(e)}"
    
    def chat_stream(self, history: List[Dict[str, str]], system_prompt: Optional[str] = None, thread_id: Optional[str] = None) -> Generator[str, None, None]:
        """
        Send a request to Claude and stream the response using LangGraph.
        
        Args:
            history: List of message objects with role and text keys
            system_prompt: Optional system prompt
            thread_id: Optional thread ID for conversation persistence
            
        Returns:
            Generator yielding response chunks as they arrive
        """
        logger.info(f"Chat_stream method called. Model: {self.model}. History length: {len(history)}")
        if not hasattr(self, 'llm') or not self.llm:
            logger.error("Chat_stream called, but LLM not initialized.")
            yield "Error: LLM not properly initialized."
            return

        formatted_messages = self._format_messages_for_graph(history)
        
        # Try to get previous state from MongoDB if thread_id provided
        if thread_id and self.checkpointer:
            config = self.checkpointer.get_config(thread_id)
            previous_checkpoint = self.checkpointer.get_checkpoint(config)
            if previous_checkpoint and "messages" in previous_checkpoint:
                # Log that we're using a checkpoint
                logger.info(f"Using checkpoint for thread_id {thread_id}")
                # Merge current conversation with previous state if needed
                if formatted_messages:
                    merged_messages = previous_checkpoint["messages"].copy()
                    merged_messages.extend(formatted_messages)
                    formatted_messages = merged_messages
        
        messages_to_send = formatted_messages.copy()
        if system_prompt:
            messages_to_send.insert(0, SystemMessage(content=system_prompt))
        
        try:
            logger.info(f"Streaming from LLM. Message count: {len(messages_to_send)}")
            # Make sure not to pass streaming=True to the stream method
            kwargs = {}  # Empty kwargs to avoid passing streaming parameter
            
            # Buffer for collecting the full response
            full_response = ""
            for chunk in self.llm.stream(messages_to_send, **kwargs):
                if chunk.content:
                    full_response += chunk.content
                    yield chunk.content
                     
            # After streaming completes, save to MongoDB if thread_id is provided
            if thread_id and self.checkpointer and formatted_messages:
                # Create a full response message
                ai_response = AIMessage(content=full_response)
                
                # Add the message to our history for saving
                messages_for_saving = formatted_messages.copy()
                messages_for_saving.append(ai_response)
                
                # Create and save the checkpoint
                checkpoint_id = str(uuid.uuid4())
                checkpoint = {
                    "ts": "2024-01-01T00:00:00.000Z",  # Placeholder timestamp
                    "id": checkpoint_id,
                    "messages": messages_for_saving,
                    "system": system_prompt or ""
                }
                
                config = self.checkpointer.get_config(thread_id)
                self.checkpointer.save_checkpoint(config, checkpoint)
                logger.info(f"Saved conversation to MongoDB with thread_id: {thread_id}")
                
        except Exception as e:
            logger.error(f"Error in streaming chat request: {type(e).__name__} - {str(e)}")
            logger.error(traceback.format_exc())
            yield f"Error during streaming: {str(e)}"
    
    def get_conversation_history(self, thread_id: str) -> Optional[List]:
        """
        Retrieve conversation history from MongoDB for a given thread ID.
        
        Args:
            thread_id: The thread ID for the conversation
            
        Returns:
            List of messages if found, None otherwise
        """
        if not self.checkpointer:
            logger.error("Cannot retrieve conversation history: MongoDB checkpointer not initialized.")
            return None
            
        try:
            logger.info(f"Retrieving conversation history for thread_id: {thread_id}")
            config = self.checkpointer.get_config(thread_id)
            checkpoint = self.checkpointer.get_checkpoint(config)
            
            if checkpoint and "messages" in checkpoint:
                logger.info(f"Found conversation history with {len(checkpoint['messages'])} messages")
                return checkpoint["messages"]
            
            logger.info(f"No conversation history found for thread_id: {thread_id}")
            return None
        except Exception as e:
            logger.error(f"Error retrieving conversation history: {type(e).__name__} - {str(e)}")
            logger.error(traceback.format_exc())
            return None
        
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