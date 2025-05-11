import os
import traceback
import logging
from flask import Flask, render_template, session, request, redirect, url_for, jsonify
from flask_socketio import SocketIO
import secrets
import uuid
from dotenv import load_dotenv
import anthropic

# Configure logging first
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables, OVERRIDING any existing system-level variables
logger.info("Loading .env file with override=True")
load_dotenv(override=True)

# Check and validate environment variables 
api_key = os.getenv("ANTHROPIC_API_KEY")
model = os.getenv("CLAUDE_MODEL")

# Log the source of the API key and model for debugging
if api_key and api_key.startswith("sk-ant-api03-"):
    logger.info("ANTHROPIC_API_KEY loaded and starts with 'sk-ant-api03-'.")
elif api_key:
    logger.warning(f"ANTHROPIC_API_KEY loaded, but does not start with 'sk-ant-api03-'. Starts with: {api_key[:10]}...")
else: # not api_key
    logger.error("ANTHROPIC_API_KEY is NOT SET in the environment after load_dotenv(override=True).")

expected_model = "claude-3-7-sonnet-20250219"
if model == expected_model:
    logger.info(f"CLAUDE_MODEL ('{model}') was loaded and matches expected '{expected_model}'.")
elif not model:
    logger.warning(f"CLAUDE_MODEL not set after load_dotenv(override=True), defaulting to claude-3-sonnet-20240229")
    model = "claude-3-sonnet-20240229"
else:
    logger.warning(f"CLAUDE_MODEL loaded as '{model}', which differs from expected ('{expected_model}') or default.")

logger.info(f"Using Claude model: {model}") # This will show the model actually being used

if api_key:
    prefix = api_key[:10] if len(api_key) > 10 else api_key
    logger.info(f"Effective API key being used - starts with: {prefix}..., length: {len(api_key)}")
    
    os.environ["ANTHROPIC_API_KEY"] = api_key.strip() # Ensure it's set for other modules
    os.environ["CLAUDE_MODEL"] = model # Ensure model is also set for other modules
    
    # Validate the API key and model by making a direct API call
    try:
        logger.info(f"Testing API key with direct Anthropic API using model: {model}...")
        direct_client = anthropic.Anthropic(api_key=api_key.strip())
        response = direct_client.messages.create(
            model=model,
            max_tokens=10,
            messages=[{"role": "user", "content": "hello"}]
        )
        logger.info(f"Direct API test successful: {response.content[0].text[:20]}...")
    except anthropic.AuthenticationError as e:
        logger.error(f"Direct API test failed (AuthenticationError): {str(e)}. The API key is being rejected by Anthropic.")
    except anthropic.BadRequestError as e:
        if "model" in str(e).lower():
            logger.error(f"Invalid model '{model}' for direct API test: {str(e)}")
            # Fallback logic can be added here if necessary, but primary issue is API key loading
        else:
            logger.error(f"Direct API test failed (BadRequestError): {str(e)}")
    except Exception as e:
        logger.error(f"Direct API test failed (Unexpected Error): {type(e).__name__} - {str(e)}")
else:
    logger.error("ANTHROPIC_API_KEY is None after attempting to load from .env with override. Cannot proceed.")

# Import our LangGraph chat agent only after setting up environment
from utils.langgraph_agent import ClaudeLangGraphAgent

# Initialize Flask and Socket.IO
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', secrets.token_hex(16))
socketio = SocketIO(app, cors_allowed_origins="*")

# Initialize the Claude LangGraph agent
try:
    if api_key: # Only attempt if API key was ostensibly loaded
        logger.info("Attempting to initialize ClaudeLangGraphAgent...")
        claude_agent = ClaudeLangGraphAgent(use_mongo_checkpointer=True)
        logger.info("Claude LangGraph agent initialized successfully")
    else:
        logger.error("Skipping ClaudeLangGraphAgent initialization due to missing API key.")
        claude_agent = None # Ensure it's defined but not usable
except Exception as e:
    logger.error(f"Failed to initialize ClaudeLangGraphAgent: {str(e)}")
    logger.error(traceback.format_exc())
    claude_agent = None # Ensure it's defined but not usable

# Store chat history in session
def get_chat_history():
    if 'chat_history' not in session:
        session['chat_history'] = []
    return session['chat_history']

def get_thread_id():
    if 'thread_id' not in session:
        # Generate a new thread ID
        session['thread_id'] = str(uuid.uuid4())
        logger.info(f"Generated new thread ID: {session['thread_id']}")
    return session['thread_id']

def add_to_chat_history(role, text):
    chat_history = get_chat_history()
    chat_history.append({"role": role, "text": text})
    session['chat_history'] = chat_history
    session.modified = True

@app.route('/')
def index():
    # Get or create thread ID
    thread_id = get_thread_id()
    
    # Try to load conversation history from MongoDB if this is the first page load
    if thread_id and not session.get('history_loaded') and claude_agent:
        try:
            stored_messages = claude_agent.get_conversation_history(thread_id)
            if stored_messages:
                # Convert LangChain message objects to our format
                chat_history = []
                for msg in stored_messages:
                    if hasattr(msg, 'type') and msg.type == 'human':
                        chat_history.append({"role": "user", "text": msg.content})
                    elif hasattr(msg, 'type') and msg.type == 'ai':
                        chat_history.append({"role": "assistant", "text": msg.content})
                
                # Update session history
                if chat_history:
                    logger.info(f"Loaded {len(chat_history)} messages from MongoDB for thread {thread_id}")
                    session['chat_history'] = chat_history
                    session['history_loaded'] = True
        except Exception as e:
            logger.error(f"Error loading history from MongoDB: {str(e)}")
            logger.error(traceback.format_exc())
    
    # Get the chat history from the session
    chat_history = get_chat_history()
    
    # Get the model name from the environment variables
    current_model_for_ui = os.getenv("CLAUDE_MODEL", "(model not set)")
    logger.info(f"Current model for UI: {current_model_for_ui}")
    
    # Pass thread_id to the template
    return render_template('index.html', 
                          chat_history=chat_history, 
                          model=current_model_for_ui,
                          thread_id=thread_id)

@app.route('/new_chat')
def new_chat():
    # Clear chat history and generate new thread ID
    session['chat_history'] = []
    session['thread_id'] = str(uuid.uuid4())
    session['history_loaded'] = False
    logger.info(f"Started new conversation with thread ID: {session['thread_id']}")
    return redirect(url_for('index'))

@app.route('/api/threads')
def get_threads():
    """API endpoint to get all available threads."""
    if not claude_agent or not claude_agent.checkpointer:
        return jsonify({"error": "MongoDB checkpointer not available"}), 500
    
    try:
        # Get all thread IDs from MongoDB
        thread_ids = claude_agent.checkpointer.list_thread_ids()
        
        # Mark the current thread
        current_thread_id = get_thread_id()
        threads = []
        
        for thread in thread_ids:
            threads.append({
                "id": thread["id"],
                "message_count": thread["message_count"],
                "timestamp": thread.get("timestamp"),
                "is_current": thread["id"] == current_thread_id
            })
        
        return jsonify({"threads": threads})
    except Exception as e:
        logger.error(f"Error getting threads: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/switch_thread/<thread_id>')
def switch_thread(thread_id):
    """Switch to a different conversation thread."""
    # Update the session thread ID
    session['thread_id'] = thread_id
    session['chat_history'] = []
    session['history_loaded'] = False
    logger.info(f"Switched to thread ID: {thread_id}")
    return redirect(url_for('index'))

@socketio.on('connect')
def handle_connect():
    logger.info('Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    logger.info('Client disconnected')

@socketio.on('send_message')
def handle_message(data):
    # Get the message from the data
    user_message = data.get('message', '')
    logger.info(f"Received user message: {user_message[:30]}...")
    
    # Add the user message to the chat history
    add_to_chat_history('user', user_message)
    
    # Get the chat history in the format needed for the LangGraph agent
    chat_history = get_chat_history()
    
    # Get thread ID for persistence
    thread_id = get_thread_id()
    
    # Create a system prompt
    system_prompt = "You are Claude, a helpful and friendly AI assistant. Be concise in your responses."
    
    # Send the start of the response to the client
    socketio.emit('response_start')
    
    # Check if agent was initialized correctly
    if claude_agent is None:
        error_msg = "Claude agent was not properly initialized (likely API key issue). Please check server logs."
        logger.error(error_msg)
        socketio.emit('response_chunk', {'chunk': f"Error: {error_msg}"})
        socketio.emit('response_end')
        return
    
    # Stream the response from Claude using LangGraph
    assistant_response = ""
    try:
        logger.info(f"Starting streaming response from Claude using LangGraph (thread_id: {thread_id})")
        for chunk in claude_agent.chat_stream(chat_history, system_prompt, thread_id):
            if chunk:
                new_text = chunk
                assistant_response += new_text
                socketio.emit('response_chunk', {'chunk': new_text})
    except Exception as e:
        error_msg = str(e)
        stack_trace = traceback.format_exc()
        logger.error(f"Error streaming response: {error_msg}")
        logger.error(f"Stack trace: {stack_trace}")
        socketio.emit('response_chunk', {'chunk': f"Error: {error_msg}"})
    
    # Ensure we have a response even if streaming fails
    if not assistant_response and claude_agent: # Check claude_agent again
        logger.info("Streaming failed, trying non-streaming API call")
        try:
            assistant_response = claude_agent.chat(chat_history, system_prompt, thread_id)
            socketio.emit('response_chunk', {'chunk': assistant_response})
        except Exception as e:
            error_msg = str(e)
            stack_trace = traceback.format_exc()
            logger.error(f"Error getting response: {error_msg}")
            logger.error(f"Stack trace: {stack_trace}")
            assistant_response = f"Error: {error_msg}"
            socketio.emit('response_chunk', {'chunk': assistant_response})
    
    # Add the complete assistant response to the chat history
    if assistant_response: # Only add if we got something
        add_to_chat_history('assistant', assistant_response)
        logger.info("Completed assistant response")
    else:
        logger.warning("No assistant response was generated.")
    
    # Send the end of the response to the client
    socketio.emit('response_end')

if __name__ == '__main__':
    # Run the Socket.IO server
    port = int(os.getenv('PORT', 8080))
    logger.info(f"Starting server on port {port}")
    socketio.run(app, host='0.0.0.0', port=port, debug=True) 