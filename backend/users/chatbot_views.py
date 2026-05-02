import os

from django.http import FileResponse
from dotenv import load_dotenv
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from users.models import ChatMessage, ChatSession


# ------------------ INIT ------------------



MODEL_NAME = "hosted_vllm/Llama-3.1-70B-Instruct"


# ------------------ PROMPTS ------------------
PROMPT_CHAT_CLASSIQUE = """..."""
PROMPT_REPORT_BENCHMARK = """..."""


def get_ai_clients():
    import chromadb
    from chromadb.utils import embedding_functions
    from openai import OpenAI

    import os
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    chroma_client = chromadb.PersistentClient(path=os.path.join(BASE_DIR, "ma_base_immo"))
    load_dotenv(os.path.join(BASE_DIR, ".env.local"))
    local_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="paraphrase-multilingual-mpnet-base-v2"
    )
    collection = chroma_client.get_collection(
        name="immo_knowledge",
        embedding_function=local_ef,
    )
    client = OpenAI(
        api_key=os.getenv("API_KEY"),
        base_url="https://tokenfactory.esprit.tn/api",
    )
    return collection, client


def repondre_a_la_question(ma_question):
    collection, client = get_ai_clients()
    mots_cles_rapport = ["rapport", "benchmark", "comparer", "comparaison", "benchmarking"]
    is_benchmark = any(mot in ma_question.lower() for mot in mots_cles_rapport)

    if is_benchmark:
        villes = [
            v.strip()
            for v in ma_question.lower().replace("entre", "").replace("et", ",").split(",")
            if v.strip()
        ]

        extraits = ""
        for ville in villes[:2]:
            res = collection.query(query_texts=[f"prix immobilier loyer standing à {ville}"], n_results=10)
            extraits += f"\n--- DONNÉES SPÉCIFIQUES POUR {ville.upper()} ---\n"
            extraits += "\n\n".join(res["documents"][0])

        prompt_final = PROMPT_REPORT_BENCHMARK.format(extraits=extraits, ma_question=ma_question)
    else:
        query_expert = f"prix immobilier m2 loyer standing quartier {ma_question}"
        resultats = collection.query(query_texts=[query_expert], n_results=20)
        extraits = "\n\n".join(resultats["documents"][0])
        prompt_final = PROMPT_CHAT_CLASSIQUE.format(extraits=extraits, ma_question=ma_question)

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": prompt_final}],
        temperature=0.3,
    )

    return response.choices[0].message.content


# ------------------ ROUTES ------------------
@api_view(["POST"])
@permission_classes([AllowAny])
def ask(request):
    question = (request.data.get("question") or "").strip()
    session_id = (request.data.get("session_id") or "").strip()

    if not question or not session_id:
        return Response({"detail": "Données manquantes"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        session, created = ChatSession.objects.get_or_create(
            session_id=session_id,
            defaults={
                "title": (question[:30] + "...") if len(question) > 30 else question
            },
        )
        if created and not session.title:
            title = (question[:30] + "...") if len(question) > 30 else question
            session.title = title
            session.save(update_fields=["title"])

        answer = repondre_a_la_question(question)

        ChatMessage.objects.create(session=session, role="user", content=question)
        ChatMessage.objects.create(session=session, role="assistant", content=answer)

        return Response({"answer": answer})
    except Exception as exc:
        import traceback
        print("\n--- ERREUR CHATBOT ---\n")
        traceback.print_exc()
        print("\n--- FIN ERREUR ---\n")
        return Response({"detail": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["POST"])
@permission_classes([AllowAny])
def generate_pdf(request):
    texte = (request.data.get("texte") or "").strip()

    if not texte:
        return Response({"detail": "Texte vide"}, status=status.HTTP_400_BAD_REQUEST)

    from pdf_generator import generer_pdf

    path = "rapport_lenstate.pdf"
    generer_pdf(texte, path)
    return FileResponse(open(path, "rb"), as_attachment=True, filename="Rapport_LensEstate.pdf")


@api_view(["GET"])
@permission_classes([AllowAny])
def get_user_sessions(request):
    sessions = ChatSession.objects.all().order_by("-created_at")
    sessions_list = [{"id": s.session_id, "title": s.title} for s in sessions]
    return Response(sessions_list)


@api_view(["GET"])
@permission_classes([AllowAny])
def get_conversation(request):
    session_id = request.query_params.get("session_id")
    if not session_id:
        return Response({"messages": []})

    try:
        session = ChatSession.objects.get(session_id=session_id)
    except ChatSession.DoesNotExist:
        return Response({"messages": []})

    formatted_messages = [
        {
            "id": msg.created_at.timestamp() if msg.created_at else 0,
            "role": msg.role,
            "text": msg.content,
        }
        for msg in session.messages.all()
    ]

    return Response({"messages": formatted_messages})
