import os
from datetime import UTC, datetime

import httpx
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")

st.set_page_config(page_title="Dashboard TrustRAG", page_icon="\U0001f4ca", layout="wide")

if "admin_key" not in st.session_state:
    st.session_state.admin_key = os.getenv("ADMIN_API_KEY", "")

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
    display: inline-block; background: #666; color: #fff;
    padding: 0.2rem 0.6rem; border-radius: 12px; font-size: 0.75rem; font-weight: 600;
}
.badge-warn {
    display: inline-block; background: #fa5c5c; color: #fff;
    padding: 0.2rem 0.6rem; border-radius: 12px; font-size: 0.75rem; font-weight: 600;
}
.badge-neutral {
    display: inline-block; background: #666; color: #fff;
    padding: 0.2rem 0.6rem; border-radius: 12px; font-size: 0.75rem; font-weight: 600;
}
.log-entry {
    padding: 0.4rem 0; border-bottom: 1px solid #eee; font-size: 0.85rem;
}
.log-entry:last-child { border: none; }
.metric-grid { display: flex; gap: 1rem; flex-wrap: wrap; }
</style>
""",
    unsafe_allow_html=True,
)


def fetch_json(path: str, headers: dict | None = None) -> dict | None:
    try:
        r = httpx.get(f"{BACKEND_URL}{path}", timeout=10.0, headers=headers)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def fetch_list(path: str, headers: dict | None = None) -> list:
    try:
        r = httpx.get(f"{BACKEND_URL}{path}", timeout=10.0, headers=headers)
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

    st.sidebar.page_link("streamlit_app.py", label="\U0001f1eb\U0001f1f7 Service Public")

    auth_headers = {"X-Admin-Key": st.session_state.admin_key} if st.session_state.admin_key else None

    metrics = fetch_json("/metrics")
    health = fetch_json("/health")
    audit_entries = fetch_list("/audit/recent?limit=100", headers=auth_headers)

    col1, col2, col3, col4 = st.columns(4)
    sec1_data = [
        ("\u2697\ufe0f Statut", "OK" if health else "HORS LIGNE",
         "ok" if health else "err"),
        ("\U0001f4ac Requêtes", str(metrics.get("chat_requests_total", "—")) if metrics else "—", "ok"),
        ("\U0001f4be Documents", str(metrics.get("collection", {}).get("points_count", "—")) if metrics else "—", "ok"),
        ("\u23f1\ufe0f Uptime", format_uptime(metrics.get("uptime_seconds", 0)) if metrics else "—", "ok"),
    ]
    for col, (icon, val, bt) in zip([col1, col2, col3, col4], sec1_data):
        with col:
            st.markdown(
                f'<div class="card"><h3>{icon}</h3>'
                f'<div class="value">{val}</div>'
                f'<span class="badge-{bt}">{bt.upper()}</span></div>',
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

    if metrics:
        lat = metrics.get("latency", {})
        err = metrics.get("errors", {})
        tok = metrics.get("tokens", {})
        fb = metrics.get("feedback", {})

        st.markdown('<div class="card"><h3>\u26a0\ufe0f Qualité & Performance</h3>', unsafe_allow_html=True)
        qa = st.columns(4)
        vals = [
            ("Taux d'erreur", f'{err.get("rate", 0) * 100:.1f}%', "warn" if err.get("rate", 0) > 0.05 else "ok"),
            ("Latence p50", f'{lat.get("p50_ms", 0):.0f} ms', "ok"),
            ("Latence p95", f'{lat.get("p95_ms", 0):.0f} ms', "ok"),
            ("Latence p99", f'{lat.get("p99_ms", 0):.0f} ms', "ok" if lat.get("p99_ms", 0) < 30000 else "warn"),
        ]
        for col, (label, val, bt) in zip(qa, vals):
            with col:
                st.markdown(
                    f'<div style="font-size:0.8rem;color:#555;">{label}</div>'
                    f'<div style="font-size:1.5rem;font-weight:700;color:#000091;">{val}</div>'
                    f'<span class="badge-{bt}">{bt.upper()}</span>',
                    unsafe_allow_html=True,
                )
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="card"><h3>\U0001f4a0 Consommation & Feedback</h3>', unsafe_allow_html=True)
        qb = st.columns(4)
        fb_rate = f'{fb.get("positive", 0) / max(fb.get("positive", 0) + fb.get("negative", 0), 1) * 100:.0f}%'
        vals2 = [
            ("Tokens totaux", f'{tok.get("total", 0):,}', "ok"),
            ("Tokens input", f'{tok.get("total_input", 0):,}', "ok"),
            ("Tokens output", f'{tok.get("total_output", 0):,}', "ok"),
            ("Feedback positif", fb_rate, "ok"),
        ]
        for col, (label, val, bt) in zip(qb, vals2):
            with col:
                st.markdown(
                    f'<div style="font-size:0.8rem;color:#555;">{label}</div>'
                    f'<div style="font-size:1.5rem;font-weight:700;color:#000091;">{val}</div>'
                    f'<span class="badge-{bt}">{bt.upper()}</span>',
                    unsafe_allow_html=True,
                )
        st.markdown("</div>", unsafe_allow_html=True)

    eval_history = fetch_list("/eval/history")
    if eval_history:
        st.markdown(
            '<div class="card"><h3>\U0001f4ca Évolution qualité RAG</h3>'
            f'<span class="sub">{len(eval_history)} runs d\'évaluation</span>',
            unsafe_allow_html=True,
        )
        ev_df = pd.DataFrame([
            {
                "run": i + 1,
                "run_label": f"#{i+1}" + (f" ({e['commit'][:7]})" if e.get("commit", "unknown") != "unknown" else ""),
                "timestamp": e.get("timestamp", "")[:19],
                "global": e["summary"]["overall_quality"],
                "fidélité": e["summary"]["avg_faithfulness"] / 5,
                "complétude": e["summary"]["avg_completeness"] / 5,
                "anti-hallucination": e["summary"]["avg_hallucination_absence"] / 5,
                "sources": e["summary"]["avg_source_usage"] / 5,
            }
            for i, e in enumerate(eval_history)
        ])
        chart_cols = ["global", "fidélité", "complétude", "anti-hallucination", "sources"]
        st.line_chart(ev_df.set_index("run")[chart_cols], height=180)
        latest = eval_history[-1]["summary"]
        st.markdown(
            f'<span class="sub">Dernier run : {ev_df.iloc[-1]["timestamp"]} &nbsp;|&nbsp; '
            f"Global: {latest['overall_quality']:.0%} &nbsp;|&nbsp; "
            f"Fidélité: {latest['avg_faithfulness']}/5 &nbsp;|&nbsp; "
            f"Complétude: {latest['avg_completeness']}/5 &nbsp;|&nbsp; "
            f"Hallucination: {latest['avg_hallucination_absence']}/5 &nbsp;|&nbsp; "
            f"Sources: {latest['avg_source_usage']}/5</span>",
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

    if audit_entries:
        times = []
        rt_values = []
        token_in_vals = []
        token_out_vals = []
        errors = 0
        source_counts: dict[str, int] = {}
        status_counts: dict[str, int] = {"ok": 0, "error": 0, "no_sources": 0}

        for e in audit_entries:
            ts = e.get("timestamp", "")
            if ts:
                try:
                    times.append(datetime.fromisoformat(ts))
                except ValueError:
                    pass
            rt = e.get("response_time_ms")
            if rt:
                rt_values.append(rt)
            ti = e.get("input_tokens", 0)
            to = e.get("output_tokens", 0)
            if ti:
                token_in_vals.append(ti)
            if to:
                token_out_vals.append(to)
            if e.get("error"):
                errors += 1
                status_counts["error"] += 1
            else:
                src_count = len(e.get("sources", []))
                if src_count > 0:
                    status_counts["ok"] += 1
                else:
                    status_counts["no_sources"] += 1
            for s in e.get("sources", []):
                doc_id = s.get("document_id") or s.get("url", "unknown")
                source_counts[doc_id] = source_counts.get(doc_id, 0) + 1

        col_a, col_b, col_c = st.columns(3)

        with col_a:
            st.markdown('<div class="card"><h3>\U0001f4c8 Temps de réponse</h3>', unsafe_allow_html=True)
            if rt_values:
                rt_df = pd.DataFrame({"ms": rt_values})
                st.line_chart(rt_df, y="ms", height=140)
                sorted_rt = sorted(rt_values)
                st.markdown(
                    f'<span class="sub">Min: {min(rt_values):.0f} &nbsp;|&nbsp; '
                    f"Moy: {sum(rt_values)/len(rt_values):.0f} &nbsp;|&nbsp; "
                    f"Max: {max(rt_values):.0f} &nbsp;|&nbsp; "
                    f"p50: {sorted_rt[len(sorted_rt)//2]:.0f} &nbsp;|&nbsp; "
                    f"p95: {sorted_rt[int(len(sorted_rt)*0.95)]:.0f} &nbsp;|&nbsp; "
                    f"p99: {sorted_rt[int(len(sorted_rt)*0.99)]:.0f}</span>",
                    unsafe_allow_html=True,
                )
            else:
                st.caption("Aucune donnée.")
            st.markdown("</div>", unsafe_allow_html=True)

        with col_b:
            st.markdown('<div class="card"><h3>\U0001f4e4 Volume par heure</h3>', unsafe_allow_html=True)
            if times:
                hour_counts = pd.Series(times).dt.floor("h").value_counts().sort_index()
                st.bar_chart(hour_counts, height=140)
            else:
                st.caption("Aucune donnée temporelle.")
            st.markdown("</div>", unsafe_allow_html=True)

        with col_c:
            st.markdown('<div class="card"><h3>\U0001f504 Distribution des statuts</h3>', unsafe_allow_html=True)
            if sum(status_counts.values()) > 0:
                status_df = pd.DataFrame([
                    {"statut": k, "count": v} for k, v in status_counts.items() if v > 0
                ]).set_index("statut")
                st.bar_chart(status_df, y="count", height=140)
            else:
                st.caption("Aucune donnée.")
            st.markdown("</div>", unsafe_allow_html=True)

        if source_counts:
            st.markdown('<div class="card"><h3>\U0001f4da Top sources consultées</h3>', unsafe_allow_html=True)
            top_sources = sorted(source_counts.items(), key=lambda x: -x[1])[:10]
            src_df = pd.DataFrame(top_sources, columns=["Document", "Requêtes"]).set_index("Document")
            st.bar_chart(src_df, y="Requêtes", height=140)
            st.markdown("</div>", unsafe_allow_html=True)

        col_log, col_tok = st.columns(2)

        with col_log:
            st.markdown(
                f'<div class="card"><h3>\U0001f4cb Derniers échanges</h3>'
                f'<span class="sub">{len(audit_entries)} affichés'
                f'{" · " + str(errors) + " en erreur" if errors else ""}</span>',
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
                t_in = e.get("input_tokens", 0) or ""
                t_out = e.get("output_tokens", 0) or ""
                tok_str = f" \U0001f4a0 {t_in}+{t_out}" if t_in or t_out else ""
                if src_count > 0:
                    badge = '<span class="badge-ok">OK</span>'
                elif err:
                    badge = '<span class="badge-err">ERR</span>'
                else:
                    badge = '<span class="badge-warn">NS</span>'
                st.markdown(
                    f'<div class="log-entry">{badge} <code>{ts}</code> '
                    f"· {src_count} src · {rlen} car. {rt_str}{tok_str}</div>",
                    unsafe_allow_html=True,
                )
            st.markdown("</div>", unsafe_allow_html=True)

        with col_tok:
            st.markdown('<div class="card"><h3>\U0001f4a0 Tokens par requête</h3>', unsafe_allow_html=True)
            if token_in_vals and token_out_vals:
                tok_df = pd.DataFrame({
                    "input": token_in_vals[-50:],
                    "output": token_out_vals[-50:],
                })
                st.area_chart(tok_df, height=160)
                avg_tok_in = sum(token_in_vals) / len(token_in_vals)
                avg_tok_out = sum(token_out_vals) / len(token_out_vals)
                total_tok = sum(token_in_vals) + sum(token_out_vals)
                st.markdown(
                    f'<span class="sub">Moy: {avg_tok_in:.0f} in / {avg_tok_out:.0f} out &nbsp;|&nbsp; '
                    f"Total: {total_tok:,}</span>",
                    unsafe_allow_html=True,
                )
            else:
                st.caption("Aucune donnée token.")
            st.markdown("</div>", unsafe_allow_html=True)

    else:
        st.info("Aucune requête enregistrée. Posez une question sur l'interface principale.")
        if not st.session_state.admin_key:
            st.warning(
                "ADMIN_API_KEY non configurée. Le dashboard affichera les métriques "
                "agrégées mais pas les logs individuels.",
            )


if __name__ == "__main__":
    main()
