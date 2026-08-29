"""
DocMind RAG — Message Renderer & Interactive Actions Toolbar
Parses markdown messages, detects diagrams, and renders zero-reload action toolbars.
"""

from __future__ import annotations
import re
import base64
import streamlit as st
import streamlit.components.v1 as components

from ui.mermaid import render_mermaid


def render_message_content(content: str) -> None:
    """
    Renders message content, automatically parsing and displaying
    Markdown text, structured tables, and visual Mermaid.js diagrams.
    """
    if not content:
        return

    # Check for unclosed mermaid code block (e.g. streaming or truncated)
    lower_content = content.lower()
    mermaid_count = lower_content.count("```mermaid")
    total_fence_count = content.count("```")
    if mermaid_count > 0 and total_fence_count % 2 != 0:
        content = content.rstrip() + "\n```"

    # Match case-insensitively for ```mermaid ... ``` blocks
    mermaid_pattern = r'(?i)```mermaid\s*([\s\S]*?)\s*```'
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


def render_assistant_actions(
    content: str,
    msg_id: str,
    feedback: str | None = None,
) -> None:
    """
    Renders a sleek, modern, zero-reload action toolbar with:
    1. 📋 Copy Answer Text (direct to clipboard)
    2. 👍 Like Feedback
    3. 👎 Dislike Feedback
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
