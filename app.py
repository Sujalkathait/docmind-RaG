"""
DocMind RAG Chatbot — Streamlit Interface
Fully local CS Learning Assistant with persistent multi-chats, multi-folder scoping,
interactive notes explorer, and Mermaid PNG/SVG diagram export.
"""

from __future__ import annotations

import os
import re
import time
import html
import base64
import importlib
from datetime import datetime
import streamlit as st
import streamlit.components.v1 as components

import config
import core.llm
import core.chat_manager
import core.vector_store
import core.embedder
import core.pdf_loader
import core.chunker

from config import PDF_FOLDER, CHUNK_SIZE, CHUNK_OVERLAP, TOP_K
from core.pdf_loader import load_pdf_from_bytes
from core.chunker import create_chunks
from core.embedder import embed_documents, embed_query
from core.vector_store import (
    add_document,
    query as vector_query,
    get_all_folders,
    get_folder_documents,
    create_folder,
    delete_folder,
    delete_document,
    clear_all,
    get_document_count,
    sanitize_folder_name,
)
from core.llm import (
    generate,
    is_model_loaded,
    get_model_info,
    get_available_models,
    set_active_model,
)
from download_model import AVAILABLE_MODELS, download_model_file
from core.chat_manager import (
    get_all_sessions,
    get_session,
    create_session,
    add_message,
    rename_session,
    toggle_pin_session,
    delete_session,
    clear_all_sessions,
    get_latest_or_default_session,
)


# ===========================
# Page Configuration
# ===========================

st.set_page_config(
    page_title="DocMind RAG - CS Learning Assistant",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ===========================
# Premium CSS Styling
# ===========================

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

    /* Badges */

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


# ===========================
# Session State Initialization
# ===========================

if "current_session_id" not in st.session_state:
    initial_session = get_latest_or_default_session()
    st.session_state.current_session_id = initial_session["id"]

if "selected_folders" not in st.session_state:
    st.session_state.selected_folders = ["All"]

if "renaming_chat_id" not in st.session_state:
    st.session_state.renaming_chat_id = None


# ===========================
# Diagram Sanitizer & Renderer with PNG/SVG Export
# ===========================


def _clean_node_label(raw: str) -> str:
    """Cleans the inner text of a Mermaid node label to avoid syntax errors."""
    txt = raw.strip()
    # Strip any leading and trailing quotes
    while (txt.startswith('"') and txt.endswith('"')) or (
        txt.startswith("'") and txt.endswith("'")
    ):
        if len(txt) <= 1:
            break
        txt = txt[1:-1].strip()

    # Replace inner double quotes with single quotes or remove
    txt = txt.replace('"', "'")
    # Replace inner square brackets with parentheses to prevent nested bracket syntax errors
    txt = txt.replace("[", "(").replace("]", ")")
    # Clean redundant quotation comma patterns like ', ' -> ', '
    txt = re.sub(r"'\s*,\s*'", ", ", txt)
    # Replace backslashes
    txt = txt.replace("\\", "/")
    return txt.strip()


def sanitize_mermaid_code(code: str) -> str:
    """
    Cleans, repairs, and sanitizes LLM-generated Mermaid diagrams,
    including nested quotes, bracket conflicts, truncated lines, and sequence errors.
    """
    code = code.strip()
    code = re.sub(r"^```(?:mermaid)?", "", code, flags=re.IGNORECASE).strip()
    code = re.sub(r"```$", "", code).strip()

    code = code.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")

    raw_lines = [l.rstrip() for l in code.splitlines() if l.strip()]
    if not raw_lines:
        return 'flowchart TD\n    A["Processing Complete"]'

    # Check or prepend header
    valid_headers = (
        "graph ", "graph\n", "flowchart ", "flowchart\n",
        "sequencediagram", "statediagram", "statediagram-v2",
        "classdiagram", "erdiagram", "gantt", "pie", "gitgraph",
        "mindmap", "timeline", "journey", "c4"
    )
    first_line = raw_lines[0].strip().lower()
    has_header = any(first_line.startswith(h) for h in valid_headers)
    if not has_header:
        raw_lines.insert(0, "flowchart TD")

    is_sequence = "sequencediagram" in raw_lines[0].lower()
    clean_lines = []

    arrow_split_regex = r"(\s*(?:-->|---|==>|-\.->|--\s*\|.*?\|\s*-->|-->\|.*?\|)\s*)"

    for idx, line in enumerate(raw_lines):
        sline = line.strip()
        if not sline:
            continue

        if idx == 0:
            clean_lines.append(sline)
            continue

        if sline.startswith("%%"):
            clean_lines.append(sline)
            continue

        if is_sequence:
            # Fix truncated sequence lines ending with arrows: US->> or A-> or B-->
            if re.search(r"(?:->>|-->>|->|-->)\s*$", sline):
                m = re.match(r"^([A-Za-z0-9_]+)\s*(?:->>|-->>|->|-->)\s*$", sline)
                if m:
                    actor = m.group(1)
                    sline = f"    {actor}->>Kernel: Service Request"
                else:
                    continue

            # If sequence line has arrow with target but missing colon: "A->>B"
            elif re.search(
                r"^[A-Za-z0-9_]+\s*(?:->>|-->>|->|-->)\s*[A-Za-z0-9_]+\s*$", sline
            ):
                sline = sline + ": Process"

            if not sline.startswith("    "):
                sline = "    " + sline

        else:
            # Flowcharts & graph diagrams
            # Drop open trailing arrows e.g. A -->
            if re.search(r"(?:-->|---|==>|-\.->)\s*$", sline):
                sline = re.sub(r"(?:-->|---|==>|-\.->)\s*$", "", sline).strip()
                if not sline:
                    continue

            # Split line into node definitions and arrow connectors
            parts = re.split(arrow_split_regex, sline)
            new_parts = []
            for part in parts:
                if not part:
                    continue
                # If it's an arrow connector, keep it
                if re.match(
                    r"^(?:-->|---|==>|-\.->|--\s*\|.*?\|\s*-->|-->\|.*?\|)$",
                    part.strip(),
                ):
                    new_parts.append(part)
                else:
                    # Match node definition e.g. NodeId[Label] or NodeId(Label) or NodeId{Label}
                    node_match = re.match(
                        r"^\s*([A-Za-z0-9_]+)\s*([\[\(\{])(.*)([\]\)\}])\s*$", part
                    )
                    if node_match:
                        node_id = node_match.group(1)
                        open_bracket = node_match.group(2)
                        raw_label = node_match.group(3)
                        close_bracket = node_match.group(4)

                        clean_label = _clean_node_label(raw_label)

                        if open_bracket == "{" or close_bracket == "}":
                            new_parts.append(f'{node_id}{{"{clean_label}"}}')
                        elif open_bracket == "(" or close_bracket == ")":
                            new_parts.append(f'{node_id}("{clean_label}")')
                        else:
                            new_parts.append(f'{node_id}["{clean_label}"]')
                    else:
                        bare_match = re.match(r"^\s*([A-Za-z0-9_]+)\s*$", part)
                        if bare_match:
                            new_parts.append(bare_match.group(1))
                        else:
                            cleaned_part = _clean_node_label(part)
                            new_parts.append(f'N_{idx}["{cleaned_part}"]' if cleaned_part else part)

            sline = " ".join(new_parts) if new_parts else sline

        clean_lines.append(sline)

    if len(clean_lines) <= 1:
        clean_lines.append('    A["Concept Overview"]')

    return "\n".join(clean_lines).strip()


def render_mermaid(code: str):
    """
    Renders interactive Mermaid diagram with built-in:
    1. 💾 Save as PNG (High-Res Canvas Export)
    2. 📥 Save as SVG (Vector Download)
    3. 📋 Copy Mermaid Code
    """
    cleaned_code = sanitize_mermaid_code(code)
    escaped_code = (
        cleaned_code.replace("\\", "\\\\")
        .replace("`", "\\`")
        .replace("$", "\\$")
    )

    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <script type="module">
            import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
            mermaid.initialize({{
                startOnLoad: false,
                theme: 'dark',
                securityLevel: 'loose',
                suppressErrorRendering: true,
                themeVariables: {{
                    darkMode: true,
                    background: '#0b0f19',
                    primaryColor: '#6366f1',
                    primaryTextColor: '#f8fafc',
                    primaryBorderColor: '#818cf8',
                    lineColor: '#a5b4fc',
                    secondaryColor: '#1e1b4b',
                    tertiaryColor: '#1e293b'
                }}
            }});

            async function drawDiagram() {{
                const container = document.getElementById('diagram-container');
                const rawCode = `{escaped_code}`;
                try {{
                    const id = 'mermaid-svg-' + Math.random().toString(36).substring(2, 9);
                    const {{ svg }} = await mermaid.render(id, rawCode);
                    // Remove any injected mermaid error containers
                    document.querySelectorAll('[id^="dmermaid"]').forEach(el => el.remove());
                    container.innerHTML = svg;
                }} catch (err) {{
                    console.warn('Mermaid rendering fallback:', err);
                    // Remove mermaid error bomb element injected into document
                    document.querySelectorAll('[id^="dmermaid"], svg[aria-roledescription="error"]').forEach(el => el.remove());

                    container.innerHTML = `
                        <div style="background: rgba(30, 41, 59, 0.7); border: 1px solid rgba(99, 102, 241, 0.3); border-radius: 8px; padding: 12px; font-family: monospace; font-size: 12px; color: #cbd5e1; white-space: pre-wrap; overflow-x: auto; width: 100%;">
                            <div style="color: #a5b4fc; font-size: 11px; margin-bottom: 6px; font-weight: 600;">📊 Process Flow</div>
                            <pre style="margin: 0; color: #94a3b8; font-size: 11px;">${{rawCode.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")}}</pre>
                        </div>
                    `;
                }}
            }}
            drawDiagram();

            window.exportPNG = function() {{
                const container = document.getElementById('diagram-container');
                const svg = container.querySelector('svg');
                if (!svg) return;

                const svgData = new XMLSerializer().serializeToString(svg);
                const svgBlob = new Blob([svgData], {{ type: 'image/svg+xml;charset=utf-8' }});
                const URL = window.URL || window.webkitURL || window;
                const blobURL = URL.createObjectURL(svgBlob);

                const image = new Image();
                image.onload = () => {{
                    const scale = 2; // High-DPI 2x scale
                    const canvas = document.createElement('canvas');
                    canvas.width = (svg.clientWidth || 800) * scale;
                    canvas.height = (svg.clientHeight || 500) * scale;
                    const ctx = canvas.getContext('2d');
                    ctx.fillStyle = '#0b0f19';
                    ctx.fillRect(0, 0, canvas.width, canvas.height);
                    ctx.drawImage(image, 0, 0, canvas.width, canvas.height);

                    const pngUrl = canvas.toDataURL('image/png');
                    const downloadLink = document.createElement('a');
                    downloadLink.download = 'docmind-diagram-' + Date.now() + '.png';
                    downloadLink.href = pngUrl;
                    document.body.appendChild(downloadLink);
                    downloadLink.click();
                    document.body.removeChild(downloadLink);
                    URL.revokeObjectURL(blobURL);
                }};
                image.src = blobURL;
            }};

            window.exportSVG = function() {{
                const container = document.getElementById('diagram-container');
                const svg = container.querySelector('svg');
                if (!svg) return;

                const svgData = new XMLSerializer().serializeToString(svg);
                const svgBlob = new Blob([svgData], {{ type: 'image/svg+xml;charset=utf-8' }});
                const downloadLink = document.createElement('a');
                downloadLink.download = 'docmind-diagram-' + Date.now() + '.svg';
                downloadLink.href = URL.createObjectURL(svgBlob);
                document.body.appendChild(downloadLink);
                downloadLink.click();
                document.body.removeChild(downloadLink);
            }};

            window.copyDiagramCode = function() {{
                const rawCode = `{escaped_code}`;
                navigator.clipboard.writeText(rawCode).then(() => {{
                    const btn = document.getElementById('copy-btn');
                    btn.innerText = '✅ Copied!';
                    setTimeout(() => {{ btn.innerText = '📋 Copy Code'; }}, 2000);
                }});
            }};
        </script>
        <style>
            body {{
                background-color: #0b0f19;
                margin: 0;
                padding: 12px;
                display: flex;
                flex-direction: column;
                justify-content: center;
                align-items: center;
                border-radius: 12px;
                border: 1px solid rgba(99, 102, 241, 0.3);
                font-family: system-ui, -apple-system, sans-serif;
            }}
            .toolbar {{
                width: 100%;
                display: flex;
                justify-content: flex-end;
                gap: 8px;
                margin-bottom: 8px;
                padding-bottom: 6px;
                border-bottom: 1px solid rgba(99, 102, 241, 0.15);
            }}
            .tool-btn {{
                background: rgba(30, 41, 59, 0.8);
                color: #c7d2fe;
                border: 1px solid rgba(99, 102, 241, 0.3);
                border-radius: 6px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.2s ease;
            }}
            .tool-btn:hover {{
                background: rgba(99, 102, 241, 0.4);
                color: #ffffff;
                border-color: #818cf8;
            }}
            #diagram-container {{
                width: 100%;
                display: flex;
                justify-content: center;
                overflow-x: auto;
            }}
            #diagram-container svg {{
                max-width: 100%;
                height: auto;
            }}
        </style>
    </head>
    <body>
        <div class="toolbar">
            <button class="tool-btn" onclick="window.exportPNG()">💾 Save PNG</button>
            <button class="tool-btn" onclick="window.exportSVG()">📥 Save SVG</button>
            <button class="tool-btn" id="copy-btn" onclick="window.copyDiagramCode()">📋 Copy Code</button>
        </div>
        <div id="diagram-container">
            <span style="color: #94a3b8; font-size: 12px;">Rendering diagram...</span>
        </div>
    </body>
    </html>
    """
    line_count = len(cleaned_code.splitlines())
    calc_height = max(220, min(line_count * 45 + 110, 650))
    components.html(html_code, height=calc_height, scrolling=True)


def render_message_content(content: str):
    """
    Renders message content, automatically parsing and displaying
    Markdown text, structured tables, and visual Mermaid.js diagrams.
    """
    if not content:
        return

    if content.count("```mermaid") > content.count("```") // 2:
        content = content.rstrip() + "\n```"

    mermaid_pattern = r'```mermaid\s*([\s\S]*?)\s*```'
    parts = re.split(mermaid_pattern, content)

    if len(parts) == 1:
        st.markdown(content)
        return

    for i, part in enumerate(parts):
        if not part.strip():
            continue
        if i % 2 == 1:
            try:
                render_mermaid(part.strip())
            except Exception:
                st.code(part.strip(), language="mermaid")
        else:
            st.markdown(part)


def render_assistant_actions(content: str, msg_id: str, feedback: str | None = None):
    """
    Renders a sleek, modern, zero-reload action toolbar with:
    1. 📋 Copy Answer Text (direct to clipboard)
    2. 👍 Like Feedback
    3. 👎 Dislike Feedback
    (No audio, no download).
    """
    clean_id = "".join(c for c in str(msg_id) if c.isalnum() or c in ("_", "-"))
    b64_content = base64.b64encode(content.encode("utf-8")).decode("ascii")

    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{
                background: transparent;
                margin: 0;
                padding: 4px 0 0 0;
                display: flex;
                align-items: center;
                gap: 8px;
                font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            }}
            .action-btn {{
                background: rgba(30, 41, 59, 0.55);
                color: #94a3b8;
                border: 1px solid rgba(148, 163, 184, 0.2);
                border-radius: 7px;
                padding: 4px 10px;
                font-size: 12px;
                font-weight: 500;
                cursor: pointer;
                display: flex;
                align-items: center;
                gap: 5px;
                transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
            }}
            .action-btn:hover {{
                background: rgba(99, 102, 241, 0.25);
                color: #f1f5f9;
                border-color: rgba(99, 102, 241, 0.5);
                transform: translateY(-1px);
            }}
            .action-btn.active-like {{
                background: rgba(52, 211, 153, 0.2) !important;
                color: #34d399 !important;
                border-color: #34d399 !important;
            }}
            .action-btn.active-dislike {{
                background: rgba(248, 113, 113, 0.2) !important;
                color: #f87171 !important;
                border-color: #f87171 !important;
            }}
        </style>
    </head>
    <body>
        <button class="action-btn" id="copy-btn-{clean_id}" onclick="handleCopy()">
            <span id="copy-icon-{clean_id}">📋</span>
            <span id="copy-text-{clean_id}">Copy</span>
        </button>
        <button class="action-btn {'active-like' if feedback == 'liked' else ''}" id="like-btn-{clean_id}" onclick="handleFeedback('liked')">
            <span>👍</span>
        </button>
        <button class="action-btn {'active-dislike' if feedback == 'disliked' else ''}" id="dislike-btn-{clean_id}" onclick="handleFeedback('disliked')">
            <span>👎</span>
        </button>

        <script>
            function decodeUnicodeB64(str) {{
                return decodeURIComponent(atob(str).split('').map(function(c) {{
                    return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
                }}).join(''));
            }}

            function handleCopy() {{
                try {{
                    const rawText = decodeUnicodeB64("{b64_content}");
                    navigator.clipboard.writeText(rawText).then(() => {{
                        const btn = document.getElementById('copy-btn-{clean_id}');
                        const icon = document.getElementById('copy-icon-{clean_id}');
                        const text = document.getElementById('copy-text-{clean_id}');
                        if (icon && text) {{
                            icon.innerText = '✅';
                            text.innerText = 'Copied!';
                            btn.style.borderColor = '#34d399';
                            btn.style.color = '#34d399';
                            setTimeout(() => {{
                                icon.innerText = '📋';
                                text.innerText = 'Copy';
                                btn.style.borderColor = '';
                                btn.style.color = '';
                            }}, 2000);
                        }}
                    }}).catch(err => {{
                        console.error('Failed to copy text: ', err);
                    }});
                }} catch(e) {{
                    console.error('Copy decode error: ', e);
                }}
            }}

            function handleFeedback(type) {{
                const likeBtn = document.getElementById('like-btn-{clean_id}');
                const dislikeBtn = document.getElementById('dislike-btn-{clean_id}');
                if (type === 'liked') {{
                    if (likeBtn.classList.contains('active-like')) {{
                        likeBtn.classList.remove('active-like');
                    }} else {{
                        likeBtn.classList.add('active-like');
                        dislikeBtn.classList.remove('active-dislike');
                    }}
                }} else if (type === 'disliked') {{
                    if (dislikeBtn.classList.contains('active-dislike')) {{
                        dislikeBtn.classList.remove('active-dislike');
                        likeBtn.classList.add('active-like');
                    }} else {{
                        dislikeBtn.classList.add('active-dislike');
                        likeBtn.classList.remove('active-like');
                    }}
                }}
            }}
        </script>
    </body>
    </html>
    """
    components.html(html_code, height=36)


# ===========================
# Upload Processing Function
# ===========================


def _process_uploads(files, folder):
    """Process uploaded PDF files: extract → chunk → embed → store."""
    progress = st.sidebar.progress(0, text="Starting ingestion...")
    total = len(files)
    success_count = 0

    for i, uploaded_file in enumerate(files):
        filename = uploaded_file.name
        progress.progress((i / total) * 0.1, text=f"Reading {filename}...")

        try:
            pdf_bytes = uploaded_file.read()

            # Save to disk
            clean_folder = sanitize_folder_name(folder)
            folder_path = os.path.join(PDF_FOLDER, clean_folder)
            os.makedirs(folder_path, exist_ok=True)
            save_path = os.path.join(folder_path, filename)
            with open(save_path, "wb") as f:
                f.write(pdf_bytes)

            # Extract text
            progress.progress((i / total) * 0.3, text=f"Extracting text from {filename}...")
            text = load_pdf_from_bytes(pdf_bytes)

            if not text.strip():
                st.sidebar.warning(f"⚠️ No text extracted from '{filename}', skipping.")
                continue

            # Chunk
            progress.progress((i / total) * 0.5, text=f"Chunking {filename}...")
            chunks = create_chunks(text, CHUNK_SIZE, CHUNK_OVERLAP)

            if not chunks:
                st.sidebar.warning(f"⚠️ No chunks created from '{filename}', skipping.")
                continue

            # Embed
            progress.progress(
                (i / total) * 0.7,
                text=f"Embedding {filename} ({len(chunks)} chunks)...",
            )
            embeddings = embed_documents(chunks)

            # Store
            progress.progress((i / total) * 0.9, text=f"Storing {filename} in ChromaDB...")
            add_document(chunks, embeddings, filename, folder=clean_folder)

            success_count += 1

        except Exception as e:
            st.sidebar.error(f"❌ Error processing '{filename}': {e}")

    progress.progress(1.0, text="Indexing complete!")
    time.sleep(0.4)
    progress.empty()

    if success_count > 0:
        st.sidebar.success(f"✅ Indexed {success_count}/{total} PDF(s) into folder '{folder}'")
        st.rerun()


# ===========================
# SIDEBAR
# ===========================

with st.sidebar:
    st.markdown("## 🎓 DocMind RAG")
    st.markdown("*CS Learning Assistant & Local PDF Intelligence*")
    st.divider()

    # --- Top Quick Action: New Chat ---
    if st.button("➕ New Chat Session", type="primary", use_container_width=True):
        new_sess = create_session(folder_scope=st.session_state.selected_folders)
        st.session_state.current_session_id = new_sess["id"]
        st.rerun()

    # --- Operational Status Card ---
    model_info = get_model_info()
    if model_info.get("is_ready", False):
        model_name = model_info.get("model_name", "Unknown")
        avail_count = len(model_info.get("available_models", []))
        extra_info = f" • {avail_count} models installed" if avail_count > 1 else ""
        st.markdown(
            f'<div class="status-card">'
            f'<div class="status-online">● LLM Active ({model_name})</div>'
            f'<small style="color:#94a3b8;">GPU Layers: {model_info["n_gpu_layers"]} | Context: {model_info["n_ctx"]} tokens{extra_info}</small>'
            f'</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f'<div class="status-card" style="border-color: rgba(239, 68, 68, 0.4);">'
            f'<div class="status-online" style="color:#f87171;">⚠️ LLM Model Not Found</div>'
            f'<small style="color:#94a3b8;">Download <b>SmolLM2-360M (~258MB)</b> or <b>Qwen2.5-3B (~2GB)</b> via the ⚙️ Manage tab or terminal.</small>'
            f'</div>',
            unsafe_allow_html=True,
        )

    st.divider()

    # --- Sidebar Navigation Tabs ---
    tab_chats, tab_folders, tab_upload, tab_settings = st.tabs([
        "💬 Chats",
        "📁 Notes & Folders",
        "📤 Upload",
        "⚙️ Manage",
    ])

    # ------------------------------------
    # TAB 1: PERSISTENT CHAT SESSIONS
    # ------------------------------------
    with tab_chats:
        st.markdown("#### 🗂️ Chat Conversations")
        sessions = get_all_sessions()

        if not sessions:
            st.info("No saved chats yet. Start asking questions!")
        else:
            for sess in sessions:
                s_id = sess["id"]
                s_title = sess.get("title", "Untitled Chat")
                is_active = s_id == st.session_state.current_session_id
                is_pinned = sess.get("is_pinned", False)
                msg_count = len(sess.get("messages", []))
                pin_icon = "📌 " if is_pinned else ""

                card_class = "chat-item chat-item-active" if is_active else "chat-item"

                col_btn, col_actions = st.columns([0.72, 0.28])
                with col_btn:
                    clean_s_title = re.sub(r"[`*#_]", "", s_title).strip()
                    if not clean_s_title:
                        clean_s_title = "Chat Session"
                    btn_label = f"{pin_icon}{clean_s_title[:22]} ({msg_count})"
                    if st.button(
                        btn_label,
                        key=f"sel_chat_{s_id}",
                        use_container_width=True,
                        type="secondary" if not is_active else "primary",
                    ):
                        st.session_state.current_session_id = s_id
                        st.rerun()

                with col_actions:
                    pop = st.popover("⚙️", use_container_width=True)
                    with pop:
                        st.markdown(f"**Chat Settings**")
                        # Pin / Unpin
                        pin_txt = "Unpin Chat" if is_pinned else "Pin to Top"
                        if st.button(pin_txt, key=f"pin_{s_id}"):
                            toggle_pin_session(s_id)
                            st.rerun()

                        # Rename
                        new_name = st.text_input(
                            "Rename Chat:",
                            value=s_title,
                            key=f"rename_input_{s_id}",
                        )
                        if st.button("Save Name", key=f"save_rename_{s_id}"):
                            if new_name.strip():
                                rename_session(s_id, new_name.strip())
                                st.rerun()

                        st.divider()
                        # Delete
                        if st.button("🗑️ Delete Chat", key=f"del_{s_id}", type="primary"):
                            delete_session(s_id)
                            # Fallback if deleting active chat
                            if st.session_state.current_session_id == s_id:
                                remaining = get_all_sessions()
                                st.session_state.current_session_id = (
                                    remaining[0]["id"] if remaining else create_session()["id"]
                                )
                            st.rerun()

    # ------------------------------------
    # TAB 2: NOTES & FOLDERS EXPLORER
    # ------------------------------------
    with tab_folders:
        st.markdown("#### 📂 Notes & Folder Explorer")

        # Create new folder
        with st.expander("➕ Create New Folder", expanded=False):
            new_f_name = st.text_input("Folder Name:", placeholder="e.g. OS, DBMS, Algorithms", key="sidebar_new_folder_inp")
            if st.button("Create Folder", key="sidebar_create_folder_btn", use_container_width=True):
                if new_f_name.strip():
                    res = create_folder(new_f_name.strip())
                    if res["success"]:
                        st.success(f"Created folder '{res['folder']}'")
                        st.rerun()
                else:
                    st.warning("Please enter a valid folder name.")

        folders = get_all_folders()
        all_docs = get_folder_documents()

        st.caption(f"Total Folders: **{len(folders)}** | Indexed Chunks: **{get_document_count()}**")

        for f in folders:
            f_name = f["name"]
            f_docs = [d for d in all_docs if d["folder"] == f_name]
            f_chunks = f["chunk_count"]

            with st.expander(f"📁 {f_name} ({len(f_docs)} docs • {f_chunks} chunks)"):
                if not f_docs:
                    st.caption("No PDF documents in this folder yet.")
                else:
                    for d in f_docs:
                        d_name = d["filename"]
                        d_size = d.get("file_size", "--")
                        d_chunks = d.get("chunk_count", 0)

                        col_doc_info, col_doc_del = st.columns([0.8, 0.2])
                        with col_doc_info:
                            st.markdown(f"📄 **{d_name}**")
                            st.caption(f"Size: `{d_size}` | Chunks: `{d_chunks}`")
                        with col_doc_del:
                            if st.button("🗑️", key=f"del_doc_{f_name}_{d_name}", help="Delete document"):
                                delete_document(d_name, folder=f_name)
                                st.rerun()

                # Delete entire folder option (if not General)
                if f_name != "General":
                    st.divider()
                    if st.button(f"🗑️ Delete Folder '{f_name}'", key=f"del_f_btn_{f_name}", type="secondary"):
                        delete_folder(f_name)
                        st.rerun()

    # ------------------------------------
    # TAB 3: UPLOAD PDFS
    # ------------------------------------
    with tab_upload:
        st.markdown("#### 📤 Ingest PDF Notes")
        folders = get_all_folders()
        folder_names = [f["name"] for f in folders]

        upload_dest = st.selectbox(
            "Target Folder:",
            folder_names,
            index=0,
            key="upload_dest_folder",
        )

        uploaded_files = st.file_uploader(
            "Choose PDF notes / slides:",
            type=["pdf"],
            accept_multiple_files=True,
            key="main_pdf_uploader",
        )

        if uploaded_files and st.button("🚀 Index & Vectorize PDFs", type="primary", use_container_width=True):
            _process_uploads(uploaded_files, upload_dest)

    # ------------------------------------
    # TAB 4: SYSTEM SETTINGS, MODELS & CLEAR
    # ------------------------------------
    with tab_settings:
        st.markdown("#### 🤖 LLM Model Management")
        avail_models = get_available_models()
        cur_model_info = get_model_info()
        cur_m_name = cur_model_info.get("model_name", "")

        if avail_models:
            st.markdown(f"**Installed Models ({len(avail_models)}):**")
            for m in avail_models:
                is_curr = m["name"] == cur_m_name
                curr_indicator = " ⭐ *(Active)*" if is_curr else ""
                col_minfo, col_mbtn = st.columns([0.70, 0.30])
                with col_minfo:
                    st.caption(f"📁 **{m['name']}** ({m['size_str']}){curr_indicator}")
                with col_mbtn:
                    if not is_curr:
                        if st.button("Use", key=f"activate_{m['name']}", use_container_width=True):
                            set_active_model(m["path"])
                            st.rerun()

        st.markdown("---")
        st.markdown("##### 📥 Download / Add Model")
        model_choices = [f"{v['name']} ({v['size_str']})" for v in AVAILABLE_MODELS.values()]
        selected_model_str = st.selectbox(
            "Select Model:",
            options=model_choices,
            index=0,
            key="model_download_selector",
        )

        chosen_info = next(v for v in AVAILABLE_MODELS.values() if f"{v['name']} ({v['size_str']})" == selected_model_str)
        st.info(f"💡 **Description**: {chosen_info['description']}\n\n**Target**: `{chosen_info['filename']}`")

        if st.button(f"⬇️ Download {chosen_info['id'].upper()}", type="primary", use_container_width=True):
            prog_bar = st.progress(0, text="Starting download...")
            status_text = st.empty()

            def update_st_progress(percent, downloaded, total_size, speed):
                dl_mb = downloaded / (1024 * 1024)
                tot_mb = total_size / (1024 * 1024) if total_size > 0 else 0
                spd_mb = speed / (1024 * 1024) if speed > 0 else 0
                prog_bar.progress(int(percent), text=f"Downloading {percent:.1f}% ({dl_mb:.1f} MB / {tot_mb:.1f} MB)")
                status_text.caption(f"Speed: {spd_mb:.2f} MB/s")

            success = download_model_file(
                url=chosen_info["url"],
                output_filename=chosen_info["filename"],
                progress_callback=update_st_progress,
            )

            if success:
                st.success(f"🎉 {chosen_info['name']} downloaded successfully!")
                set_active_model(chosen_info["filename"])
                st.rerun()
            else:
                st.error("Download failed or was cancelled.")

        st.markdown("---")
        st.markdown("#### ⚙️ Data Management")

        if st.button("🗑️ Clear All Document Index", type="secondary", use_container_width=True):
            clear_all()
            st.success("Vector index & PDF storage cleared!")
            st.rerun()

        if st.button("🗑️ Clear All Chat History", type="secondary", use_container_width=True):
            clear_all_sessions()
            new_s = create_session()
            st.session_state.current_session_id = new_s["id"]
            st.success("Chat history cleared!")
            st.rerun()


# ===========================
# MAIN CHAT AREA
# ===========================

# Load Active Session from persistent storage
current_session = get_session(st.session_state.current_session_id)
if not current_session:
    current_session = get_latest_or_default_session()
    st.session_state.current_session_id = current_session["id"]

chat_messages = current_session.get("messages", [])
chat_title = current_session.get("title", "DocMind RAG Session")

# Header Section — Full Width Branding
st.markdown(
    f"""
    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 4px;">
        <div style="display: flex; align-items: center; gap: 14px;">
            <h1 style="background: linear-gradient(135deg, #6366f1, #8b5cf6, #a78bfa);
                        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
                        font-size: 2.2rem; font-weight: 800; margin: 0; white-space: nowrap;">
                DocMind RAG
            </h1>
            <span style="background: rgba(99, 102, 241, 0.2); border: 1px solid rgba(99, 102, 241, 0.4);
                         color: #c7d2fe; font-size: 0.75rem; font-weight: 700; padding: 4px 12px; border-radius: 20px; white-space: nowrap;">
                CS LEARNING ASSISTANT
            </span>
        </div>
    </div>
    <p style="color: #94a3b8; font-size: 0.95rem; margin: 0 0 10px 0;">
        Active Chat: <b style="color:#e0e7ff;">{chat_title}</b>
    </p>
    """,
    unsafe_allow_html=True,
)

# Controls Row: Dynamic Model Selector & Multi-Folder Search Scope
avail_models = get_available_models()
if len(avail_models) > 1:
    col_model, col_scope = st.columns([0.42, 0.58])
    with col_model:
        model_names = [m["name"] for m in avail_models]
        cur_m_name = get_model_info().get("model_name", model_names[0])
        cur_idx = model_names.index(cur_m_name) if cur_m_name in model_names else 0
        selected_model = st.selectbox(
            "🤖 Active LLM Model:",
            options=model_names,
            index=cur_idx,
            key="top_model_selector",
            help="Select which local LLM model to run for reasoning and answers.",
        )
        if selected_model != cur_m_name:
            set_active_model(selected_model)
            st.rerun()
    with col_scope:
        available_folders = [f["name"] for f in get_all_folders()]
        scope_options = ["All"] + available_folders
        selected_scope = st.multiselect(
            "🎯 Search Scope:",
            options=scope_options,
            default=["All"] if "All" in scope_options else [available_folders[0]],
            key="scope_multiselect",
            help="Select one folder, multiple specific folders (e.g. OS + DBMS), or 'All' to query everything.",
        )
else:
    available_folders = [f["name"] for f in get_all_folders()]
    scope_options = ["All"] + available_folders
    selected_scope = st.multiselect(
        "🎯 Search Scope:",
        options=scope_options,
        default=["All"] if "All" in scope_options else [available_folders[0]],
        key="scope_multiselect",
        help="Select one folder, multiple specific folders (e.g. OS + DBMS), or 'All' to query everything.",
    )

# Clean scope logic
if not selected_scope:
    effective_scope = ["All"]
elif "All" in selected_scope and len(selected_scope) > 1:
    effective_scope = [s for s in selected_scope if s != "All"]
else:
    effective_scope = selected_scope

st.session_state.selected_folders = effective_scope

st.divider()


# ===========================
# Display Conversation Messages
# ===========================

if not chat_messages:
    st.markdown(
        """
        <div style="text-align: center; padding: 2.5rem 1rem; background: rgba(15, 23, 42, 0.4);
                    border: 1px dashed rgba(99, 102, 241, 0.3); border-radius: 16px; margin: 1rem 0;">
            <div style="font-size: 2.5rem; margin-bottom: 0.5rem;">📚</div>
            <h3 style="color: #c7d2fe; margin-bottom: 0.5rem;">Ready to master Computer Science concepts!</h3>
            <p style="color: #94a3b8; max-width: 580px; margin: 0 auto 1rem auto; font-size: 0.95rem;">
                Upload your PDF notes or textbooks in the sidebar. Ask any question to get in-depth explanations,
                step-by-step algorithms, live <b>Mermaid diagrams (exportable as PNG/SVG)</b>, and clean code examples.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

for msg_idx, msg in enumerate(chat_messages):
    role = msg.get("role", "user")
    content = msg.get("content", "")
    sources = msg.get("sources", [])
    exec_time = msg.get("execution_time") or msg.get("time")
    scope = msg.get("folder_scope")
    msg_id = msg.get("id", str(msg_idx))
    feedback = msg.get("feedback")
    msg_mode = msg.get("mode")
    msg_ts = msg.get("timestamp", time.time())
    msg_time_str = datetime.fromtimestamp(msg_ts).strftime("%I:%M %p")

    with st.chat_message(role):
        render_message_content(content)

        if role == "user":
            st.markdown(
                f'<div style="text-align: right; margin-top: 4px;">'
                f'<span style="font-size: 0.75rem; color: #64748b; font-weight: 500;">🕒 {msg_time_str}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

        # Meta tags & action row for assistant messages
        elif role == "assistant":
            badges_html = []
            if sources:
                for s in sources:
                    badges_html.append(f'<span class="source-badge">📎 {s}</span>')
            if exec_time:
                badges_html.append(f'<span class="timing-badge">⏱️ {exec_time:.2f}s</span>')
            if scope and scope != "All":
                scope_str = ", ".join(scope) if isinstance(scope, list) else str(scope)
                badges_html.append(f'<span class="scope-badge">📁 {scope_str}</span>')
            badges_html.append(f'<span class="time-badge">🕒 {msg_time_str}</span>')

            if badges_html:
                st.markdown(" ".join(badges_html), unsafe_allow_html=True)

            # Minimalist Action Toolbar: Copy, Like, Dislike (No audio, No download)
            render_assistant_actions(content=content, msg_id=msg_id, feedback=feedback)


# ===========================
# Chat Input & Execution
# ===========================

if prompt := st.chat_input("Ask a question about your CS notes and PDFs..."):
    # 1. Validation Checks
    if get_document_count() == 0:
        st.warning("📭 No documents indexed yet. Upload PDFs using the sidebar first.")
        st.stop()

    if not is_model_loaded():
        st.error(
            "⚠️ **Local LLM Model Not Found!**\n\n"
            "Please download the Qwen2.5-3B-Instruct GGUF model into the `models/` directory "
            "(run `python download_model.py` in your terminal)."
        )
        st.stop()

    # Capture prior history turns from current active session
    prior_history = list(chat_messages)

    # 2. Add and display user message
    user_msg_dict = add_message(
        session_id=st.session_state.current_session_id,
        role="user",
        content=prompt,
        folder_scope=st.session_state.selected_folders,
    )

    with st.chat_message("user"):
        render_message_content(prompt)
        current_time_str = datetime.now().strftime("%I:%M %p")
        st.markdown(
            f'<div style="text-align: right; margin-top: 4px;">'
            f'<span style="font-size: 0.75rem; color: #64748b; font-weight: 500;">🕒 {current_time_str}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # 3. Generate Assistant Response
    with st.chat_message("assistant"):
        start_time = time.time()

        # Step A: Embed Query
        with st.spinner("🔍 Searching your vector knowledge base..."):
            query_embedding = embed_query(prompt)

            # Step B: Multi-Folder Scoped Retrieval
            target_folders = (
                None
                if "All" in st.session_state.selected_folders
                else st.session_state.selected_folders
            )

            results = vector_query(
                query_embedding,
                top_k=TOP_K,
                folder=target_folders,
            )

        chunks = results.get("chunks", [])
        metadatas = results.get("metadatas", [])

        if not chunks:
            fallback_response = (
                "I couldn't find matching content in the selected folder scope. "
                "Try broadening your search to 'All' or uploading additional PDF notes."
            )
            st.markdown(fallback_response)
            elapsed = round(time.time() - start_time, 2)
            add_message(
                session_id=st.session_state.current_session_id,
                role="assistant",
                content=fallback_response,
                sources=[],
                execution_time=elapsed,
                folder_scope=st.session_state.selected_folders,
                mode="llm",
            )
        else:
            # Step C: Assemble context and sources
            sources = []
            context_parts = []
            for idx, chunk in enumerate(chunks):
                meta = metadatas[idx] if idx < len(metadatas) else {}
                src = meta.get("source", "Document")
                folder = meta.get("folder", "General")
                context_parts.append(f"[Source: {src} | Folder: {folder}]\n{chunk}")

                label = f"{src} ({folder})" if folder != "General" else src
                if label not in sources:
                    sources.append(label)

            context = "\n\n---\n\n".join(context_parts)
            response_placeholder = st.empty()
            full_response = ""

            try:
                token_stream = generate(
                    prompt=prompt,
                    context=context,
                    history=prior_history,
                    stream=True,
                )

                for token in token_stream:
                    full_response += token
                    response_placeholder.markdown(full_response + "▌")

                response_placeholder.empty()
                with response_placeholder.container():
                    render_message_content(full_response)

            except Exception as e:
                full_response = f"⚠️ LLM Generation encountered an error: {str(e)}"
                response_placeholder.empty()
                with response_placeholder.container():
                    render_message_content(full_response)

            elapsed = round(time.time() - start_time, 2)

            # Badges + Timestamp
            badges_html = []
            for s in sources:
                badges_html.append(f'<span class="source-badge">📎 {s}</span>')
            badges_html.append(f'<span class="timing-badge">⏱️ {elapsed:.2f}s</span>')
            if target_folders:
                badges_html.append(f'<span class="scope-badge">📁 {", ".join(target_folders)}</span>')
            ans_time_str = datetime.now().strftime("%I:%M %p")
            badges_html.append(f'<span class="time-badge">🕒 {ans_time_str}</span>')

            st.markdown(" ".join(badges_html), unsafe_allow_html=True)

            # Persist to disk
            assistant_msg_dict = add_message(
                session_id=st.session_state.current_session_id,
                role="assistant",
                content=full_response,
                sources=sources,
                execution_time=elapsed,
                folder_scope=st.session_state.selected_folders,
                mode="llm",
            )

            # Action Bar
            render_assistant_actions(
                content=full_response,
                msg_id=assistant_msg_dict.get("id") if assistant_msg_dict else "latest",
            )

            # Rerun to update chat title and sidebar counters
            st.rerun()
