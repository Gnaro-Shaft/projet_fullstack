import os

import httpx
import streamlit as st
from dotenv import load_dotenv


load_dotenv()
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")

st.set_page_config(
    page_title="Assistant Service Public",
    page_icon="\U0001f1eb\U0001f1f7",
    layout="centered",
)


def apply_style() -> None:
    st.markdown(
        """
        <style>
        .stApp { background: #ffffff; }
        .block-container { max-width: 860px; padding: 3rem 1.5rem 3rem; }
        .title {
            border-top: 5px solid #000091; padding-top: 1.5rem; text-align: center;
        }
        .title h1 { color: #161616; font-size: 2.2rem; margin-bottom: 0.5rem; }
        .title p { color: #555; font-size: 1.1rem; margin-bottom: 1.5rem; }
        .ai-notice {
            background: #e3e3fd; border-left: 4px solid #000091;
            padding: 0.7rem 1rem; margin: 1rem 0; font-size: 0.9rem;
        }
        .disclaimer {
            color: #555; font-size: 0.82rem; margin-top: 0.5rem;
        }
        .source-card {
            background: #f6f6f6; border-left: 4px solid #000091;
            padding: 0.5rem 0.8rem; margin: 0.4rem 0;
        }
        .source-card a { color: #000091; }
        .feedback-btn {
            background: none; border: 1px solid #ccc; border-radius: 4px;
            padding: 2px 8px; cursor: pointer; font-size: 0.85rem;
        }
        .status-dot {
            display: inline-block; width: 8px; height: 8px;
            border-radius: 50%; margin-right: 6px;
        }
        .msg-user {
            background: #f0f0ff;
            border-left: 4px solid #000091;
            padding: 1rem 1.2rem;
            margin: 1rem 0;
            border-radius: 4px;
        }
        .msg-assistant {
            background: #fff;
            border: 1px solid #ddd;
            border-top: 4px solid #e1000f;
            padding: 1rem 1.2rem;
            margin: 1rem 0;
            border-radius: 4px;
        }
        .msg-assistant p { margin: 0; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def ask_backend(question: str) -> dict:
    try:
        with httpx.Client(timeout=90.0) as client:
            response = client.post(f"{BACKEND_URL}/chat", json={"message": question})
            response.raise_for_status()
            elapsed = response.headers.get("x-response-time-ms", "")
            return {**response.json(), "response_time_ms": elapsed}
    except httpx.HTTPError as error:
        return {"error": f"Le backend est indisponible : {error}"}


def check_backend_status() -> str:
    try:
        r = httpx.get(f"{BACKEND_URL}/ping", timeout=5.0)
        return "connecté" if r.status_code == 200 else "indisponible"
    except Exception:
        return "hors ligne"


def display_sources(sources: list[dict]) -> None:
    if not sources:
        return
    st.markdown("**Sources officielles**")
    for source in sources:
        title = source.get("title") or source.get("document_id") or "Fiche Service Public"
        url = source.get("url")
        parts = []
        if source.get("modified_at"):
            parts.append(f"Mise à jour : {source['modified_at']}")
        if source.get("effective_at"):
            parts.append(f"Entrée en vigueur : {source['effective_at']}")
        if source.get("status"):
            parts.append(f"Statut : {source['status']}")
        meta = f"<br><small>{' · '.join(parts)}</small>" if parts else ""
        if url:
            st.markdown(f'<div class="source-card"><a href="{url}" target="_blank">{title}</a>{meta}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="source-card">{title}{meta}</div>', unsafe_allow_html=True)


def display_feedback(msg_index: int) -> None:
    key = f"feedback_{msg_index}"
    if key not in st.session_state:
        st.session_state[key] = None
    current = st.session_state[key]
    col1, col2, col3 = st.columns([1, 1, 8])
    thumbs_up = col1.button("\U0001f44d", key=f"up_{msg_index}", help="Utile")
    thumbs_down = col2.button("\U0001f44e", key=f"down_{msg_index}", help="Pas utile")
    if thumbs_up:
        st.session_state[key] = "up"
        st.rerun()
    if thumbs_down:
        st.session_state[key] = "down"
        st.rerun()
    if current == "up":
        col1.markdown("\U0001f44d **Utile**")
    elif current == "down":
        col2.markdown("\U0001f44e **Pas utile**")


def main() -> None:
    apply_style()

    status = check_backend_status()
    dot_color = {"connecté": "#00a83e", "indisponible": "#fa5c5c", "hors ligne": "#fa5c5c"}
    bg = dot_color.get(status, "#888")
    st.markdown(
        f'<div style="text-align:right;font-size:0.8rem;color:#888;">'
        f'<span class="status-dot" style="background:{bg}"></span>'
        f'Backend {status}</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="title"><h1>Assistant Service Public</h1>'
        "<p>Une question sur vos droits ? Nous vous aidons à trouver l'information officielle.</p></div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="ai-notice"><strong>Assistant utilisant une IA</strong><br>'
        "Les réponses sont générées à partir de sources officielles. "
        "Vérifiez toujours la source avant d'entreprendre une démarche.</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="disclaimer">Information générale : cette réponse ne constitue pas un avis juridique personnalisé.</div>',
        unsafe_allow_html=True,
    )

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for i, msg in enumerate(st.session_state.messages):
        css_class = "msg-user" if msg["role"] == "user" else "msg-assistant"
        st.markdown(f'<div class="{css_class}">{msg["content"]}</div>', unsafe_allow_html=True)
        if msg.get("time_ms"):
            st.caption(f"Répondu en {msg['time_ms']} ms")
        if msg.get("sources"):
            display_sources(msg["sources"])
        if msg["role"] == "assistant":
            display_feedback(i)

    if st.session_state.messages:
        if st.button("Nouvelle conversation", type="secondary", use_container_width=True):
            st.session_state.messages = []
            st.rerun()

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
        with st.spinner("Recherche dans les fiches officielles\u2026"):
            result = ask_backend(clean_question)

        if "error" in result:
            answer = result["error"]
            sources = []
            time_ms = ""
        else:
            answer = result.get("response", "Aucune réponse reçue.")
            sources = result.get("sources", [])
            time_ms = result.get("response_time_ms", "")

        st.session_state.messages.append({"role": "user", "content": clean_question})
        st.session_state.messages.append({
            "role": "assistant",
            "content": answer,
            "sources": sources,
            "time_ms": time_ms,
        })
        st.rerun()


if __name__ == "__main__":
    main()
