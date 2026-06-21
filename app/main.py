import streamlit as st

from app.components import agent_trace, disclaimer, feedback, report_view, suggestions
from app.runner_bridge import RunHandle, start_run
from app.state.session import init, reset

st.set_page_config(page_title="CDSS — Clinical Research Assistant", layout="wide")


@st.cache_resource
def _get_runner():
    """Build the core runner once per session; loads LLM client and KG lazily."""
    from cdss.config.settings import load_settings
    from cdss.pipeline.runner import build_runner
    return build_runner(load_settings())


init()
disclaimer.render()

col_chat, col_trace = st.columns([3, 2])

with col_chat:
    st.subheader("Chat")

    # Render prior messages.
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            if msg["role"] == "assistant" and msg.get("report"):
                report_view.render(msg["report"])
                feedback.render()
            else:
                st.write(msg["content"])

    # Suggestion chips before first message.
    if not st.session_state.messages and st.session_state.run_status == "idle":
        chosen = suggestions.render()
        if chosen:
            st.session_state.messages.append({"role": "user", "content": chosen})
            st.rerun()

    # Chat input — accepts optional PDF attachment.
    prompt = st.chat_input(
        "Describe your diagnosis or upload a test-result PDF…",
        accept_file=True,
        file_type=["pdf"],
    )

    if prompt and st.session_state.run_status == "idle":
        text = prompt.text or ""
        files = prompt.files or []
        try:
            runner = _get_runner()
            handle: RunHandle = start_run(runner, text, files or None)
            st.session_state.run_handle = handle
            st.session_state.run_status = "running"
            user_content = text if text else "📎 PDF uploaded"
            st.session_state.messages.append({"role": "user", "content": user_content})
            st.rerun()
        except ValueError as exc:
            st.error(str(exc))

    if st.button("🔄 New case", use_container_width=False):
        reset()
        st.rerun()

with col_trace:
    st.subheader("Agent Activity")
    handle: RunHandle | None = st.session_state.run_handle

    if handle and st.session_state.run_status == "running":
        @st.fragment(run_every="0.7s")
        def _live_trace():
            new_events = handle.drain_events()
            st.session_state.events.extend(new_events)
            agent_trace.render(st.session_state.events)

            if handle.done():
                status = "completed" if not handle.error() else "failed"
                st.session_state.run_status = status
                if handle.result():
                    st.session_state.report = handle.result()
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": "",
                        "report": handle.result(),
                    })
                elif handle.error():
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": f"❌ Run failed: {handle.error()}",
                    })
                st.rerun()

        _live_trace()

    elif st.session_state.events:
        agent_trace.render(st.session_state.events)
    else:
        st.caption("Agent activity will appear here during a run.")
