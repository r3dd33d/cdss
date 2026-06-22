import sys

if sys.version_info < (3, 11):
    raise SystemExit(
        "CDSS requires Python 3.11+, but this interpreter is "
        f"{sys.version.split()[0]}.\n"
        "Run from the project venv: ./run  or  make run"
    )

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import streamlit as st

from app.components import agent_trace, disclaimer, feedback, report_view, suggestions
from app.runner_bridge import RunHandle, start_run
from app.state.session import init, reset

st.set_page_config(
    page_title="CDSS — Clinical Research Assistant",
    page_icon=":material/medical_services:",
    layout="wide",
)


@st.cache_resource
def _get_runner():
    """Build the core runner once per session; loads LLM client and KG lazily."""
    from cdss.config.settings import load_settings
    from cdss.pipeline.runner import build_runner
    return build_runner(load_settings())


def _render_sidebar_trace(handle: RunHandle | None) -> None:
    """Show live or completed agent activity in the sidebar."""
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
                        "content": f":material/error: Run failed: {handle.error()}",
                    })
                st.rerun()

        _live_trace()
    elif st.session_state.events:
        agent_trace.render(st.session_state.events)
    else:
        st.caption("Agent activity will appear here during a run.")


def _submit_message(text: str, files: list | None = None) -> None:
    """Append user message and start the pipeline."""
    try:
        runner = _get_runner()
        handle: RunHandle = start_run(runner, text, files)
        st.session_state.run_handle = handle
        st.session_state.run_status = "running"
        user_content = text if text.strip() else ":material/attach_file: PDF uploaded"
        st.session_state.messages.append({"role": "user", "content": user_content})
        st.rerun()
    except ValueError as exc:
        st.error(str(exc))


init()
disclaimer.render()

with st.sidebar:
    st.subheader(":material/psychology: Agent activity")
    _render_sidebar_trace(st.session_state.run_handle)
    st.divider()
    if st.button(":material/refresh: New case", use_container_width=True):
        reset()
        st.rerun()

st.subheader("Chat")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg["role"] == "assistant" and msg.get("report"):
            report_view.render(msg["report"])
            feedback.render()
        else:
            st.write(msg["content"])

if not st.session_state.messages and st.session_state.run_status == "idle":
    chosen = suggestions.render()
    if chosen:
        _submit_message(chosen)

prompt = st.chat_input(
    "Describe your diagnosis or upload a test-result PDF…",
    accept_file=True,
    file_type=["pdf"],
)

if prompt and st.session_state.run_status == "idle":
    text = prompt.text or ""
    files = prompt.files or []
    if text.strip() or files:
        _submit_message(text, files or None)
