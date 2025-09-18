# main.py UI only no CLI
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from controller import evaluate_text_stream
import json
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/evaluate")
async def evaluate(text: str):
    async def event_generator():
        async for event in evaluate_text_stream(text):
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")