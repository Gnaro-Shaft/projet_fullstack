import os
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")

st.set_page_config(page_title="Dashboard TrustRAG", page_icon="\U0001f4ca", layout="wide")

st.markdown(
    """
<style>
.stApp { background: #f8f8fa; }
.block-container { padding: 2rem 1.5rem; }
.card {
    background: #fff; border-radius: 8px; padding: 1.2rem 1.5rem;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06); margin-bottom: 1rem;
}
.card h3 { margin: 0 0 0.5rem; color: #161616; font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.5px; }
.card .value { font-size: 2rem; font-weight: 700; color: #000091; }
.card .sub { font-size: 0.8rem; color: #888; }
.badge-ok {
    display: inline-block; background: #00a83e; color: #fff;
    padding: 0.2rem 0.6rem; border-radius: 12px; font-size: 0.75rem; font-weight: 600;
}
.badge-err {
    display: inline-block; background: #e1000f; color: #fff;
    padding: 0.2rem 0.6rem; border-radius: 12px; font-size: 0.75rem; font-weight: 600;
}
.badge-warn {
    display: inline-block; background: #fa5c5c; color: #fff;
    padding: 0.2rem 0.6rem; border-radius: 12px; font-size: 0.75rem; font-weight: 600;
}
.log-entry {
    padding: 0.4rem 0; border-bottom: 1px solid #eee; font-size: 0.85rem;
}
.log-entry:last-child { border: none; }
</style>
""",
    unsafe_allow_html=True,
)


def fetch_json(path: str) -> dict | None:
    try:
        r = httpx.get(f"{BACKEND_URL}{path}", timeout=10.0)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def fetch_list(path: str) -> list:
    try:
        r = httpx.get(f"{BACKEND_URL}{path}", timeout=10.0)
        r.raise_for_status()
        return r.json()
    except Exception:
        return []


def format_uptime(seconds: float) -> str:
    hours, remainder = divmod(int(seconds), 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours}h {minutes}m"


def main() -> None:
    st.title("TrustRAG")
    st.markdown(
        '<p style="color:#888;margin-top:-0.5rem;font-size:0.95rem;">'
        "Tableau de bord de l'assistant aux démarches administratives</p>",
        unsafe_allow_html=True,
    )

    metrics = fetch_json("/metrics")
    health = fetch_json("/health")
    audit_entries = fetch_list("/audit/recent?limit=50")

    row1 = st.columns(4)
    metrics_data = [
        ("\u2697\ufe0f Statut", "OK" if health else "HORS LIGNE",
         "ok" if health else "err"),
        ("\U0001f4ac Requêtes", str(metrics.get("chat_requests_total", "—")) if metrics else "—",
         "ok"),
        ("\U0001f4be Documents", str(metrics.get("collection", {}).get("points_count", "—")) if metrics else "—",
         "ok"),
        ("\u23f1\ufe0f Uptime", format_uptime(metrics.get("uptime_seconds", 0)) if metrics else "—",
         "ok"),
    ]
    for col, (icon, val, badge_type) in zip(row1, metrics_data):
        with col:
            st.markdown(
                f'<div class="card"><h3>{icon} {val.split()[0] if " " in val else ""}</h3>'
                f'<div class="value">{val}</div>'
                f'<span class="badge-{badge_type}">{badge_type.upper()}</span></div>',
                unsafe_allow_html=True,
            )

    if health:
        st.markdown('<div class="card"><h3>\U0001f3af Services</h3>', unsafe_allow_html=True)
        svc_cols = st.columns(len(health))
        for col, (service, status) in zip(svc_cols, health.items()):
            with col:
                ok = status == "ok"
                st.markdown(
                    f'<span style="font-size:0.85rem;">{service}</span><br>'
                    f'<span class="badge-{"ok" if ok else "err"}">'
                    f'{"OK" if ok else status}</span>',
                    unsafe_allow_html=True,
                )
        st.markdown("</div>", unsafe_allow_html=True)

    if audit_entries:
        times = []
        lengths = []
        errors = 0
        for e in audit_entries:
            ts = e.get("timestamp", "")
            if ts:
                try:
                    times.append(datetime.fromisoformat(ts))
                except ValueError:
                    pass
            rl = e.get("response_length", 0)
            if isinstance(rl, (int, float)):
                lengths.append(rl)
            if e.get("error"):
                errors += 1

        col_a, col_b = st.columns(2)

        with col_a:
            st.markdown('<div class="card"><h3>\U0001f4c8 Temps de réponse</h3>', unsafe_allow_html=True)
            rt_values = [e.get("response_time_ms", 0) for e in audit_entries if e.get("response_time_ms")]
            if rt_values:
                rt_df = pd.DataFrame({"ms": rt_values})
                st.line_chart(rt_df, y="ms", height=160)
                avg_rt = sum(rt_values) / len(rt_values)
                st.markdown(
                    f'<span class="sub">Moyenne: {avg_rt:.0f} ms &nbsp;|&nbsp; '
                    f"Min: {min(rt_values):.0f} ms &nbsp;|&nbsp; "
                    f"Max: {max(rt_values):.0f} ms</span>",
                    unsafe_allow_html=True,
                )
            else:
                st.caption("Aucune donnée de temps de réponse.")
            st.markdown("</div>", unsafe_allow_html=True)

        with col_b:
            st.markdown('<div class="card"><h3>\U0001f4ac Volume par heure</h3>', unsafe_allow_html=True)
            if times:
                hour_counts = pd.Series(times).dt.floor("h").value_counts().sort_index()
                st.bar_chart(hour_counts, height=160)
            else:
                st.caption("Aucune donnée temporelle.")
            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown(
            f'<div class="card"><h3>\U0001f4cb Dernières échanges</h3>'
            f'<span class="sub">{len(audit_entries)} affichés '
            f'({"dont " + str(errors) + " en erreur" if errors else ""})</span>',
            unsafe_allow_html=True,
        )
        for e in audit_entries[:20]:
            ts = e.get("timestamp", "")
            if ts:
                try:
                    ts = datetime.fromisoformat(ts).strftime("%d/%m %H:%M")
                except ValueError:
                    ts = ts[:16]
            q_hash = e.get("question_sha256", "")[:10]
            src_count = len(e.get("sources", []))
            rlen = e.get("response_length", 0)
            rt = e.get("response_time_ms")
            rt_str = f"{rt:.0f} ms" if rt else ""
            err = e.get("error")
            err_str = f'<span class="badge-err">ERR</span>' if err else ""
            status_badge = ""
            if src_count > 0:
                status_badge = '<span class="badge-ok">OK</span>'
            elif err:
                status_badge = f'<span class="badge-err">ERR</span>'
            st.markdown(
                f'<div class="log-entry">{status_badge} <code>{ts}</code> '
                f"· {src_count} sources · {rlen} car. {rt_str} {err_str}</div>",
                unsafe_allow_html=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
