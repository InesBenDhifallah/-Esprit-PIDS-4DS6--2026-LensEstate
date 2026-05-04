from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import sys
import io
import os
from dotenv import load_dotenv
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

import chromadb
from chromadb.utils import embedding_functions
from openai import OpenAI
from pdf_generator import generer_pdf
from pymongo import MongoClient
from datetime import datetime

# Add housegan to path
current_dir = os.path.dirname(__file__)
sys.path.append(current_dir)
sys.path.append(os.path.join(current_dir, "housegan"))

from housegan.inference_helper import generate_plan_from_graph


# ------------------ INIT ------------------
load_dotenv()

app = FastAPI()

class PlanRequest(BaseModel):
    rooms: list[str]
    edges: list[list[int]]

@app.post("/generate-plan")
async def generate_plan_api(data: PlanRequest):
    try:
        img = generate_plan_from_graph(data.rooms, data.edges, checkpoint_path='./housegan/checkpoints/exp_demo_D_500000.pth')
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return StreamingResponse(buf, media_type="image/png")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------ IA (MOCKED FOR DEMO) ------------------
# chroma_client = chromadb.PersistentClient(path="./ma_base_immo")
# local_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
#     model_name="paraphrase-multilingual-mpnet-base-v2"
# )

# collection = chroma_client.get_collection(
#     name="immo_knowledge",
#     embedding_function=local_ef
# )

# client = OpenAI(
#     api_key=os.getenv("API_KEY"),
#     base_url="https://tokenfactory.esprit.tn/api",
# )

MODEL_NAME = "hosted_vllm/Llama-3.1-70B-Instruct"
STATIC_USER_ID = "admin_user_test"

# ------------------ MODELS ------------------
class AskRequest(BaseModel):
    question: str
    session_id: str

class PDFRequest(BaseModel):
    texte: str

# ------------------ PROMPTS ------------------
PROMPT_CHAT_CLASSIQUE = """..."""
PROMPT_REPORT_BENCHMARK = """..."""

# ------------------ IA FUNCTION ------------------
def repondre_a_la_question(ma_question):
    return "This is a placeholder response (AI model loading skipped)."

# ------------------ MONGO ------------------
mongo_client = MongoClient("mongodb://localhost:27017/")
db = mongo_client["LensEstateDB"]
users_collection = db["users_data"]

# ------------------ ROUTES ------------------

@app.post("/ask")
async def ask(data: AskRequest):
    question = data.question.strip()
    session_id = data.session_id

    if not question or not session_id:
        raise HTTPException(status_code=400, detail="Données manquantes")

    try:
        # Créer user si non existant
        users_collection.update_one(
            {"user_id": STATIC_USER_ID},
            {"$setOnInsert": {"sessions": []}},
            upsert=True
        )

        # Vérifier session
        session_exists = users_collection.find_one({
            "user_id": STATIC_USER_ID,
            "sessions.session_id": session_id
        })

        if not session_exists:
            title = (question[:30] + '...') if len(question) > 30 else question
            users_collection.update_one(
                {"user_id": STATIC_USER_ID},
                {"$push": {"sessions": {
                    "session_id": session_id,
                    "title": title,
                    "messages": []
                }}}
            )

        # IA
        answer = repondre_a_la_question(question)

        # Save messages
        users_collection.update_one(
            {"user_id": STATIC_USER_ID, "sessions.session_id": session_id},
            {"$push": {"sessions.$.messages": {
                "$each": [
                    {"role": "user", "content": question, "time": datetime.now()},
                    {"role": "assistant", "content": answer, "time": datetime.now()}
                ]
            }}}
        )

        return {"answer": answer}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate-pdf")
async def generate_pdf(data: PDFRequest):
    texte = data.texte.strip()

    if not texte:
        raise HTTPException(status_code=400, detail="Texte vide")

    path = "rapport_lenstate.pdf"
    generer_pdf(texte, path)

    return FileResponse(path, filename="Rapport_LensEstate.pdf")


@app.get("/get_user_sessions")
async def get_user_sessions():
    user = users_collection.find_one({"user_id": STATIC_USER_ID})

    if not user or "sessions" not in user:
        return []

    sessions_list = [
        {"id": s["session_id"], "title": s["title"]}
        for s in user["sessions"]
    ]

    return sessions_list[::-1]


@app.get("/get_conversation")
async def get_conversation(session_id: str = Query(...)):
    user = users_collection.find_one({"user_id": STATIC_USER_ID})

    if not user:
        return {"messages": []}

    session = next(
        (s for s in user.get("sessions", []) if s["session_id"] == session_id),
        None
    )

    if not session:
        return {"messages": []}

    formatted_messages = [
        {
            "id": msg.get("time").timestamp() if msg.get("time") else 0,
            "role": msg["role"],
            "text": msg["content"]
        }
        for msg in session.get("messages", [])
    ]

    return {"messages": formatted_messages}