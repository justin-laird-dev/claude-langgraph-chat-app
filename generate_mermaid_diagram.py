#!/usr/bin/env python3
"""
Generate a PNG diagram from the LangGraph agent graph
"""
import os
import sys
from dotenv import load_dotenv
from langchain_core.runnables.graph import MermaidDrawMethod

def generate_diagram():
    # Load environment variables required by the agent
    load_dotenv()
    
    try:
        # Import the agent class that contains the graph
        from utils.langgraph_agent import ClaudeLangGraphAgent
        
        print("Initializing the agent from langgraph_agent.py...")
        agent = ClaudeLangGraphAgent()
        
        # Get the graph from the agent instance
        graph = agent.graph
        
      
        # Generate PNG using the API
        png_file = "graph.png"
        print(f"Generating PNG visualization to {png_file}...")
        
        # Generate PNG data using Mermaid.ink API
        png_data = graph.get_graph().draw_mermaid_png(
            draw_method=MermaidDrawMethod.API
        )
        
        # Save the PNG data to a file
        with open(png_file, "wb") as f:
            f.write(png_data)
        
        print(f"PNG saved to {os.path.abspath(png_file)}")
        return True
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        print("\nMake sure you have valid API credentials in your .env file.")
        return False

if __name__ == "__main__":
    print("=== Generating PNG diagram from LangGraph Agent ===")
    success = generate_diagram()
    sys.exit(0 if success else 1) 