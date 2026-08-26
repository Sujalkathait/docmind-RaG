"""
DocMind RAG — UI Styling Module
Custom dark theme, typography, cards, badges, and button styling.
"""

from __future__ import annotations
import streamlit as st


def apply_custom_css() -> None:
    """Injects premium custom CSS styles into the Streamlit application."""
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

        /* Global Typography & Background */
        .stApp {
            font-family: 'Plus Jakarta Sans', sans-serif;
            background-color: #090d16;
            color: #f1f5f9;
        }

        /* Hide default Streamlit clutter */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}

        /* Sidebar Styling */
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #0b0f19 0%, #111827 50%, #0b0f19 100%);
            border-right: 1px solid rgba(99, 102, 241, 0.2);
        }

        [data-testid="stSidebar"] .stMarkdown h1,
        [data-testid="stSidebar"] .stMarkdown h2,
        [data-testid="stSidebar"] .stMarkdown h3 {
            color: #a5b4fc;
            font-weight: 700;
        }

        /* Status Cards */
        .status-card {
            background: linear-gradient(135deg, rgba(99, 102, 241, 0.12), rgba(139, 92, 246, 0.08));
            border: 1px solid rgba(99, 102, 241, 0.3);
            border-radius: 12px;
            padding: 12px 16px;
            margin: 6px 0;
        }

        .status-online {
            color: #34d399;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .status-offline {
            color: #f87171;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 6px;
        }

        /* Chat Session List Cards */
        .chat-item {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 8px 12px;
            margin-bottom: 6px;
            border-radius: 8px;
            background: rgba(30, 41, 59, 0.5);
            border: 1px solid rgba(99, 102, 241, 0.15);
            transition: all 0.2s ease;
        }
        .chat-item:hover {
            background: rgba(99, 102, 241, 0.18);
            border-color: rgba(99, 102, 241, 0.4);
        }
        .chat-item-active {
            background: linear-gradient(135deg, rgba(99, 102, 241, 0.25), rgba(139, 92, 246, 0.25)) !important;
            border-color: #818cf8 !important;
        }

        /* Document & Folder Cards */
        .folder-card {
            background: rgba(15, 23, 42, 0.7);
            border: 1px solid rgba(99, 102, 241, 0.2);
            border-radius: 10px;
            padding: 10px 14px;
            margin-bottom: 8px;
        }
        .doc-pill {
            display: flex;
            align-items: center;
            justify-content: space-between;
            background: rgba(30, 41, 59, 0.6);
            border: 1px solid rgba(148, 163, 184, 0.15);
            border-radius: 8px;
            padding: 6px 10px;
            margin: 4px 0;
            font-size: 0.85rem;
        }

        /* Source Badges */
        .source-badge {
            display: inline-block;
            background: rgba(99, 102, 241, 0.15);
            border: 1px solid rgba(99, 102, 241, 0.35);
            border-radius: 8px;
            padding: 4px 10px;
            margin: 2px 4px 4px 0;
            font-size: 0.8em;
            color: #c7d2fe;
            font-weight: 500;
        }

        /* Timing Badge */
        .timing-badge {
            display: inline-block;
            background: rgba(52, 211, 153, 0.15);
            border: 1px solid rgba(52, 211, 153, 0.35);
            border-radius: 8px;
            padding: 4px 10px;
            font-size: 0.8em;
            color: #6ee7b7;
            font-weight: 500;
        }

        /* Scope Badge */
        .scope-badge {
            display: inline-block;
            background: rgba(245, 158, 11, 0.15);
            border: 1px solid rgba(245, 158, 11, 0.35);
            border-radius: 8px;
            padding: 4px 10px;
            font-size: 0.8em;
            color: #fcd34d;
            font-weight: 500;
        }

        /* Time Badge */
        .time-badge {
            display: inline-block;
            background: rgba(148, 163, 184, 0.12);
            border: 1px solid rgba(148, 163, 184, 0.25);
            border-radius: 8px;
            padding: 4px 10px;
            font-size: 0.8em;
            color: #94a3b8;
            font-weight: 500;
        }

        /* Enhanced Markdown Tables */
        table {
            width: 100%;
            border-collapse: separate;
            border-spacing: 0;
            margin: 1.2rem 0;
            border-radius: 10px;
            overflow: hidden;
            border: 1px solid rgba(99, 102, 241, 0.25);
        }
        thead th {
            background: linear-gradient(135deg, rgba(99, 102, 241, 0.4), rgba(139, 92, 246, 0.35));
            color: #e0e7ff !important;
            font-weight: 600;
            padding: 10px 16px;
            border-bottom: 2px solid rgba(99, 102, 241, 0.4);
            text-align: left;
        }
        tbody td {
            padding: 10px 16px;
            border-bottom: 1px solid rgba(99, 102, 241, 0.12);
            background: rgba(15, 23, 42, 0.6);
            color: #f1f5f9;
        }
        tbody tr:last-child td {
            border-bottom: none;
        }
        tbody tr:nth-child(even) td {
            background: rgba(30, 41, 59, 0.5);
        }
        tbody tr:hover td {
            background: rgba(99, 102, 241, 0.18);
        }

        /* Streamlit Chat Messages */
        [data-testid="stChatMessage"] {
            border-radius: 14px;
            border: 1px solid rgba(99, 102, 241, 0.15);
            margin-bottom: 10px;
            background: rgba(15, 23, 42, 0.45);
        }
        [data-testid="stChatMessage"] h1 {
            font-size: 1.3rem !important;
            font-weight: 700 !important;
            color: #e0e7ff !important;
            margin: 0.6rem 0 0.4rem 0 !important;
            line-height: 1.4 !important;
        }
        [data-testid="stChatMessage"] h2 {
            font-size: 1.15rem !important;
            font-weight: 600 !important;
            color: #c7d2fe !important;
            margin: 0.5rem 0 0.3rem 0 !important;
            line-height: 1.35 !important;
        }
        [data-testid="stChatMessage"] h3 {
            font-size: 1.05rem !important;
            font-weight: 600 !important;
            color: #a5b4fc !important;
            margin: 0.4rem 0 0.25rem 0 !important;
        }
        [data-testid="stChatMessage"] h4, [data-testid="stChatMessage"] h5, [data-testid="stChatMessage"] h6 {
            font-size: 0.95rem !important;
            font-weight: 600 !important;
            color: #cbd5e1 !important;
            margin: 0.3rem 0 0.2rem 0 !important;
        }
        [data-testid="stChatMessage"] p, [data-testid="stChatMessage"] li {
            font-size: 0.95rem !important;
            line-height: 1.6 !important;
            color: #f1f5f9 !important;
        }

        /* Buttons */
        button[kind="primary"],
        button[data-testid="baseButton-primary"] {
            background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%) !important;
            border: 1px solid #818cf8 !important;
            color: #ffffff !important;
            font-weight: 600 !important;
            border-radius: 9px !important;
            box-shadow: 0 2px 8px rgba(99, 102, 241, 0.35) !important;
            transition: all 0.2s ease !important;
        }
        button[kind="primary"]:hover,
        button[data-testid="baseButton-primary"]:hover {
            background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%) !important;
            border-color: #a5b4fc !important;
            box-shadow: 0 4px 14px rgba(99, 102, 241, 0.5) !important;
            transform: translateY(-1px) !important;
        }
        button[kind="secondary"],
        button[data-testid="baseButton-secondary"] {
            background: rgba(30, 41, 59, 0.6) !important;
            border: 1px solid rgba(99, 102, 241, 0.2) !important;
            color: #e2e8f0 !important;
            border-radius: 9px !important;
            transition: all 0.2s ease !important;
        }
        button[kind="secondary"]:hover,
        button[data-testid="baseButton-secondary"]:hover {
            background: rgba(99, 102, 241, 0.22) !important;
            border-color: rgba(99, 102, 241, 0.45) !important;
            color: #ffffff !important;
            transform: translateY(-1px) !important;
        }
    </style>
    """, unsafe_allow_html=True)
