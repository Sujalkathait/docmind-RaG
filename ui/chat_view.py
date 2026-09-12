"""
DocMind RAG — Main Chat View & Execution Engine
Renders chat interface, search scope selector, conversation stream, and handles RAG queries.
Optimized for high-speed streaming, dynamic token limits, and detailed timing metrics.
"""

from __future__ import annotations
import time
from datetime import datetime
import streamlit as st

from config import TOP_K
from core.embedder import embed_query
from core.vector_store import (
    query as vector_query,
    get_all_folders,
    get_document_count,
)
from core.llm import (
    generate,
    is_model_loaded,
    get_model_info,
    get_available_models,
    set_active_model,
    get_dynamic_max_tokens,
)
from core.chat_manager import (
    get_session,
    add_message,
    get_latest_or_default_session,
)
from ui.message_renderer import (
    render_message_content,
    render_assistant_actions,
)


def render_chat_view() -> None:
    """Renders the main chat header, scope selector, message history, and chat input."""
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
        tok_speed = msg.get("tokens_per_sec")
        ret_time = msg.get("retrieval_time")
        scope = msg.get("folder_scope")
        msg_id = msg.get("id", str(msg_idx))
        feedback = msg.get("feedback")
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
                    timing_str = f"⏱️ {exec_time:.2f}s"
                    if tok_speed and tok_speed > 0:
                        timing_str += f" (⚡ {tok_speed:.1f} tok/s)"
                    title_attr = f"Total: {exec_time:.2f}s"
                    if ret_time:
                        title_attr += f" | Retrieval: {ret_time*1000:.0f}ms"
                    badges_html.append(f'<span class="timing-badge" title="{title_attr}">{timing_str}</span>')
                if scope and scope != "All":
                    scope_str = ", ".join(scope) if isinstance(scope, list) else str(scope)
                    badges_html.append(f'<span class="scope-badge">📁 {scope_str}</span>')
                badges_html.append(f'<span class="time-badge">🕒 {msg_time_str}</span>')

                if badges_html:
                    st.markdown(" ".join(badges_html), unsafe_allow_html=True)

                # Action Toolbar: Copy, Like, Dislike
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
                "(run `python download_model.py` in your terminal or use the ⚙️ Manage tab)."
            )
            st.stop()

        # Capture prior history turns from current active session
        prior_history = list(chat_messages)

        # 2. Add and display user message
        add_message(
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
            start_total_time = time.time()

            # Step A: Embed Query & Scoped Retrieval (Timing: t_retrieval)
            t_ret_start = time.time()
            with st.spinner("🔍 Searching your vector knowledge base..."):
                query_embedding = embed_query(prompt)

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
            t_retrieval = time.time() - t_ret_start

            chunks = results.get("chunks", [])
            metadatas = results.get("metadatas", [])

            if not chunks:
                fallback_response = (
                    "I couldn't find matching content in the selected folder scope. "
                    "Try broadening your search to 'All' or uploading additional PDF notes."
                )
                st.markdown(fallback_response)
                elapsed = round(time.time() - start_total_time, 2)
                add_message(
                    session_id=st.session_state.current_session_id,
                    role="assistant",
                    content=fallback_response,
                    sources=[],
                    execution_time=elapsed,
                    folder_scope=st.session_state.selected_folders,
                    mode="llm",
                )
                st.rerun()
            else:

                # Step B: Assemble Second Brain Grounded Context (Evidence + Wiki + Memory)
                t_prompt_start = time.time()
                from backend.orchestration.context_assembler import assemble_grounded_context
                from backend.memory.memory_evaluator import evaluate_interaction_for_memory

                assembled = assemble_grounded_context(
                    query=prompt,
                    raw_chunks=chunks,
                    metadatas=metadatas,
                    history=prior_history,
                )

                context = assembled["context"]
                sources = assembled["sources"]
                wiki_concepts = assembled.get("wiki_concepts", [])
                activated_memories = assembled.get("activated_memories", [])
                t_prompt = time.time() - t_prompt_start

                # Step C: Stream generation with dynamic token limit (Timing: t_gen)
                dynamic_tokens = get_dynamic_max_tokens(prompt)
                response_placeholder = st.empty()
                full_response = ""
                tok_count = 0
                first_token_time = None
                t_gen_start = time.time()

                try:
                    token_stream = generate(
                        prompt=prompt,
                        context=context,
                        history=prior_history,
                        max_tokens=dynamic_tokens,
                        stream=True,
                    )

                    for token in token_stream:
                        if first_token_time is None:
                            first_token_time = time.time()
                        tok_count += 1
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

                t_gen_end = time.time()
                total_elapsed = round(t_gen_end - start_total_time, 2)
                t_gen_duration = t_gen_end - (first_token_time or t_gen_start)
                tok_speed = (tok_count / t_gen_duration) if t_gen_duration > 0 else 0.0

                # Badges + Timestamp
                badges_html = []
                for s in sources:
                    badges_html.append(f'<span class="source-badge">📎 {s}</span>')

                for c in wiki_concepts:
                    badges_html.append(f'<span class="scope-badge" style="background: rgba(16, 185, 129, 0.2); border-color: rgba(16, 185, 129, 0.4); color: #6ee7b7;" title="Wiki Knowledge Link">🌐 {c}</span>')

                if activated_memories:
                    badges_html.append(f'<span class="scope-badge" style="background: rgba(245, 158, 11, 0.2); border-color: rgba(245, 158, 11, 0.4); color: #fde68a;" title="{len(activated_memories)} Memory Preferences Applied">🧠 Memory Applied</span>')

                speed_label = f"⏱️ {total_elapsed:.2f}s"
                if tok_speed > 0:
                    speed_label += f" (⚡ {tok_speed:.1f} tok/s)"
                hover_info = f"Total: {total_elapsed:.2f}s | Retrieval: {t_retrieval*1000:.0f}ms | Prep: {t_prompt*1000:.0f}ms | Gen: {t_gen_duration:.2f}s"
                badges_html.append(f'<span class="timing-badge" title="{hover_info}">{speed_label}</span>')

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
                    execution_time=total_elapsed,
                    tokens_per_sec=round(tok_speed, 1),
                    retrieval_time=round(t_retrieval, 4),
                    folder_scope=st.session_state.selected_folders,
                    mode="llm",
                )

                # Second Brain Update Loop: Evaluate interaction for persistent memory
                mem_saved = evaluate_interaction_for_memory(prompt, full_response)
                if mem_saved:
                    st.toast(f"💡 Saved preference to Second Brain: {mem_saved['key']}", icon="🧠")

                # Action Bar
                render_assistant_actions(
                    content=full_response,
                    msg_id=assistant_msg_dict.get("id") if assistant_msg_dict else "latest",
                )

                # Rerun to update chat title and sidebar counters
                st.rerun()
