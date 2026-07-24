import os
from pathlib import Path

import httpx
import streamlit as st
from dotenv import load_dotenv

load_dotenv()
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")
AUDIT_LOG = Path("data/audit/chat_audit.jsonl")

st.set_page_config(page_title="Dashboard TrustRAG", page_icon="\U0001f4ca", layout="wide")


def fetch_json(path: str) -> dict | None:
    try:
        r = httpx.get(f"{BACKEND_URL}{path}", timeout=10.0)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def read_audit_log() -> list[dict]:
    if not AUDIT_LOG.exists():
        return []
    lines = AUDIT_LOG.read_text(encoding="utf-8").strip().split("\n")
    results = []
    for line in lines:
        if not line.strip():
            continue
        try:
            import json
            results.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return results


def format_uptime(seconds: float) -> str:
    hours, remainder = divmod(int(seconds), 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours}h {minutes}m {secs}s"


def main() -> None:
    st.title("\U0001f4ca Dashboard TrustRAG")
    st.caption(f"Backend : {BACKEND_URL}")

    metrics = fetch_json("/metrics")
    health = fetch_json("/health")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        status = "ok" if health else "hors ligne"
        st.metric("\u2697\ufe0f Statut backend", status.upper(), delta=None)
    with col2:
        chats = metrics.get("chat_requests_total", 0) if metrics else 0
        st.metric("\U0001f4ac Requêtes chat", chats)
    with col3:
        pts = metrics.get("collection", {}).get("points_count", 0) if metrics else 0
        st.metric("\U0001f4be Documents indexés", pts)
    with col4:
        uptime = metrics.get("uptime_seconds", 0) if metrics else 0
        st.metric("\u23f1\ufe0f Uptime", format_uptime(uptime))

    if health is not None:
        st.subheader("\U0001f3af Healthcheck")
        cols = st.columns(3)
        for i, (service, status_val) in enumerate(health.items()):
            with cols[i]:
                ok = status_val == "ok"
                st.metric(service, "\u2705 OK" if ok else f"\u274c {status_val}")
    else:
        st.error("\u274c Healthcheck: backend injoignable")

    st.subheader("\U0001f4cb Dernières requêtes")
    logs = read_audit_log()
    if logs:
        recent = logs[-10:]
        recent.reverse()
        for entry in recent:
            ts = entry.get("timestamp", "")[:19]
            q_sha = entry.get("question_sha256", "")[:12]
            src_count = len(entry.get("sources", []))
            rlen = entry.get("response_length", 0)
            st.markdown(
                f"`{ts}` \u2022 `{q_sha}` \u2022 {src_count} sources \u2022 {rlen} car."
            )
    else:
        st.info("Aucune requête pour l'instant.")

    with st.expander("\U0001f4ca Métriques détaillées (JSON)"):
        if metrics:
            st.json(metrics)
        if health:
            st.json(health)


if __name__ == "__main__":
    main()
