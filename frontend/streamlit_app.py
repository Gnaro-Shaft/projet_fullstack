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
        .block-container { max-width: 720px; padding: 2rem 1.5rem 3rem; margin: 0 auto; }
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
        .consent-box {
            max-width: 540px; margin: 3rem auto;
            background: #fff; border: 1px solid #ddd;
            border-radius: 8px; padding: 2rem 2rem 1.5rem;
            box-shadow: 0 4px 16px rgba(0,0,0,0.08);
        }
        .consent-box h2 { margin: 0 0 0.5rem; color: #161616; font-size: 1.3rem; }
        .consent-box p { color: #555; font-size: 0.92rem; line-height: 1.5; margin: 0 0 1.2rem; }
        .consent-box ul { color: #555; font-size: 0.88rem; padding-left: 1.2rem; margin: 0 0 1.2rem; }
        .consent-box li { margin-bottom: 0.4rem; }
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


def send_feedback(request_id: str, score: str) -> bool:
    try:
        r = httpx.post(f"{BACKEND_URL}/feedback", json={"request_id": request_id, "score": score}, timeout=10.0)
        return r.status_code == 200
    except Exception:
        return False


def display_feedback(msg_index: int) -> None:
    key = f"feedback_{msg_index}"
    if key not in st.session_state:
        st.session_state[key] = None
    current = st.session_state[key]
    msg = st.session_state.messages[msg_index]
    request_id = msg.get("request_id", "")
    col1, col2, col3 = st.columns([1, 1, 8])
    thumbs_up = col1.button("\U0001f44d", key=f"up_{msg_index}", help="Utile")
    thumbs_down = col2.button("\U0001f44e", key=f"down_{msg_index}", help="Pas utile")
    if thumbs_up:
        if request_id:
            send_feedback(request_id, "positive")
        st.session_state[key] = "up"
        st.rerun()
    if thumbs_down:
        if request_id:
            send_feedback(request_id, "negative")
        st.session_state[key] = "down"
        st.rerun()
    if current == "up":
        col1.markdown("\U0001f44d **Utile**")
    elif current == "down":
        col2.markdown("\U0001f44e **Pas utile**")


def main() -> None:
    apply_style()

    st.sidebar.page_link("pages/\U0001f4ca_Dashboard.py", label="\U0001f4ca Dashboard")

    if not st.session_state.get("consent_given"):
        st.markdown(
            '<div class="consent-box">'
            "<h2>Protection de vos donnees</h2>"
            "<p>Cet assistant utilise une IA pour vous aider dans vos demarches "
            "administratives. Conformement au RGPD, nous collectons :</p>"
            "<ul>"
            "<li>L'empreinte chiffree (hash) de votre question - pas le texte brut</li>"
            "<li>Votre adresse IP (anonymisee, dernier octet masque)</li>"
            "<li>Le navigateur utilise</li>"
            "<li>Le temps de reponse et les sources consulrees</li>"
            "</ul>"
            "<p>Aucune donnee personnelle n'est stockee en clair. "
            "Vous pouvez demander l'effacement de vos traces a tout moment.</p>"
            "</div>",
            unsafe_allow_html=True,
        )
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("Accepter et continuer", type="primary", use_container_width=True):
                st.session_state.consent_given = True
                st.rerun()
        return

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

    st.markdown('<div style="max-width:660px;margin:0 auto;">', unsafe_allow_html=True)

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for i, msg in enumerate(st.session_state.messages):
        if msg["role"] == "user":
            st.markdown(
                f'<div style="background:#f0f0ff;border-left:4px solid #000091;'
                f'padding:0.8rem 1rem;margin:0.8rem 0;border-radius:4px;">'
                f'{msg["content"]}</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'<div style="background:#fff;border:1px solid #ddd;'
                f'border-top:4px solid #2a2a2a;'
                f'padding:0.8rem 1rem;margin:0.8rem 0;border-radius:4px;">'
                f'{msg["content"]}</div>',
                unsafe_allow_html=True,
            )
        if msg.get("time_ms"):
            st.caption(f"Répondu en {msg['time_ms']} ms")
        if msg.get("sources"):
            display_sources(msg["sources"])
        if msg["role"] == "assistant":
            display_feedback(i)

    st.markdown("</div>", unsafe_allow_html=True)

    with st.form("question_form", clear_on_submit=True):
        st.markdown('<div style="max-width:660px;margin:0 auto;">', unsafe_allow_html=True)
        question = st.text_area(
            "Votre question",
            placeholder="Exemple : quelles sont les conditions pour obtenir un logement social ?",
            height=100,
            label_visibility="collapsed",
        )
        submitted = st.form_submit_button("Envoyer", type="primary", use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

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

        st.session_state.messages = [
            {"role": "user", "content": clean_question},
            {
                "role": "assistant",
                "content": answer,
                "sources": sources,
                "time_ms": time_ms,
                "request_id": result.get("request_id", ""),
            },
        ]
        st.rerun()


if __name__ == "__main__":
    main()
