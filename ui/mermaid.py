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

    # Replace inner double quotes with single quotes
    txt = txt.replace('"', "'")
    # Replace inner square brackets with parentheses to prevent nested bracket syntax errors
    txt = txt.replace("[", "(").replace("]", ")")
    # Replace backslashes with forward slashes
    txt = txt.replace("\\", "/")
    # Remove newlines inside labels
    txt = txt.replace("\n", " ").replace("\r", "")
    return txt.strip()


def parse_and_repair_nodes_in_segment(segment: str) -> list[str]:
    """
    Parses a string segment (between arrows) into one or more repaired Mermaid node tokens.
    Handles mismatched brackets (e.g. B(Text]), complex labels with inner brackets/spaces,
    and bare IDs.
    """
    segment = segment.strip()
    if not segment:
        return []

    tokens = []
    i = 0
    n = len(segment)

    while i < n:
        # Skip whitespace
        while i < n and segment[i].isspace():
            i += 1
        if i >= n:
            break

        # Check if an identifier starts at i: [A-Za-z0-9_]+
        m_id = re.match(r"^[A-Za-z0-9_]+", segment[i:])
        if not m_id:
            # Not a standard ID, might be punctuation or unquoted text like "..."
            next_space = segment.find(" ", i)
            if next_space == -1:
                chunk = segment[i:]
                i = n
            else:
                chunk = segment[i:next_space]
                i = next_space + 1
            cleaned = _clean_node_label(chunk)
            if cleaned:
                tokens.append(f'Node["{cleaned}"]')
            continue

        node_id = m_id.group(0)
        i += len(node_id)

        # Skip whitespace between node_id and opening bracket (e.g. NodeA [Label])
        while i < n and segment[i].isspace():
            i += 1

        if i >= n:
            tokens.append(node_id)
            break

        # Check for opening bracket shapes
        # 1. Database / Cylinder: [( ... )]
        if segment[i:i+2] == "[(":
            i += 2
            end_idx = segment.find(")]", i)
            if end_idx != -1:
                lbl = segment[i:end_idx]
                i = end_idx + 2
            else:
                m_end = re.search(r"[\)\]]", segment[i:])
                if m_end:
                    lbl = segment[i:i+m_end.start()]
                    i = i + m_end.end()
                else:
                    lbl = segment[i:]
                    i = n
            tokens.append(f'{node_id}[("{_clean_node_label(lbl)}")]')

        # 2. Stadium / Pill: ([ ... ])
        elif segment[i:i+2] == "([":
            i += 2
            end_idx = segment.find("])", i)
            if end_idx != -1:
                lbl = segment[i:end_idx]
                i = end_idx + 2
            else:
                m_end = re.search(r"[\)\]]", segment[i:])
                if m_end:
                    lbl = segment[i:i+m_end.start()]
                    i = i + m_end.end()
                else:
                    lbl = segment[i:]
                    i = n
            tokens.append(f'{node_id}(["{_clean_node_label(lbl)}"])')

        # 3. Subroutine: [[ ... ]]
        elif segment[i:i+2] == "[[":
            i += 2
            end_idx = segment.find("]]", i)
            if end_idx != -1:
                lbl = segment[i:end_idx]
                i = end_idx + 2
            else:
                m_end = re.search(r"\]", segment[i:])
                if m_end:
                    lbl = segment[i:i+m_end.start()]
                    i = i + m_end.end()
                else:
                    lbl = segment[i:]
                    i = n
            tokens.append(f'{node_id}[["{_clean_node_label(lbl)}"]]')

        # 4. Hexagon: {{ ... }}
        elif segment[i:i+2] == "{{":
            i += 2
            end_idx = segment.find("}}", i)
            if end_idx != -1:
                lbl = segment[i:end_idx]
                i = end_idx + 2
            else:
                m_end = re.search(r"\}", segment[i:])
                if m_end:
                    lbl = segment[i:i+m_end.start()]
                    i = i + m_end.end()
                else:
                    lbl = segment[i:]
                    i = n
            tokens.append(f'{node_id}{{"{_clean_node_label(lbl)}"}}')

        # 5. Circle: (( ... ))
        elif segment[i:i+2] == "((":
            i += 2
            end_idx = segment.find("))", i)
            if end_idx != -1:
                lbl = segment[i:end_idx]
                i = end_idx + 2
            else:
                m_end = re.search(r"\)", segment[i:])
                if m_end:
                    lbl = segment[i:i+m_end.start()]
                    i = i + m_end.end()
                else:
                    lbl = segment[i:]
                    i = n
            tokens.append(f'{node_id}(("{_clean_node_label(lbl)}"))')

        # 6. Decision / Rhombus: { ... }
        elif segment[i] == "{":
            i += 1
            m_end = re.search(r"[\}\]\)]", segment[i:])
            if m_end:
                lbl = segment[i:i+m_end.start()]
                i = i + m_end.end()
            else:
                lbl = segment[i:]
                i = n
            tokens.append(f'{node_id}{{"{_clean_node_label(lbl)}"}}')

        # 7. Rounded rectangle: ( ... ) or mismatched ( ... ]
        elif segment[i] == "(":
            i += 1
            m_end = re.search(r"[\)\]\}]", segment[i:])
            if m_end:
                lbl = segment[i:i+m_end.start()]
                i = i + m_end.end()
            else:
                lbl = segment[i:]
                i = n
            tokens.append(f'{node_id}("{_clean_node_label(lbl)}")')

        # 8. Standard rectangle: [ ... ] or mismatched [ ... )
        elif segment[i] == "[":
            i += 1
            # Check if inner quotes are present e.g. ["..."]
            if i < n and (segment[i] == '"' or segment[i] == "'"):
                q = segment[i]
                i += 1
                end_q = segment.find(q, i)
                if end_q != -1:
                    lbl = segment[i:end_q]
                    i = end_q + 1
                    if i < n and segment[i] == "]":
                        i += 1
                else:
                    lbl = segment[i:]
                    i = n
            else:
                # Look for closing bracket followed by whitespace/end
                m_end = re.search(r"(?:\]|\)|\})(?:\s+[A-Za-z0-9_]+|\s*$)", segment[i:])
                if m_end:
                    lbl = segment[i:i+m_end.start()]
                    i = i + m_end.start() + 1
                else:
                    m_first_end = re.search(r"[\]\)]", segment[i:])
                    if m_first_end:
                        lbl = segment[i:i+m_first_end.start()]
                        i = i + m_first_end.end()
                    else:
                        lbl = segment[i:]
                        i = n
            tokens.append(f'{node_id}["{_clean_node_label(lbl)}"]')

        else:
            tokens.append(node_id)

    return tokens


def sanitize_mermaid_code(code: str) -> str:
    """
    Cleans, repairs, and sanitizes LLM-generated Mermaid diagrams,
    including mismatched brackets, unclosed nodes, unquoted labels,
    multi-statement lines, truncated arrows, and sequence diagram errors.
    """
    code = code.strip()
    code = re.sub(r"^```(?:mermaid)?", "", code, flags=re.IGNORECASE).strip()
    code = re.sub(r"```$", "", code).strip()

    # Normalize unicode smart quotes
    code = code.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")

    raw_lines = [l.rstrip() for l in code.splitlines() if l.strip()]
    if not raw_lines:
        return 'flowchart TD\n    A["Processing Complete"]'

    # Valid Mermaid diagram headers
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

    arrow_re = re.compile(
        r"(\s*(?:-->\|.*?\||--\s*\|.*?\|\s*-->|--\s+[^\-\n>]+\s+-->|-->|---|==>|-\.->|-->>|->>|->|--)\s*)"
    )

    for idx, line in enumerate(raw_lines):
        sline = line.strip()
        if not sline:
            continue

        if idx == 0:
            clean_lines.append(sline)
            continue

        # Comments
        if sline.startswith("%%"):
            clean_lines.append(sline)
            continue

        # Subgraphs and end keywords
        if re.match(r"^subgraph\b", sline, re.IGNORECASE) or re.match(r"^end\b", sline, re.IGNORECASE):
            m_sub = re.match(r"^subgraph\s+([A-Za-z0-9_]+)(?:\s*\[\s*\"?(.*?)\"?\s*\])?\s*$", sline, re.IGNORECASE)
            if m_sub:
                sg_id = m_sub.group(1)
                sg_lbl = m_sub.group(2)
                if sg_lbl:
                    clean_lines.append(f'    subgraph {sg_id} ["{_clean_node_label(sg_lbl)}"]')
                else:
                    clean_lines.append(f"    subgraph {sg_id}")
            else:
                clean_lines.append("    " + sline)
            continue

        if is_sequence:
            # Sequence diagram repair rules
            if re.search(r"(?:->>|-->>|->|-->)\s*$", sline):
                m = re.match(r"^([A-Za-z0-9_]+)\s*(?:->>|-->>|->|-->)\s*$", sline)
                if m:
                    actor = m.group(1)
                    sline = f"    {actor}->>Server: Request"
                else:
                    continue
            elif re.search(r"^[A-Za-z0-9_]+\s*(?:->>|-->>|->|-->)\s*[A-Za-z0-9_]+\s*$", sline):
                sline = sline + ": Process"

            if not sline.startswith("    "):
                sline = "    " + sline
            clean_lines.append(sline)

        else:
            # Flowcharts & graph diagrams
            # Check for multiple statements separated by semicolons
            sub_statements = [s.strip() for s in sline.split(";") if s.strip()]
            for stmt in sub_statements:
                # Remove dangling trailing arrows
                stmt = re.sub(r"(?:-->|---|==>|-\.->)\s*$", "", stmt).strip()
                if not stmt:
                    continue

                # Split by arrows and repair node segments
                parts = arrow_re.split(stmt)
                processed_parts = []
                for part in parts:
                    if not part or not part.strip():
                        continue
                    if arrow_re.match(part):
                        processed_parts.append(part.strip())
                    else:
                        nodes = parse_and_repair_nodes_in_segment(part)
                        if nodes:
                            processed_parts.append(" ".join(nodes))

                if processed_parts:
                    clean_lines.append("    " + " ".join(processed_parts))

    if len(clean_lines) <= 1:
        clean_lines.append('    A["Concept Overview"]')

    return "\n".join(clean_lines).strip()


def render_mermaid(code: str) -> None:
    """
    Renders interactive Mermaid diagram with built-in:
    1. 💾 Save as PNG (High-Res Canvas Export)
    2. 📥 Save as SVG (Vector Download)
    3. 📋 Copy Mermaid Code
    4. Auto Error Recovery & Fallback Box
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

            function purgeMermaidErrors() {{
                document.querySelectorAll('[id^="dmermaid"], [id^="mermaid-"], svg[aria-roledescription="error"], .mermaidError, div.error-icon').forEach(el => el.remove());
            }}

            async function drawDiagram() {{
                const container = document.getElementById('diagram-container');
                const rawCode = `{escaped_code}`;
                try {{
                    const id = 'mermaid-svg-' + Math.random().toString(36).substring(2, 9);
                    const {{ svg }} = await mermaid.render(id, rawCode);
                    purgeMermaidErrors();
                    container.innerHTML = svg;
                }} catch (err) {{
                    console.warn('Mermaid rendering fallback:', err);
                    purgeMermaidErrors();
                    setTimeout(purgeMermaidErrors, 50);
                    setTimeout(purgeMermaidErrors, 200);

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
