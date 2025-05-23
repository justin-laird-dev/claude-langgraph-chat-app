import os
import logging
from typing import List, Dict, Generator, Any, Optional, TypedDict
import json
from dataclasses import dataclass
import traceback
import uuid

# LangGraph and LangChain imports
from langgraph.graph import StateGraph, END, MessagesState
from langgraph.checkpoint.mongodb import MongoDBSaver
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableConfig
from pymongo import MongoClient

# Configure logging
logger = logging.getLogger(__name__)

class ClaudeLangGraphAgent:
    """A LangGraph-based agent with built-in memory management using checkpointers."""
    
    def __init__(self):
        """Initialize the Claude LangGraph agent with checkpointer for memory."""
        logger.info("Initializing ClaudeLangGraphAgent with checkpointer...")
        
        # Ensure API key is in environment
        api_key_env = os.getenv("ANTHROPIC_API_KEY")
        if not api_key_env:
            logger.error("CRITICAL: ANTHROPIC_API_KEY not found in environment.")
            raise ValueError("ANTHROPIC_API_KEY not found in environment variables.")
        logger.info(f"ANTHROPIC_API_KEY is set (first 10 chars): {api_key_env[:10]}...")

        self.model = os.getenv("CLAUDE_MODEL")
        if not self.model:
            logger.warning("CLAUDE_MODEL not found, using claude-3-haiku-20240307 as default.")
            self.model = "claude-3-haiku-20240307"
        logger.info(f"Model Name: {self.model}")

        self.max_tokens = int(os.getenv("MAX_TOKENS", "4000"))

        try:
            logger.info(f"Initializing ChatAnthropic with model: {self.model}")
            self.llm = ChatAnthropic(
                model=self.model,
                max_tokens=self.max_tokens
            )
            logger.info(f"ChatAnthropic initialized successfully with model: {self.model}")
            
            # Initialize checkpointer for memory (MongoDB ONLY - required)
            self.checkpointer = self._initialize_checkpointer()
            
            self._build_graph()

        except Exception as e:
            logger.error(f"Unexpected error during initialization: {type(e).__name__} - {str(e)}")
            logger.error(traceback.format_exc())
            raise ValueError(f"Failed to initialize agent: {str(e)}") from e
            
    def _initialize_checkpointer(self):
        """Initialize MongoDB checkpointer - REQUIRED, no fallback."""
        mongodb_uri = os.getenv("MONGODB_URI")
        
        if not mongodb_uri:
            logger.error("🚨 MONGODB_URI not found in environment variables!")
            logger.error("🔧 Please add MONGODB_URI=mongodb://localhost:27017/chatapp to your .env file")
            raise ValueError("MONGODB_URI is required. No fallback to in-memory storage.")
        
        try:
            logger.info(f"🔌 Connecting to MongoDB: {mongodb_uri}")
            # Use the proper pattern from official LangGraph documentation
            client = MongoClient(mongodb_uri)
            checkpointer = MongoDBSaver(client, db_name="chatapp")
            
            logger.info("✅ MongoDB checkpointer initialized successfully")
            logger.info("💾 Conversations will persist across app restarts")
            return checkpointer
                
        except Exception as e:
            logger.error(f"💥 Failed to connect to MongoDB: {e}")
            logger.error("🚨 STARTUP FAILED - MongoDB connection required")
            raise ValueError(f"MongoDB connection failed: {e}. Check your MONGODB_URI and ensure MongoDB is running.")
            
    def _build_graph(self):
        """Build the LangGraph agent with checkpointer for memory management."""
        logger.info("Building LangGraph agent with memory checkpointer...")
        
        def agent_node(state: MessagesState, config: RunnableConfig) -> MessagesState:
            """Main agent node that processes messages with system prompt."""
            try:
                # Get any system prompt from config
                system_prompt = config.get("configurable", {}).get("system_prompt", 
                    "You are Claude, a helpful and friendly AI assistant. Be concise in your responses.")
                
                # Prepare messages with system prompt
                messages = [SystemMessage(content=system_prompt)] + state["messages"]
                
                logger.info(f"Agent node: Processing {len(state['messages'])} messages")
                response = self.llm.invoke(messages)
                
                # Return updated state with new message
                return {"messages": [response]}
                
            except Exception as e:
                logger.error(f"Error in agent_node: {type(e).__name__} - {e}")
                fallback_msg = AIMessage(content=f"I encountered an error: {e}")
                return {"messages": [fallback_msg]}
        
        # Build the graph
        builder = StateGraph(MessagesState)
        builder.add_node("agent", agent_node)
        builder.set_entry_point("agent")
        builder.set_finish_point("agent")
        
        # Compile with checkpointer for memory
        self.graph = builder.compile(checkpointer=self.checkpointer)
        logger.info("LangGraph agent with memory checkpointer built successfully")

    def chat(self, user_message: str, system_prompt: Optional[str] = None, thread_id: str = "default") -> str:
        """
        Chat with the agent using the built-in memory system.
        
        Args:
            user_message: The user's message
            system_prompt: Optional system prompt
            thread_id: Thread ID for conversation memory (default: "default")
        
        Returns:
            The agent's response as a string
        """
        logger.info(f"Chat method called. Thread: {thread_id}, Message: {user_message[:50]}...")
        
        if not hasattr(self, 'graph') or not self.graph:
            logger.error("Chat called, but graph not initialized.")
            return "Error: Agent graph not properly initialized."
        
        # Configure with thread ID and optional system prompt
        config = {
            "configurable": {
                "thread_id": thread_id,
                "system_prompt": system_prompt
            }
        }
        
        # Create input with user message
        input_state = {"messages": [HumanMessage(content=user_message)]}
        
        try:
            # Invoke the graph - it will automatically handle conversation memory
            final_state = self.graph.invoke(input_state, config=config)
            response_message = final_state["messages"][-1]
            
            if hasattr(response_message, 'content'):
                return str(response_message.content)
            return str(response_message)
            
        except Exception as e:
            logger.error(f"Error in chat request: {type(e).__name__} - {str(e)}")
            logger.error(traceback.format_exc())
            return f"Error communicating with Claude: {str(e)}"
    
    def chat_stream(self, user_message: str, system_prompt: Optional[str] = None, thread_id: str = "default") -> Generator[str, None, None]:
        """
        Stream chat with the agent using the built-in memory system.
        
        Args:
            user_message: The user's message
            system_prompt: Optional system prompt
            thread_id: Thread ID for conversation memory (default: "default")
        
        Yields:
            Chunks of the agent's response
        """
        logger.info(f"Chat_stream method called. Thread: {thread_id}, Message: {user_message[:50]}...")
        
        if not hasattr(self, 'graph') or not self.graph:
            logger.error("Chat_stream called, but graph not initialized.")
            yield "Error: Agent graph not properly initialized."
            return

        # Configure with thread ID and optional system prompt
        config = {
            "configurable": {
                "thread_id": thread_id,
                "system_prompt": system_prompt
            }
        }
        
        # Create input with user message
        input_state = {"messages": [HumanMessage(content=user_message)]}
        
        try:
            logger.info(f"Streaming from graph. Thread: {thread_id}")
            
            # Stream from the graph - it will automatically handle conversation memory
            for chunk in self.graph.stream(input_state, config=config, stream_mode="messages"):
                if isinstance(chunk, AIMessage) and chunk.content:
                    yield chunk.content
                elif hasattr(chunk, 'content') and chunk.content:
                    yield chunk.content
                    
        except Exception as e:
            logger.error(f"Error in streaming chat request: {type(e).__name__} - {str(e)}")
            logger.error(traceback.format_exc())
            yield f"Error during streaming: {str(e)}"
            
    def get_conversation_history(self, thread_id: str = "default") -> List[Dict[str, Any]]:
        """
        Get the conversation history for a thread.
        
        Args:
            thread_id: Thread ID to get history for
            
        Returns:
            List of message dictionaries
        """
        try:
            config = {"configurable": {"thread_id": thread_id}}
            state = self.graph.get_state(config)
            
            history = []
            for msg in state.values.get("messages", []):
                if isinstance(msg, HumanMessage):
                    history.append({"role": "user", "text": msg.content})
                elif isinstance(msg, AIMessage):
                    history.append({"role": "assistant", "text": msg.content})
                    
            return history
            
        except Exception as e:
            logger.error(f"Error getting conversation history: {e}")
            return []
            
    def clear_conversation(self, thread_id: str = "default") -> bool:
        """
        Clear the conversation history for a thread.
        
        Args:
            thread_id: Thread ID to clear
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # MongoDB checkpointer supports thread deletion
            if hasattr(self.checkpointer, 'delete_thread'):
                self.checkpointer.delete_thread(thread_id)
                logger.info(f"🗑️  Cleared conversation for thread: {thread_id}")
                return True
            else:
                logger.warning(f"⚠️  Conversation clearing not supported by {type(self.checkpointer).__name__}. Thread: {thread_id}")
                return False
            
        except Exception as e:
            logger.error(f"Error clearing conversation: {e}")
            return False
            
    def get_checkpointer_info(self) -> Dict[str, Any]:
        """Get information about the current checkpointer."""
        checkpointer_type = type(self.checkpointer).__name__
        info = {
            "type": checkpointer_type,
            "persistent": checkpointer_type == "MongoDBSaver",
            "supports_deletion": hasattr(self.checkpointer, 'delete_thread'),
            "mongodb_uri": os.getenv("MONGODB_URI", "Not configured")
        }
        
        if checkpointer_type == "MongoDBSaver":
            info["status"] = "✅ Connected to MongoDB"
            info["persistence"] = "Conversations persist across restarts"
        else:
            info["status"] = "💭 Using in-memory storage"
            info["persistence"] = "Conversations lost on restart"
        
        return info 