from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

import chromadb
from chromadb.utils import embedding_functions
from openai import OpenAI
from pdf_generator import generer_pdf
from dotenv import load_dotenv
import os
from pymongo import MongoClient
from datetime import datetime

# ------------------ INIT ------------------
load_dotenv()

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------ IA ------------------
chroma_client = chromadb.PersistentClient(path="./ma_base_immo")
local_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="paraphrase-multilingual-mpnet-base-v2"
)

collection = chroma_client.get_collection(
    name="immo_knowledge",
    embedding_function=local_ef
)

client = OpenAI(
    api_key=os.getenv("API_KEY"),
    base_url="https://tokenfactory.esprit.tn/api",
)

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
    mots_cles_rapport = ["rapport", "benchmark", "comparer", "comparaison", "benchmarking"]
    is_benchmark = any(mot in ma_question.lower() for mot in mots_cles_rapport)

    if is_benchmark:
        villes = [v.strip() for v in ma_question.lower().replace("entre", "").replace("et", ",").split(",") if v.strip()]
        
        extraits = ""
        for ville in villes[:2]:
            res = collection.query(query_texts=[f"prix immobilier loyer standing à {ville}"], n_results=10)
            extraits += f"\n--- DONNÉES SPÉCIFIQUES POUR {ville.upper()} ---\n"
            extraits += "\n\n".join(res['documents'][0])
        
        prompt_final = PROMPT_REPORT_BENCHMARK.format(extraits=extraits, ma_question=ma_question)
    else:
        query_expert = f"prix immobilier m2 loyer standing quartier {ma_question}"
        resultats = collection.query(query_texts=[query_expert], n_results=20)
        extraits = "\n\n".join(resultats['documents'][0])
        prompt_final = PROMPT_CHAT_CLASSIQUE.format(extraits=extraits, ma_question=ma_question)

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": prompt_final}],
        temperature=0.3
    )

    return response.choices[0].message.content

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