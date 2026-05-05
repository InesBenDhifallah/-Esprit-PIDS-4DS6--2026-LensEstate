from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
import io
from fastapi.responses import StreamingResponse
from inference_helper import generate_plan_from_graph
import uvicorn
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class GraphInput(BaseModel):
    rooms: List[str]
    edges: List[List[int]]

@app.post("/generate")
async def generate(data: GraphInput):
    try:
        img = generate_plan_from_graph(data.rooms, data.edges)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return StreamingResponse(buf, media_type="image/png")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
