# Claude LangGraph Chat Application

A real-time web-based chat application powered by Anthropic's Claude AI, implemented using LangGraph for flexible agent architecture. This application provides a clean interface for interacting with Claude models through a streaming chat experience.

## Features

- **LangGraph Integration**: Utilizes LangGraph for building flexible, extensible AI agents
- **Real-time Streaming Responses**: See Claude's responses appear as they're generated
- **MongoDB Persistent Memory**: Conversations persist across app restarts using MongoDB checkpointer
- **Modern Interface**: Clean, responsive design that works on desktop and mobile
- **System Prompt Support**: Customize Claude's behavior with system prompts
- **Error Handling**: Graceful handling of API errors with informative messages
- **Support for Claude 3.7**: Compatible with the latest Claude models
- **Graph Visualization**: Generate PNG diagrams of the LangGraph agent structure

## Getting Started

### Prerequisites

- Python 3.8 or higher
- An Anthropic API key (get one from [Anthropic's console](https://console.anthropic.com/))
- Docker (required for MongoDB persistent memory)

### Installation

1. **Clone or download this repository**
2. **Create a virtual environment**:
   ```bash
   python -m venv venv
   ```
3. **Activate the virtual environment**:
   - On macOS/Linux:
     ```bash
     source venv/bin/activate
     ```
   - On Windows:
     ```bash
     venv\Scripts\activate
     ```
4. **Install the required dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
5. **Create a `.env` file** in the project root directory with the following contents:
   ```
   ANTHROPIC_API_KEY=your_actual_api_key_here
   CLAUDE_MODEL=claude-3-7-sonnet-20250219
   MAX_TOKENS=4000
   DEBUG_MODE=false
   LOG_LEVEL=info
   PORT=8080
   MONGODB_URI=mongodb://localhost:27017/chatapp
   ```
   Replace `your_actual_api_key_here` with your Anthropic API key.

## Command Line Usage

### 1. Create and activate your virtual environment

Create the virtual environment:
```bash
python -m venv venv
```

Activate it:
- On macOS/Linux:
  ```bash
  source venv/bin/activate
  ```
- On Windows:
  ```bash
  venv\Scripts\activate
  ```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Set up your environment variables

Create a `.env` file in the project directory with your Anthropic API key and other settings (see example in "Getting Started").

### 4. Set up MongoDB (for persistent memory)

Follow the [MongoDB Setup](#mongodb-setup-for-persistent-memory) instructions below.

### 5. Run the web application

```bash
python app.py
```
Then open [http://localhost:8080](http://localhost:8080) in your browser.

### 6. Generate a PNG diagram of the agent graph

```bash
python generate_mermaid_diagram.py
```
This will create a `graph.png` file in the current directory.

## Project Structure

- **app.py**: Main Flask application that handles routing and Socket.IO events
- **utils/langgraph_agent.py**: LangGraph-based Claude agent implementation with MongoDB checkpointer
- **utils/__init__.py**: Initialization code for utilities
- **templates/index.html**: HTML template for the chat interface
- **static/css/style.css**: CSS styling for the application
- **static/js/chat.js**: JavaScript for managing the chat interface and streaming
- **generate_mermaid_diagram.py**: Script for generating agent structure diagrams
- **requirements.txt**: Python dependencies

## LangGraph Architecture

This application uses LangGraph to create an intelligent agent architecture:

1. **State Management**: The agent maintains a state with messages and system prompts
2. **Agent Graph**: A simple yet powerful graph with a single agent node for chat processing
3. **Streaming Support**: Provides real-time streaming of responses through LangChain's streaming interface
4. **MongoDB Checkpointer**: Conversations persist across app restarts in MongoDB
5. **Extensibility**: The architecture can be extended with additional nodes for more complex behaviors

### Extension Ideas

The LangGraph architecture makes it easy to extend this application with:

- **Tool Use**: Add tool-calling capabilities for external API access
- **Multi-step Reasoning**: Implement chains of thought and multi-step reasoning
- **Memory Systems**: Integrate more sophisticated memory mechanisms
- **Multi-agent Collaboration**: Create collaborative agents with different roles

## Configuration Options

The following options can be configured in the `.env` file:

| Option | Description | Default |
|--------|-------------|---------|
| `ANTHROPIC_API_KEY` | Your Anthropic API key | (required) |
| `CLAUDE_MODEL` | The Claude model to use | claude-3-sonnet-20240229 |
| `MAX_TOKENS` | Maximum number of tokens in Claude's response | 4000 |
| `DEBUG_MODE` | Enable/disable debug mode | false |
| `LOG_LEVEL` | Logging level (debug, info, warning, error) | info |
| `PORT` | Port for the web server | 8080 |
| `MONGODB_URI` | MongoDB connection string | mongodb://localhost:27017/chatapp |

## MongoDB Setup for Persistent Memory

**⚠️ IMPORTANT**: This application requires MongoDB for persistent conversation memory. The app will not start without a valid MongoDB connection.

### Setting up MongoDB with Docker

1. **Start a MongoDB container** (with port exposed for external access):
   ```bash
   docker run -d \
     --name mongodb \
     -p 27017:27017 \
     -v mongodb_data:/data/db \
     -e MONGO_INITDB_DATABASE=chatapp \
     mongo:latest
   ```

2. **Check if the container is running**:
   ```bash
   docker ps
   ```
   You should see something like:
   ```
   CONTAINER ID   IMAGE          COMMAND                  CREATED       STATUS       PORTS                      NAMES
   b46dc563bbef   mongo:latest   "docker-entrypoint.s…"   1 minute ago  Up 1 minute  0.0.0.0:27017->27017/tcp   mongodb
   ```

3. **If you already have a container without exposed ports**:
   ```bash
   # Stop the current container
   docker stop <container_name>
   
   # Remove it
   docker rm <container_name>
   
   # Start a new one with proper port mapping
   docker run -d --name mongodb -p 27017:27017 mongo:latest
   ```

### MongoDB Container Management Commands

```bash
# Start the MongoDB container
docker start mongodb

# Stop the MongoDB container
docker stop mongodb

# Restart the MongoDB container
docker restart mongodb

# Remove the container (will lose data unless you use volumes)
docker rm mongodb

# View MongoDB logs
docker logs mongodb

# Follow logs in real-time
docker logs -f mongodb

# Check container status
docker ps | grep mongo
```

### Testing MongoDB Connection

1. **Connect to MongoDB shell inside the container**:
   ```bash
   docker exec -it mongodb mongosh
   ```

2. **Basic MongoDB commands** (inside the MongoDB shell):
   ```javascript
   // Show all databases
   show dbs

   // Create/switch to the chatapp database
   use chatapp

   // Check if LangGraph created collections (after running the app)
   show collections

   // View conversation data (after chatting)
   db.checkpoints.find().limit(5)

   // Exit MongoDB shell
   exit
   ```

3. **Test connection from Python** (from your host machine):
   ```bash
   python -c "
   from pymongo import MongoClient
   try:
       client = MongoClient('mongodb://localhost:27017', serverSelectionTimeoutMS=5000)
       print('Available databases:', client.list_database_names())
       client.close()
       print('✅ MongoDB connection successful!')
   except Exception as e:
       print(f'❌ Connection failed: {e}')
   "
   ```

### MongoDB Data Persistence

By default, MongoDB data is stored inside the container and will be lost when the container is removed. For production use, consider:

1. **Using Docker volumes for data persistence**:
   ```bash
   docker run -d --name mongodb -p 27017:27017 -v mongodb_data:/data/db mongo:latest
   ```

2. **Using Docker Compose** for easier management:
   ```yaml
   # docker-compose.yml
   version: '3.8'
   services:
     mongodb:
       image: mongo:latest
       container_name: mongodb
       ports:
         - "27017:27017"
       volumes:
         - mongodb_data:/data/db
       environment:
         - MONGO_INITDB_DATABASE=chatapp
   
   volumes:
     mongodb_data:
   ```
   
   Then run with:
   ```bash
   docker-compose up -d
   ```

### Troubleshooting MongoDB

**If the app fails to start with MongoDB errors:**
1. Check if the container is running: `docker ps`
2. Check if the port is properly exposed: Look for `0.0.0.0:27017->27017/tcp`
3. Check container logs: `docker logs mongodb`
4. Verify your `.env` file has the correct `MONGODB_URI=mongodb://localhost:27017/chatapp`
5. Test connection inside container: `docker exec -it mongodb mongosh`

**If you get permission errors:**
```bash
# On some systems, you might need to run with sudo
sudo docker run -d --name mongodb -p 27017:27017 mongo:latest
```

**Application won't start without MongoDB:**
- This is by design - the app requires persistent memory
- Make sure MongoDB is running and accessible at the URI specified in your `.env` file
- Check the console logs for specific MongoDB connection errors

## Status and Health Checks

The application provides several endpoints for monitoring:

- **`/status`**: Check application status and MongoDB connection info
- **`/conversation_history`**: View current conversation history
- **`/clear_conversation`**: Clear conversation history (POST request)

## How It Works

### Backend

1. The application uses Flask as the web framework and Socket.IO for real-time communication.
2. When a user sends a message, it's transmitted to the server via Socket.IO.
3. The server uses the LangGraph agent to process the message and send it to the Anthropic API.
4. Claude's response is streamed back in real-time using Socket.IO events.
5. The conversation history is maintained using MongoDB checkpointer for persistence across restarts.

### LangGraph Agent

The `ClaudeLangGraphAgent` class in `utils/langgraph_agent.py` handles all AI processing:

- **_initialize_checkpointer()**: Sets up MongoDB checkpointer (required)
- **_build_graph()**: Constructs the LangGraph architecture with memory checkpointer
- **chat()**: Processes messages through the graph and returns complete responses
- **chat_stream()**: Streams responses as they're generated
- **get_conversation_history()**: Retrieves conversation history from checkpointer
- **clear_conversation()**: Clears conversation history for a thread

## License

This project is open source and available under the MIT License.

## Acknowledgements

- [Anthropic](https://www.anthropic.com/) for providing the Claude API
- [LangChain](https://www.langchain.com/) and [LangGraph](https://python.langchain.com/docs/langgraph) for the agent framework
- [Flask](https://flask.palletsprojects.com/) web framework
- [Socket.IO](https://socket.io/) for real-time communication
- [MongoDB](https://www.mongodb.com/) for persistent data storage 