import os
import uvicorn
import gradio as gr
from app.main import app as fastapi_app

# Create a clean status page for Hugging Face Space landing
with gr.Blocks(title="DataSense AI Backend API") as demo:
    gr.Markdown("# ⚡ DataSense AI Production Backend API")
    gr.Markdown("FastAPI + DuckDB + Groq LLM + Hybrid RAG Engine is live and serving requests.")
    gr.Markdown("API Documentation: [Swagger Docs](/docs)")

# Mount FastAPI app onto Gradio
app = gr.mount_gradio_app(fastapi_app, demo, path="/")

if __name__ == "__main__":
    port = int(os.getenv("PORT", 7860))
    demo.launch(server_name="0.0.0.0", server_port=port)
