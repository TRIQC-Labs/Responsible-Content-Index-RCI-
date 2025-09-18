# main.py (FastAPI UI server, not CLI)
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from controller import evaluate_text_stream
import json

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/evaluate")
def evaluate(text: str):
    def gen():
        for evt in evaluate_text_stream(text):
            # You can also include a named event line if you want:
            # yield f"event: {evt.get('event','message')}\n"
            yield f"data: {json.dumps(evt, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # disable proxy buffering if any
            # "Connection": "keep-alive",  # some proxies ignore this; SSE works without it
        },
    )