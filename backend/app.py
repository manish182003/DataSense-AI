import os
import sys
import importlib

# Ensure current directory is on python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

import gradio as gr

# Load app.main explicitly to avoid module name collision between app.py and app/ directory
main_mod = importlib.import_module("app.main")
fastapi_app = main_mod.app

# Create a clean status page for Hugging Face Space landing
with gr.Blocks(title="DataSense AI Backend API") as demo:
    gr.Markdown("# ⚡ DataSense AI Production Backend API")
    gr.Markdown("FastAPI + DuckDB + Groq LLM + Hybrid RAG Engine is live and serving requests.")
    gr.Markdown("API Documentation: [Swagger Docs](/docs)")

# Mount FastAPI app onto Gradio
app = gr.mount_gradio_app(fastapi_app, demo, path="/")
