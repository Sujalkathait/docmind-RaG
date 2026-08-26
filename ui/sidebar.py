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


def render_sidebar() -> None:
    """Renders the comprehensive sidebar with 4 tabs and system status cards."""
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

            uploaded_files = st.file_uploader(
                "Choose PDF notes / slides:",
                type=["pdf"],
                accept_multiple_files=True,
                key="main_pdf_uploader",
            )

            if uploaded_files and st.button("🚀 Index & Vectorize PDFs", type="primary", use_container_width=True):
                process_pdf_uploads(uploaded_files, upload_dest)

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
