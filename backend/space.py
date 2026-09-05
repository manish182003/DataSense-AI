import gradio as gr
from app.main import app as fastapi_app

# Create a clean status page for Hugging Face Space landing
with gr.Blocks(title="DataSense AI Backend API") as demo:
    gr.Markdown("# ⚡ DataSense AI Production Backend API")
    gr.Markdown("FastAPI + DuckDB + Groq LLM + Hybrid RAG Engine is live and serving requests.")
    gr.Markdown("API Documentation: [Swagger Docs](/docs)")

# Mount FastAPI app onto Gradio
app = gr.mount_gradio_app(fastapi_app, demo, path="/")
