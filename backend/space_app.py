import sys
import os
import huggingface_hub

# Compatibility shim for Gradio + huggingface_hub 0.25+
if not hasattr(huggingface_hub, "HfFolder"):
    class HfFolder:
        @staticmethod
        def get_token():
            return os.getenv("HF_TOKEN", None)
        @staticmethod
        def save_token(token):
            pass
    huggingface_hub.HfFolder = HfFolder

# Ensure current directory is on sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

import gradio as gr
from app.main import app as fastapi_app

# Create a clean status page for Hugging Face Space landing
with gr.Blocks(title="DataSense AI Backend API") as demo:
    gr.Markdown("# ⚡ DataSense AI Production Backend API")
    gr.Markdown("FastAPI + DuckDB + Groq LLM + Hybrid RAG Engine is live and serving requests.")
    gr.Markdown("API Documentation: [Swagger Docs](/docs)")

# Mount FastAPI app onto Gradio
app = gr.mount_gradio_app(fastapi_app, demo, path="/")

# Launch server and block main thread to keep Hugging Face Space container alive
port = int(os.getenv("PORT", 7860))
demo.launch(server_name="0.0.0.0", server_port=port)
