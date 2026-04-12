from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import chromadb
from chromadb.utils import embedding_functions
from openai import OpenAI
from pdf_generator import generer_pdf
from dotenv import load_dotenv
import os

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


PROMPT_CHAT_CLASSIQUE = """
Tu es un assistant expert de l'immobilier en Tunisie. 
RÈGLES STRICTES :
1. Utilise EXCLUSIVEMENT le CONTEXTE ci-dessous.
2. Si la réponse n'est pas dans le contexte, dis poliment que tu ne sais pas.
3. Réponds de façon naturelle et professionnelle.

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
        # STRATÉGIE HYBRIDE : On sépare les recherches
        # On essaie d'extraire les villes (exemple simple ici, à adapter selon tes besoins)
        # Si ta question est "Benchmarking entre Ezzahra et Hammamet" :
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
        resultats = collection.query(query_texts=[ma_question], n_results=10)
        extraits = "\n\n".join(resultats['documents'][0])
        prompt_final = PROMPT_CHAT_CLASSIQUE.format(extraits=extraits, ma_question=ma_question)

    # 2. Appel au modèle Llama 
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": prompt_final}],
        temperature=0.3
    )
    
    return response.choices[0].message.content
# --- Route principale ---
@app.route("/ask", methods=["POST"])
def ask():
    data = request.get_json()
    question = data.get("question", "").strip()
    if not question:
        return jsonify({"error": "Question vide"}), 400
    try:
        answer = repondre_a_la_question(question)
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


if __name__ == "__main__":
    app.run(debug=True, port=5000)