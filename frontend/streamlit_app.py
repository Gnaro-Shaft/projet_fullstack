"""Interface Streamlit minimale pour l'assistant Service Public."""

import os

import httpx
import streamlit as st
from dotenv import load_dotenv


load_dotenv()
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")

st.set_page_config(
    page_title="Assistant Service Public",
    page_icon="🇫🇷",
    layout="centered",
)


def apply_simple_style() -> None:
    """Applique une présentation blanche, centrée et institutionnelle."""
    st.markdown(
        """
        <style>
        .stApp { background: #ffffff; }
        .block-container {
            max-width: 860px;
            padding: 5rem 1.5rem 3rem;
        }
        .page-title {
            border-top: 5px solid #000091;
            padding-top: 1.5rem;
            text-align: center;
        }
        .page-title h1 {
            color: #161616;
            font-size: 2.5rem;
            margin-bottom: 0.8rem;
        }
        .page-title p {
            color: #555555;
            font-size: 1.2rem;
            margin-bottom: 2.5rem;
        }
        .assistant-box {
            background: #f6f6f6;
            border: 1px solid #dddddd;
            border-top: 4px solid #e1000f;
            padding: 1.2rem 1.4rem;
            margin: 1.5rem 0;
        }
        .ai-notice {
            background: #e3e3fd;
            border-left: 4px solid #000091;
            color: #161616;
            padding: 0.8rem 1rem;
            margin: 1rem 0;
            font-size: 0.95rem;
        }
        .legal-disclaimer {
            color: #555555;
            font-size: 0.85rem;
            margin-top: 1rem;
        }
        .source-card {
            background: #f6f6f6;
            border-left: 4px solid #000091;
            padding: 0.7rem 1rem;
            margin: 0.5rem 0;
        }
        .source-card a { color: #000091; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def ask_backend(question: str) -> dict:
    """Envoie une question au backend FastAPI."""
    try:
        response = httpx.post(
            f"{BACKEND_URL}/chat",
            json={"message": question},
            timeout=90.0,
        )
        response.raise_for_status()
        return response.json()
    except httpx.HTTPError as error:
        return {"error": f"Le backend est indisponible : {error}"}


def display_sources(sources: list[dict]) -> None:
    """Affiche les liens officiels associés à une réponse."""
    if not sources:
        return

    st.markdown("**Sources officielles**")
    for source in sources:
        title = source.get("title") or source.get("document_id") or "Fiche Service Public"
        url = source.get("url")
        if url:
            metadata_parts = []
            if source.get("modified_at"):
                metadata_parts.append(f"Mise à jour : {source['modified_at']}")
            if source.get("effective_at"):
                metadata_parts.append(f"Entrée en vigueur : {source['effective_at']}")
            if source.get("status"):
                metadata_parts.append(f"Statut : {source['status']}")
            metadata = "<br><small>" + " · ".join(metadata_parts) + "</small>" if metadata_parts else ""
            st.markdown(
                f'<div class="source-card"><a href="{url}" target="_blank">{title}</a>{metadata}</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(f'<div class="source-card">{title}</div>', unsafe_allow_html=True)


def main() -> None:
    apply_simple_style()

    # En-tête volontairement court : le produit principal est le chat.
    st.markdown(
        """
        <div class="page-title">
          <h1>Assistant Service Public</h1>
          <p>Une question sur vos droits ? Nous vous aidons à trouver l'information officielle.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="ai-notice"><strong>Assistant utilisant une IA</strong><br>'
        "Les réponses sont générées automatiquement à partir de sources officielles. "
        "Vérifiez toujours la source avant d'entreprendre une démarche.</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="legal-disclaimer">Information générale : cette réponse ne constitue pas un avis juridique personnalisé.</div>',
        unsafe_allow_html=True,
    )

    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Une seule question et une seule réponse sont affichées à la fois.
    # Cela évite d'allonger la page à chaque nouvelle recherche.
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message.get("sources"):
                display_sources(message["sources"])

    st.markdown('<div class="assistant-box">Posez votre question sur vos droits et démarches administratives.</div>', unsafe_allow_html=True)

    # Un formulaire centré est utilisé plutôt que le chat_input fixe en bas de l'écran.
    with st.form("question_form", clear_on_submit=True):
        question = st.text_area(
            "Votre question",
            placeholder="Exemple : quelles sont les conditions pour obtenir un logement social ?",
            height=100,
            label_visibility="collapsed",
        )
        submitted = st.form_submit_button("Envoyer", type="primary", use_container_width=True)

    if submitted and question.strip():
        clean_question = question.strip()
        with st.spinner("Recherche dans les fiches officielles…"):
            result = ask_backend(clean_question)

        if "error" in result:
            answer = result["error"]
            sources = []
        else:
            answer = result.get("response", "Aucune réponse reçue.")
            sources = result.get("sources", [])

        # On remplace l'ancien échange au lieu de l'ajouter à l'historique.
        st.session_state.messages = [
            {"role": "user", "content": clean_question},
            {"role": "assistant", "content": answer, "sources": sources},
        ]
        st.rerun()


if __name__ == "__main__":
    main()
