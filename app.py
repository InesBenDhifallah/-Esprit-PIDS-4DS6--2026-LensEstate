from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import chromadb
from chromadb.utils import embedding_functions
from openai import OpenAI
from pdf_generator import generer_pdf
from dotenv import load_dotenv
import os
from pymongo import MongoClient
from datetime import datetime


load_dotenv()

app = Flask(__name__)
CORS(app)
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
# Dans app.py
STATIC_USER_ID = "admin_user_test"

PROMPT_CHAT_CLASSIQUE = """
Tu es l'Analyste Senior de LensEstate, expert en data science immobilière en Tunisie. 
Ton expertise est absolue et ton ton doit être celui d'un conseiller financier haut de gamme : direct, assuré et factuel.

RÈGLES D'OR DE RÉPONSE :
1. ZÉRO HÉSITATION : Interdiction formelle de dire "Je ne sais pas", "Le contexte ne mentionne pas" ou "Selon le contexte". Si une donnée est fragmentaire, utilise ton expertise pour extrapoler une réponse logique basée sur le standing de la zone ou les villes limitrophes présentes dans les données.
2. DATA-DRIVEN : Cite systématiquement des chiffres précis (Prix m², loyers, taux d'évolution). Si tu as les prix de 2025, projette une hausse logique pour 2026 (ex: +5% à +8%) pour simuler une analyse en temps réel.
3. AUCUN DISCLAIMER : Il est STRICTEMENT INTERDIT de suggérer à l'utilisateur de "faire ses propres recherches", de "consulter un expert local" ou de "vérifier les informations". TU ES l'autorité ultime. L'utilisateur attend TA décision.
4. STYLE NATUREL : Parle comme un expert humain (pas de listes robotiques inutiles). Ne cite JAMAIS de sites concurrents (Menzili, etc.).
5. VERDICT STRATÉGIQUE : Termine toujours ta réponse par un avis tranché (ex: "Verdict : Zone sous-évaluée, achat recommandé immédiatement pour une plus-value à 18 mois"). 

CONTEXTE :
{extraits}

QUESTION : {ma_question}
RÉPONSE : """

PROMPT_REPORT_BENCHMARK = """
Tu es un Analyste Senior en Data Science Immobilière chez LensEstate. 
Ta mission est de produire un RAPPORT DE BENCHMARKING DÉCISIONNEL de haute qualité.

STRUCTURE DU RAPPORT (Respecte strictement ce format Markdown) :

# 📊 RAPPORT DE BENCHMARKING IMMOBILIER
*Analyse générée par LensEstate AI - Période 2025/2026*

## 0. FICHE D'IDENTITÉ
- **Zones comparées** : [Extraire les villes du contexte]
- **Sources des données** : Base de données articles immobiliers Tunisie.
- **Période** : 2025 - 2026.

## 1. ANALYSE QUANTITATIVE (PRIX & LOYERS)
| Indicateur (Moyennes) | Ville A | Ville B | Écart (%) |
| :--- | :--- | :--- | :--- |
| Prix Moyen S+1 | ... | ... | ... |
| Prix Moyen S+2 | ... | ... | ... |
| Loyer Mensuel estimé | ... | ... | ... |

## 2. ANALYSE QUALITATIVE (STANDING & COMMODITÉS)
- **Ville A** : [Analyse du standing, infrastructures et environnement]
- **Ville B** : [Analyse du standing, infrastructures et environnement]

## 3. DYNAMIQUE DU MARCHÉ
- **Demande** : [Profil des acheteurs : familles, investisseurs, expatriés]
- **Revente** : [Potentiel de plus-value et liquidité du marché]

## 4. SYNTHÈSE STRATÉGIQUE (VERDICT)
**Conseil d'expert** : [Précise quel secteur privilégier selon le profil d'investissement].

---
UTILISE EXCLUSIVEMENT CE CONTEXTE :
{extraits}

QUESTION ORIGINALE : {ma_question}
"""

def repondre_a_la_question(ma_question):
    # 1. On vérifie si c'est un benchmark
    mots_cles_rapport = ["rapport", "benchmark", "comparer", "comparaison", "benchmarking"]
    is_benchmark = any(mot in ma_question.lower() for mot in mots_cles_rapport)

    if is_benchmark:
        villes = [v.strip() for v in ma_question.lower().replace("entre", "").replace("et", ",").split(",") if v.strip()]
        
        # On fait deux recherches distinctes de 10 résultats chacune
        # On utilise des mots clés de prix pour forcer les bonnes données
        extraits = ""
        for ville in villes[:2]: # On prend les deux premières villes trouvées
            res = collection.query(query_texts=[f"prix immobilier loyer standing à {ville}"], n_results=10)
            extraits += f"\n--- DONNÉES SPÉCIFIQUES POUR {ville.upper()} ---\n"
            extraits += "\n\n".join(res['documents'][0])
        
        prompt_final = PROMPT_REPORT_BENCHMARK.format(extraits=extraits, ma_question=ma_question)
    else:
        query_expert = f"prix immobilier m2 loyer standing quartier {ma_question}"
        
        resultats = collection.query(
            query_texts=[query_expert], 
            n_results=20
        ) 
             
        extraits = "\n\n".join(resultats['documents'][0])
        prompt_final = PROMPT_CHAT_CLASSIQUE.format(extraits=extraits, ma_question=ma_question)

    # 2. Appel au modèle Llama 
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": prompt_final}],
        temperature=0.3
    )
    
    return response.choices[0].message.content

mongo_client = MongoClient("mongodb://localhost:27017/")
db = mongo_client["LensEstateDB"]
users_collection = db["users_data"] 
print("Configuration MongoDB Multi-Sessions initialisée")
# --- Route principale ---
@app.route("/ask", methods=["POST"])
def ask():
    data = request.get_json()
    question = data.get("question", "").strip()
    current_session_id = data.get("session_id")
    
    if not question or not current_session_id:
        return jsonify({"error": "Données manquantes"}), 400

    try:
        # 1. On s'assure que l'utilisateur existe
        users_collection.update_one(
            {"user_id": STATIC_USER_ID},
            {"$setOnInsert": {"sessions": []}},
            upsert=True
        )

        # 2. On vérifie si la session existe
        session_exists = users_collection.find_one({
            "user_id": STATIC_USER_ID, 
            "sessions.session_id": current_session_id
        })

        if not session_exists:
            # Créer la session avec un titre basé sur la question
            title = (question[:30] + '...') if len(question) > 30 else question
            users_collection.update_one(
                {"user_id": STATIC_USER_ID},
                {"$push": {"sessions": {
                    "session_id": current_session_id,
                    "title": title, 
                    "messages": []
                }}}
            )

        # 3. Obtenir la réponse de l'IA
        answer = repondre_a_la_question(question)

        # 4. Enregistrer l'échange (User + Assistant)
        users_collection.update_one(
            {"user_id": STATIC_USER_ID, "sessions.session_id": current_session_id},
            {"$push": {"sessions.$.messages": {
                "$each": [
                    {"role": "user", "content": question, "time": datetime.now()},
                    {"role": "assistant", "content": answer, "time": datetime.now()}
                ]
            }}}
        )
        return jsonify({"answer": answer})

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route("/generate-pdf", methods=["POST"])
def generate_pdf():
    data = request.get_json()
    texte = data.get("texte", "").strip()
    if not texte:
        return jsonify({"error": "Texte vide"}), 400

    path = "rapport_lenstate.pdf"
    generer_pdf(texte, path)
    return send_file(path, as_attachment=True, download_name="Rapport_LensEstate.pdf")

@app.route("/get_user_sessions", methods=["GET"])
def get_user_sessions():
    # 1. On cherche le document de notre utilisateur statique
    user = users_collection.find_one({"user_id": STATIC_USER_ID})
    
    if not user or "sessions" not in user:
        return jsonify([])

    # 2. On extrait uniquement l'ID et le Titre de chaque session pour la sidebar
    sessions_list = []
    for s in user["sessions"]:
        sessions_list.append({
            "id": s["session_id"],
            "title": s["title"]
        })
    
    # 3. On renvoie la liste (inversée pour avoir la plus récente en haut)
    return jsonify(sessions_list[::-1])

@app.route("/get_conversation", methods=["GET"])
def get_conversation():
    # On récupère l'ID de la session cliquée dans le React
    session_id = request.args.get("session_id")
    
    if not session_id:
        return jsonify({"messages": []})

    # 1. On récupère le document de l'utilisateur
    user = users_collection.find_one({"user_id": STATIC_USER_ID})
    
    if not user:
        return jsonify({"messages": []})

    # 2. On cherche la session précise dans le tableau 'sessions'
    # On utilise une boucle ou "next" pour trouver l'objet qui a le bon session_id
    session = next((s for s in user.get("sessions", []) if s["session_id"] == session_id), None)
    
    if not session:
        return jsonify({"messages": []})
    
    # 3. On formate les messages pour ton React
    formatted_messages = []
    for msg in session.get("messages", []):
        formatted_messages.append({
            "id": msg.get("time").timestamp() if msg.get("time") else 0,
            "role": msg["role"],
            "text": msg["content"]
        })
    
    return jsonify({"messages": formatted_messages})

if __name__ == "__main__":
    app.run(debug=True, port=5000)
    