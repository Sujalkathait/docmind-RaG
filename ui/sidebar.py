"""
DocMind RAG — Sidebar UI Component
Manages chat sessions, notes/folders explorer, PDF uploads, and LLM model settings.
"""

from __future__ import annotations
import re
import streamlit as st

from core.vector_store import (
    get_all_folders,
    get_folder_documents,
    create_folder,
    delete_folder,
    delete_document,
    clear_all,
    get_document_count,
)
from core.llm import (
    get_model_info,
    get_available_models,
    set_active_model,
)
from download_model import AVAILABLE_MODELS, download_model_file
from core.chat_manager import (
    get_all_sessions,
    create_session,
    rename_session,
    toggle_pin_session,
    delete_session,
    clear_all_sessions,
)
from ui.ingestion import process_pdf_uploads
from backend.database.crud import (
    list_memories,
    upsert_memory,
    delete_memory,
    list_knowledge_nodes,
    get_node_relationships,
    get_sources_for_node,
    list_outputs,
)
from backend.database.models import MemoryCategory
from backend.output.generator import generate_study_deliverable


def render_sidebar() -> None:
    """Renders the comprehensive sidebar with 5 tabs including Second Brain and system status cards."""
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

        # --- Sidebar Navigation Tabs (5 Tabs with Second Brain) ---
        tab_chats, tab_folders, tab_upload, tab_brain, tab_settings = st.tabs([
            "💬 Chats",
            "📁 Folders",
            "📤 Upload",
            "🧠 Second Brain",
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
                            st.markdown("**Chat Settings**")
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

            # Upload Guidelines & Capacity Info Badge
            st.markdown(
                """
                <div style="background: rgba(99, 102, 241, 0.08); border: 1px solid rgba(99, 102, 241, 0.25); border-radius: 8px; padding: 9px 12px; margin-bottom: 10px; font-size: 0.8rem; color: #cbd5e1;">
                    <div>📂 <b>Multi-PDF Upload:</b> Enabled</div>
                    <div>📦 <b>Recommended Batch:</b> 20–50 files at once</div>
                    <div>📏 <b>Max File Size:</b> Up to 200 MB per PDF</div>
                    <div>🗄️ <b>Storage Capacity:</b> Unlimited PDFs (100,000+ chunks)</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            uploaded_files = st.file_uploader(
                "Choose PDF notes / slides:",
                type=["pdf"],
                accept_multiple_files=True,
                key="main_pdf_uploader",
                help="You can select and upload multiple PDF files simultaneously into the chosen folder.",
            )

            if uploaded_files:
                total_files = len(uploaded_files)
                total_mb = sum(getattr(f, "size", 0) for f in uploaded_files) / (1024 * 1024)
                est_chunks = max(total_files * 15, int(total_mb * 60))
                st.info(f"📊 **Selected**: `{total_files}` PDF(s) ({total_mb:.1f} MB) • Est. `~{est_chunks}` chunks")

                if st.button("🚀 Index & Vectorize PDFs", type="primary", use_container_width=True):
                    process_pdf_uploads(uploaded_files, upload_dest)

        # ------------------------------------
        # TAB 4: SECOND BRAIN (PERSISTENT KNOWLEDGE, MEMORY & OUTPUTS)
        # ------------------------------------
        with tab_brain:
            st.markdown("#### 🧠 Second Brain Layer")
            brain_mem, brain_wiki, brain_studio = st.tabs([
                "🧠 Memory",
                "🌐 Wiki Graph",
                "📝 Study Studio",
            ])

            # Subtab 1: Memory & Preferences
            with brain_mem:
                st.markdown("##### 📌 Persistent User & Learning Memory")
                mems = list_memories()
                if not mems:
                    st.caption("No persistent memories saved yet.")
                else:
                    for m in mems:
                        col_m_text, col_m_del = st.columns([0.85, 0.15])
                        with col_m_text:
                            cat_label = m.category.replace("_", " ").title()
                            st.markdown(
                                f"""<div style="background: rgba(30, 41, 59, 0.7); border: 1px solid rgba(99, 102, 241, 0.3); border-radius: 6px; padding: 6px 10px; margin-bottom: 6px;">
                                    <div style="font-size: 0.75rem; color: #a5b4fc; font-weight: 700;">{cat_label} • {m.memory_key} (Imp: {m.importance_score})</div>
                                    <div style="font-size: 0.85rem; color: #e2e8f0;">{m.memory_value}</div>
                                </div>""",
                                unsafe_allow_html=True,
                            )
                        with col_m_del:
                            if st.button("✕", key=f"del_mem_{m.id}", help="Delete memory"):
                                delete_memory(m.id)
                                st.rerun()

                st.markdown("---")
                with st.expander("➕ Add New Preference / Memory", expanded=False):
                    new_cat = st.selectbox(
                        "Category",
                        options=[
                            MemoryCategory.LEARNING_PREFERENCE,
                            MemoryCategory.USER_PREFERENCE,
                            MemoryCategory.PROJECT_CONTEXT,
                            MemoryCategory.USER_GOAL,
                        ],
                        key="new_mem_cat",
                    )
                    new_key = st.text_input("Memory Key", placeholder="e.g. code_style or primary_goal", key="new_mem_key")
                    new_val = st.text_area("Value", placeholder="e.g. Always show C code examples first with intuition", key="new_mem_val")
                    new_imp = st.slider("Importance Score", 0.1, 1.0, 0.8, step=0.05, key="new_mem_imp")
                    if st.button("Save Memory", type="primary", use_container_width=True):
                        if new_key.strip() and new_val.strip():
                            upsert_memory(
                                user_id="default_user",
                                category=new_cat,
                                key=new_key,
                                value=new_val,
                                importance_score=new_imp,
                            )
                            st.success("Memory saved to Second Brain!")
                            st.rerun()

            # Subtab 2: Wiki Knowledge Graph
            with brain_wiki:
                st.markdown("##### 🌐 Structured Wiki Concepts")
                wiki_search = st.text_input("🔍 Search Concepts:", placeholder="e.g. Deadlock, TCP...", key="wiki_search_input")
                nodes = list_knowledge_nodes(query=wiki_search if wiki_search.strip() else None)
                st.caption(f"Showing **{len(nodes)}** concepts in knowledge base.")

                for node in nodes[:15]:
                    with st.expander(f"📌 {node.name} [{node.category}]", expanded=False):
                        if node.canonical_definition:
                            st.markdown(f"**Canonical Definition:**\n> {node.canonical_definition}")
                        st.markdown(f"**Summary:** {node.summary}")
                        rels = get_node_relationships(node.id)
                        if rels:
                            st.markdown("**Connected Relationships:**")
                            for r in rels:
                                other = r.target_name if r.source_node_id == node.id else r.source_name
                                st.markdown(f"- **{r.relation_type}** → `{other}` *(conf: {r.confidence})*")
                        sources = get_sources_for_node(node.id)
                        if sources:
                            st.markdown("**Anchored Sources:**")
                            for s in sources:
                                st.markdown(f"- 📄 `{s.document_name or 'Document'}` — Page {s.page_number}")

            # Subtab 3: Study Studio & Deliverables
            with brain_studio:
                st.markdown("##### 📝 Study Deliverable Generator")
                target_topic = st.text_input("Study Topic:", placeholder="e.g. Deadlock & Two-Phase Locking", key="studio_topic")
                out_type = st.selectbox("Output Format:", ["STUDY_NOTES", "SUMMARY", "QUIZ", "FLASHCARDS"], key="studio_format")
                if st.button("✨ Generate Deliverable", type="primary", use_container_width=True):
                    if target_topic.strip():
                        with st.spinner(f"Synthesizing {out_type} for '{target_topic}'..."):
                            res = generate_study_deliverable(
                                topic=target_topic,
                                output_type=out_type,
                                folder_scope=st.session_state.selected_folders,
                            )
                            if res.get("success"):
                                st.success(f"Generated and saved to `{res['file_path']}`!")
                                st.rerun()
                            else:
                                st.error(res.get("error", "Generation failed."))

                st.markdown("---")
                st.markdown("##### 🗄️ Saved Deliverables")
                saved_outputs = list_outputs()
                if not saved_outputs:
                    st.caption("No study deliverables generated yet.")
                else:
                    for out in saved_outputs[:6]:
                        st.markdown(
                            f"""<div style="background: rgba(15, 23, 42, 0.6); border: 1px solid rgba(148, 163, 184, 0.2); border-radius: 6px; padding: 6px 10px; margin-bottom: 6px;">
                                <div style="font-size: 0.8rem; font-weight: 700; color: #818cf8;">📄 {out.title}</div>
                                <div style="font-size: 0.72rem; color: #94a3b8;">Path: <code>{out.file_path}</code></div>
                            </div>""",
                            unsafe_allow_html=True,
                        )

        # ------------------------------------
        # TAB 5: SYSTEM SETTINGS, MODELS & CLEAR
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
