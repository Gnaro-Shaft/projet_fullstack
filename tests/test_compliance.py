from pathlib import Path


def test_streamlit_displays_ai_notice_and_legal_disclaimer() -> None:
    frontend = Path("frontend/streamlit_app.py").read_text(encoding="utf-8")

    assert "Assistant utilisant une IA" in frontend
    assert "ne constitue pas un avis juridique personnalisé" in frontend
