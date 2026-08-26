"""
DocMind RAG — Mermaid Diagram Sanitizer & Interactive Exporter
Renders responsive diagrams with high-resolution PNG export, SVG download, and syntax recovery.
"""

from __future__ import annotations
import re
import streamlit.components.v1 as components


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


def render_mermaid(code: str) -> None:
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
