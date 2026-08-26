"""
DocMind RAG Chatbot — Main Application Entry Point
Fully local CS Learning Assistant with persistent multi-chats, multi-folder scoping,
interactive notes explorer, and Mermaid PNG/SVG diagram export.
"""

from __future__ import annotations
import streamlit as st

from core.chat_manager import get_latest_or_default_session
from ui.styles import apply_custom_css
from ui.sidebar import render_sidebar
from ui.chat_view import render_chat_view


def init_session_state() -> None:
    """Initializes Streamlit session state variables for active chat and folder scoping."""
    if "current_session_id" not in st.session_state:
        initial_session = get_latest_or_default_session()
        st.session_state.current_session_id = initial_session["id"]

    if "selected_folders" not in st.session_state:
        st.session_state.selected_folders = ["All"]

    if "renaming_chat_id" not in st.session_state:
        st.session_state.renaming_chat_id = None


def main() -> None:
    """Main application layout and controller."""
    # 1. Page Configuration
    st.set_page_config(
        page_title="DocMind RAG - CS Learning Assistant",
        page_icon="🎓",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # 2. Ingest Custom Dark Theme & Styling
    apply_custom_css()

    # 3. Initialize Session State
    init_session_state()

    # 4. Render 4-Tab Sidebar
    render_sidebar()

    # 5. Render Main Chat Interface & Execution Engine
    render_chat_view()


if __name__ == "__main__":
    main()
