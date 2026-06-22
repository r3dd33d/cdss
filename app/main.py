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

from app.chat_bridge import route_and_reply
from app.components import disclaimer, feedback, report_view, suggestions, thinking_trace
from app.components.trace_labels import derive_steps
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


def _finalize_run(handle: RunHandle, steps: list) -> None:
    """Attach the run's report + derived steps to a new assistant message."""
    if handle.result():
        st.session_state.last_report = handle.result()
        st.session_state.messages.append({
            "role": "assistant", "content": "",
            "report": handle.result(), "steps": steps, "trace_state": "completed",
        })
        st.session_state.run_status = "completed"
    else:
        st.session_state.messages.append({
            "role": "assistant",
            "content": f":material/error: Run failed: {handle.error()}",
            "steps": steps, "trace_state": "failed",
        })
        st.session_state.run_status = "failed"
    st.session_state.run_handle = None


def _render_live_turn() -> None:
    """Render the in-progress assistant turn with a live thinking block in the thread."""
    with st.chat_message("assistant"):
        @st.fragment(run_every="0.7s")
        def _live():
            handle = st.session_state.run_handle
            if handle is None:
                return
            st.session_state.events.extend(handle.drain_events())
            steps = derive_steps(st.session_state.events)
            thinking_trace.render_live(steps)
            if handle.done():
                _finalize_run(handle, steps)
                st.rerun()

        _live()


def _start_research_run(text: str, files: list | None = None) -> None:
    """Start the pipeline without appending the user message (caller handles that)."""
    runner = _get_runner()
    st.session_state.events = []  # isolate this run's trace from any prior turn
    handle: RunHandle = start_run(runner, text, files)
    st.session_state.run_handle = handle
    st.session_state.run_status = "running"
    st.rerun()


def _submit_message(text: str, files: list | None = None) -> None:
    """Append user message and start the pipeline (research path)."""
    try:
        user_content = text if text.strip() else ":material/attach_file: PDF uploaded"
        st.session_state.messages.append({"role": "user", "content": user_content})
        _start_research_run(text, files)
    except ValueError as exc:
        st.error(str(exc))


def _handle_chat_input(text: str, files: list | None) -> None:
    """Route message: chat/clarify reply inline, or start research pipeline."""
    prior = st.session_state.get("last_report")
    # PDF upload always forces full research pipeline.
    if files:
        _submit_message(text, files)
        return

    decision, reply = route_and_reply(
        text,
        has_prior_report=prior is not None,
        prior_report=prior,
    )
    st.session_state.messages.append({"role": "user", "content": text})

    if decision.mode == "research":
        _start_research_run(text, None)
    else:
        st.session_state.messages.append({"role": "assistant", "content": reply or ""})
        st.rerun()


init()
disclaimer.render()

with st.sidebar:
    if st.button(":material/refresh: New case", use_container_width=True):
        reset()
        st.rerun()

st.subheader("Chat")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg.get("steps"):
            thinking_trace.render_static(msg["steps"], msg.get("trace_state", "completed"))
        if msg.get("report"):
            report_view.render(msg["report"])
            feedback.render()
        elif msg.get("content"):
            st.write(msg["content"])

if st.session_state.run_status == "running" and st.session_state.run_handle:
    _render_live_turn()

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
        _handle_chat_input(text, files or None)
