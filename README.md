# Claude LangGraph Chat Application

A real-time web-based chat application powered by Anthropic's Claude AI, implemented using LangGraph for flexible agent architecture. This application provides a clean interface for interacting with Claude models through a streaming chat experience.

## Features

- **LangGraph Integration**: Utilizes LangGraph for building flexible, extensible AI agents
- **Real-time Streaming Responses**: See Claude's responses appear as they're generated
- **Full Chat History**: Conversation history is preserved within your session
- **MongoDB Persistence**: Conversations are stored and can be retrieved across sessions
- **Modern Interface**: Clean, responsive design that works on desktop and mobile
- **System Prompt Support**: Customize Claude's behavior with system prompts
- **Error Handling**: Graceful handling of API errors with informative messages
- **Support for Claude 3.7**: Compatible with the latest Claude models
- **Graph Visualization**: Generate PNG diagrams of the LangGraph agent structure

## Getting Started

### Prerequisites

- Python 3.8 or higher
- An Anthropic API key (get one from [Anthropic's console](https://console.anthropic.com/))
- Docker (for running MongoDB)

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
   MONGODB_URI=mongodb://localhost:27017/claude_memory
   DEBUG_MODE=false
   LOG_LEVEL=info
   PORT=8080
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

### 4. Run the web application

```bash
python app.py
```
Then open [http://localhost:8080](http://localhost:8080) in your browser.

### 5. Generate a PNG diagram of the agent graph

```bash
python generate_mermaid_diagram.py
```
This will create a `graph.png` file in the current directory.

## Project Structure

- **app.py**: Main Flask application that handles routing and Socket.IO events
- **utils/langgraph_agent.py**: LangGraph-based Claude agent implementation
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
4. **Extensibility**: The architecture can be extended with additional nodes for more complex behaviors

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
| `MONGODB_URI` | MongoDB connection URI | mongodb://localhost:27017/claude_memory |
| `DEBUG_MODE` | Enable/disable debug mode | false |
| `LOG_LEVEL` | Logging level (debug, info, warning, error) | info |
| `PORT` | Port for the web server | 8080 |

## How It Works

### Backend

1. The application uses Flask as the web framework and Socket.IO for real-time communication.
2. When a user sends a message, it's transmitted to the server via Socket.IO.
3. The server uses the LangGraph agent to process the message and send it to the Anthropic API.
4. Claude's response is streamed back in real-time using Socket.IO events.
5. The conversation history is maintained in the user's session.

### LangGraph Agent

The `ClaudeLangGraphAgent` class in `utils/langgraph_agent.py` handles all AI processing:

- **_build_agent()**: Constructs the LangGraph architecture
- **chat()**: Processes messages through the graph and returns complete responses
- **chat_stream()**: Streams responses as they're generated
- **_format_messages_for_graph()**: Formats messages for LangChain

## MongoDB Integration

### Setup

This application uses MongoDB to persist conversation history across sessions. The data is stored using the LangGraph checkpointing system with a MongoDB backend.

1. **Start MongoDB using Docker**:
   ```bash
   docker run -d --name mongodb -p 27017:27017 mongo
   ```

2. **Configure MongoDB connection**:
   Add the MongoDB URI to your `.env` file:
   ```
   MONGODB_URI=mongodb://localhost:27017/claude_memory
   ```

### Data Structure

- Conversations are stored in the `checkpointing_db` database
- The database contains two collections:
  - `checkpoints`: Stores the actual conversation data
  - `checkpoint_writes`: Tracks write operations

Each checkpoint includes:
- `thread_id`: Unique identifier for each conversation thread
- `checkpoint_id`: Unique identifier for each checkpoint
- `checkpoint`: Binary encoded conversation data (MessagePack format)
- `metadata`: Additional information about the checkpoint

### Exploring the Data

To explore the MongoDB data:

1. **Connect to the MongoDB container**:
   ```bash
   docker exec -it mongodb mongosh
   ```

2. **View databases**:
   ```
   show dbs
   ```

3. **Switch to the checkpoint database**:
   ```
   use checkpointing_db
   ```

4. **View collections**:
   ```
   show collections
   ```

5. **View all checkpoints**:
   ```
   db.checkpoints.find().pretty()
   ```

6. **View checkpoints for a specific thread**:
   ```
   db.checkpoints.find({thread_id: "your-thread-id"}).pretty()
   ```

7. **Count total checkpoints**:
   ```
   db.checkpoints.countDocuments()
   ```

8. **View all unique conversation threads**:
   ```
   db.checkpoints.distinct("thread_id")
   ```

### Testing MongoDB Integration

The repository includes a test script to verify MongoDB connectivity:

```bash
python test_mongo.py
```

This script creates a test checkpoint in MongoDB and retrieves it to verify the connection is working properly.

## License

This project is open source and available under the MIT License.

## Acknowledgements

- [Anthropic](https://www.anthropic.com/) for providing the Claude API
- [LangChain](https://www.langchain.com/) and [LangGraph](https://python.langchain.com/docs/langgraph) for the agent framework
- [Flask](https://flask.palletsprojects.com/) web framework
- [Socket.IO](https://socket.io/) for real-time communication
- [MongoDB](https://www.mongodb.com/) for persistence 