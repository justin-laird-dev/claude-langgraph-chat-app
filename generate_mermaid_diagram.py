#!/usr/bin/env python3
"""
Generate a PNG diagram from the LangGraph agent graph
"""
import os
import sys
from dotenv import load_dotenv

# Import the MermaidDrawMethod, trying both possible import paths
try:
    from langchain_core.runnables.graph import CurveStyle, MermaidDrawMethod, NodeStyles
except ImportError:
    # This might be a newer version with a different import structure
    try:
        from langchain.graphs import CurveStyle, MermaidDrawMethod, NodeStyles
    except ImportError:
        print("Unable to import diagram generation classes")
        sys.exit(1)

def save_graph_visualization(output_file="graph.png"):
    """Save the graph visualization as PNG using Mermaid + Pyppeteer."""
    try:
        # Load environment variables for API keys
        load_dotenv()
        
        # Initialize agent and get its graph
        from utils.langgraph_agent import ClaudeLangGraphAgent
        agent = ClaudeLangGraphAgent()
        graph = agent.graph
        
        # Get the graph and generate PNG
        print(f"Generating graph visualization to {output_file}...")
        graph.get_graph().draw_mermaid_png(
            curve_style=CurveStyle.LINEAR,
            node_colors=NodeStyles(
                first="#ffdfba",
                last="#baffc9", 
                default="#fad7de"
            ),
            wrap_label_n_words=9,
            output_file_path=output_file,
            draw_method=MermaidDrawMethod.PYPPETEER,
            background_color="white",
            padding=10,
        )
        print(f"Graph visualization saved to {output_file}")
        
    except Exception as e:
        print(f"Error generating graph visualization: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    save_graph_visualization() 