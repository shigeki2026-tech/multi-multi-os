def _get_database_url() -> str:
    try:
        import streamlit as st
        url = st.secrets.get("DATABASE_URL")
        if url:
            return str(url)
    except Exception:
        pass
    return os.getenv("DATABASE_URL", "sqlite:///multimulti_os.db")
