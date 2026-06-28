"""
app.py
-------
A premium, ChatGPT-style Streamlit front-end for the PDF RAG backend
(rag_backend.py).

Run with:
    streamlit run app.py

Make sure GROQ_API_KEY is set in a .env file next to this script
(see .env.example).
"""

import os
import html as html_lib

import streamlit as st
from dotenv import load_dotenv

from rag_backend import (
    build_or_load_vectorstore,
    build_chain,
    get_sources,
    stream_answer,
)

load_dotenv()

UPLOAD_DIR = "uploaded_pdfs"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ---------------------------------------------------------------------------
# 👇 Credit shown in the sidebar footer + the floating corner badge.
#    Change this to your own name / handle.
# ---------------------------------------------------------------------------
BUILDER_NAME = "Sarthak Arsul"

# ---------------------------------------------------------------------------
# Page config (must be the first Streamlit call)
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="DocMind — Chat with your PDF",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Custom CSS — dark,premium theme
# ---------------------------------------------------------------------------
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
[data-testid="stToolbar"] { visibility: hidden; }
[data-testid="stToolbarActions"] { visibility: hidden; }


header, [data-testid="stHeader"] {
  background: transparent !important;
  visibility: visible !important;
}


[data-testid="collapsedControl"],
[data-testid="stSidebarCollapseButton"],
[data-testid="stSidebarCollapsedControl"],
[data-testid="stExpandSidebarButton"] {
  visibility: visible !important;
  display: flex !important;
  opacity: 1 !important;
  z-index: 999999 !important;
}
[data-testid="collapsedControl"] *,
[data-testid="stSidebarCollapseButton"] *,
[data-testid="stSidebarCollapsedControl"] *,
[data-testid="stExpandSidebarButton"] * {
  visibility: visible !important;
  opacity: 1 !important;
}

html, body { overflow-x: hidden; }
.block-container {
  padding-top: 1.6rem;
  max-width: 880px;
  position: relative;
  z-index: 1;
  animation: pageFadeIn 0.5s ease;
}

.stApp {
  background: radial-gradient(circle at top left, #1a1c23 0%, #0e0f13 65%);
  color: #e6e6e6;
}


.stApp::before, .stApp::after {
  content: "";
  position: fixed;
  width: 420px; height: 420px;
  border-radius: 50%;
  filter: blur(120px);
  z-index: 0;
  pointer-events: none;
}
.stApp::before { background: rgba(16,163,127,0.16); top: -140px; left: -120px; }
.stApp::after  { background: rgba(110,231,183,0.09); bottom: -160px; right: -120px; }

::-webkit-scrollbar { width: 8px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #4d4d58; border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: #6b6b78; }

/* Sidebar */
[data-testid="stSidebar"] {
  background: #17181d;
  border-right: 1px solid #2a2b32;
}
[data-testid="stSidebar"] * { color: #e6e6e6 !important; }

.brand { font-size: 1.35rem; font-weight: 700; display:flex; align-items:center; gap:10px; }
.brand-icon {
  display:inline-flex; align-items:center; justify-content:center;
  width:34px; height:34px; border-radius:10px; font-size:1.05rem;
  background: linear-gradient(135deg,#10a37f,#0c8a6b);
  box-shadow: 0 4px 12px rgba(16,163,127,0.35);
}
.brand-sub { color:#9b9ba3 !important; font-size:0.82rem; margin-top:2px; }

.status-card {
  background:#1f2027; border:1px solid #34353d; border-left:3px solid #10a37f;
  border-radius:10px; padding:10px 14px; margin:10px 0;
  font-size:0.88rem; line-height:1.4;
}
.muted { color:#9b9ba3 !important; font-size:0.78rem; }

.live-dot {
  display:inline-block; width:7px; height:7px; border-radius:50%;
  background:#10a37f; margin-right:6px;
  animation: livePulse 2s infinite;
}
@keyframes livePulse {
  0%   { box-shadow:0 0 0 0 rgba(16,163,127,0.55); }
  70%  { box-shadow:0 0 0 7px rgba(16,163,127,0); }
  100% { box-shadow:0 0 0 0 rgba(16,163,127,0); }
}

.builder-card { margin-top: 24px; text-align:center; }
.builder-line {
  height:1px; margin-bottom:14px;
  background: linear-gradient(90deg, transparent, #34353d, transparent);
}
.builder-text { font-size:0.84rem; color:#9b9ba3 !important; margin:0; }
.builder-name {
  font-weight:700;
  background: linear-gradient(90deg,#10a37f,#6ee7b7);
  -webkit-background-clip:text; -webkit-text-fill-color:transparent !important;
}
.builder-tag { font-size:0.7rem; color:#5c5d66 !important; margin-top:4px; }

/* Header */
.header-wrap { text-align:center; padding: 4px 0 18px; }
.app-title {
  font-size: 2.4rem; font-weight: 800; letter-spacing:-0.5px; margin-bottom: 2px;
  background: linear-gradient(90deg, #10a37f, #6ee7b7, #10a37f);
  background-size: 200% auto;
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  animation: gradientShift 6s ease infinite;
}
.app-subtitle { color:#9b9ba3; font-size:0.95rem; margin-top:0; }
.hero-pill {
  display:inline-block; margin-top:12px; padding:5px 14px; border-radius:999px;
  border:1px solid #2d4f44; background:rgba(16,163,127,0.08);
  color:#7ee9c4; font-size:0.76rem; font-weight:600; letter-spacing:0.2px;
}

.suggestions-label { color:#9b9ba3; font-size:0.85rem; margin:16px 0 8px; text-align:center; }

/* Chat bubbles */
.user-bubble {
  background: linear-gradient(135deg, #10a37f, #0c8a6b);
  color: #fff; padding: 12px 16px; border-radius: 16px 16px 4px 16px;
  display:inline-block; line-height:1.55; box-shadow: 0 2px 10px rgba(16,163,127,0.25);
}
.ai-bubble {
  background:#1f2027; border:1px solid #30313a; color:#e6e6e6;
  padding:12px 16px; border-radius: 16px 16px 16px 4px;
  display:inline-block; line-height:1.6;
}
.fade-in { animation: fadeInUp 0.3s ease-out; }

.typing-indicator { display:flex; gap:5px; align-items:center; padding:14px 16px; }
.typing-indicator span {
  width:8px; height:8px; border-radius:50%; background:#10a37f;
  animation: pulse 1.2s infinite ease-in-out;
}
.typing-indicator span:nth-child(2) { animation-delay: 0.2s; }
.typing-indicator span:nth-child(3) { animation-delay: 0.4s; }

@keyframes fadeInUp { from { opacity:0; transform:translateY(8px); } to { opacity:1; transform:translateY(0); } }
@keyframes gradientShift { 0% { background-position:0% 50%; } 50% { background-position:100% 50%; } 100% { background-position:0% 50%; } }
@keyframes pulse { 0%,80%,100% { transform:scale(0.6); opacity:0.4; } 40% { transform:scale(1); opacity:1; } }
@keyframes pageFadeIn { from { opacity:0; transform:translateY(6px); } to { opacity:1; transform:translateY(0); } }

/* Buttons */
.stButton>button {
  border-radius: 10px; border: 1px solid #34353d; background:#1f2027;
  color:#e6e6e6; transition: all 0.18s ease;
}
.stButton>button:hover { border-color:#10a37f; color:#10a37f; transform: translateY(-1px); }
.stButton>button:active { transform: translateY(0) scale(0.98); }

button[kind="primary"] {
  background: linear-gradient(135deg, #10a37f, #0c8a6b) !important;
  border:none !important; color:#fff !important;
  position:relative; overflow:hidden;
}
button[kind="primary"]::after {
  content:""; position:absolute; top:0; left:-75%; width:50%; height:100%;
  background: linear-gradient(120deg, transparent, rgba(255,255,255,0.35), transparent);
  transform: skewX(-20deg); transition: left 0.5s ease;
}
button[kind="primary"]:hover::after { left:130%; }
button[kind="primary"]:hover { filter:brightness(1.08); color:#fff !important; }

[data-testid="stChatInput"] textarea { border-radius: 14px; }

/* Expanders (sources panel) */
[data-testid="stExpander"] {
  border:1px solid #2c2d33 !important;
  border-radius:12px !important;
  background:#15161b !important;
}

/* Floating builder credit badge — desktop only */
.builder-badge {
  position: fixed; bottom: 18px; right: 22px; z-index: 9999;
  background: rgba(23,24,29,0.85); backdrop-filter: blur(8px);
  border: 1px solid #33343c; border-radius: 999px; padding: 7px 14px;
  font-size: 0.78rem; color: #9b9ba3;
  box-shadow: 0 4px 14px rgba(0,0,0,0.35);
  transition: all 0.25s ease;
}
.builder-badge:hover {
  border-color:#10a37f; transform: translateY(-2px);
  box-shadow: 0 6px 18px rgba(16,163,127,0.35);
}
.builder-badge b {
  background: linear-gradient(90deg,#10a37f,#6ee7b7);
  -webkit-background-clip:text; -webkit-text-fill-color:transparent;
  font-weight:700;
}
@media (max-width: 900px) { .builder-badge { display:none; } }
</style>
""",
    unsafe_allow_html=True,
)

# Floating bottom-right credit badge (desktop)
st.markdown(
    f'<div class="builder-badge">✨ Built by <b>{html_lib.escape(BUILDER_NAME)}</b></div>',
    unsafe_allow_html=True,
)


def esc(text: str) -> str:
    """Escape text for safe injection into our custom HTML bubbles."""
    return html_lib.escape(text).replace("\n", "<br>")


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------
defaults = {
    "messages": [],
    "ready": False,
    "chain": None,
    "retriever": None,
    "vectorstore": None,
    "doc_name": None,
    "num_chunks": 0,
    "k": 3,
    "temp": 0.2,
    "pending_question": None,
}
for key, val in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val

# ---------------------------------------------------------------------------
# API key check
# ---------------------------------------------------------------------------
if not os.getenv("GROQ_API_KEY"):
    st.error("⚠️ GROQ_API_KEY not found. Add it to a `.env` file (see `.env.example`) and restart the app.")
    st.stop()

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown(
        '<div class="brand"><span class="brand-icon">🧠</span><span>DocMind</span></div>',
        unsafe_allow_html=True,
    )
    st.markdown('<p class="brand-sub">Chat with any PDF, instantly.</p>', unsafe_allow_html=True)
    st.markdown("---")

    uploaded_file = st.file_uploader("Upload a PDF", type=["pdf"])

    col_a, col_b = st.columns(2)
    process_clicked = col_a.button("⚡ Process", use_container_width=True, type="primary", disabled=uploaded_file is None)
    reindex_clicked = col_b.button("🔄 Re-index", use_container_width=True, disabled=uploaded_file is None)

    if process_clicked or reindex_clicked:
        file_bytes = uploaded_file.getvalue()
        save_path = os.path.join(UPLOAD_DIR, uploaded_file.name)
        with open(save_path, "wb") as f:
            f.write(file_bytes)

        with st.spinner("Reading & indexing your document…"):
            try:
                vectorstore, num_chunks, _cache_dir, loaded_from_cache = build_or_load_vectorstore(
                    save_path, file_bytes, uploaded_file.name, force_rebuild=reindex_clicked
                )
                chain, retriever = build_chain(vectorstore, k=st.session_state.k, temperature=st.session_state.temp)

                st.session_state.vectorstore = vectorstore
                st.session_state.chain = chain
                st.session_state.retriever = retriever
                st.session_state.doc_name = uploaded_file.name
                st.session_state.num_chunks = num_chunks
                st.session_state.ready = True
                st.session_state.messages = []

                tag = "Loaded from cache ⚡" if loaded_from_cache else "Freshly indexed ✅"
                st.success(f"{tag} — {num_chunks} chunks ready.")
            except Exception as e:
                st.error(f"Couldn't process this PDF: {e}")

    if st.session_state.ready:
        st.markdown(
            f"""<div class="status-card">
                    <span class="live-dot"></span><b>{esc(st.session_state.doc_name)}</b><br>
                    <span class="muted">{st.session_state.num_chunks} chunks indexed</span>
                </div>""",
            unsafe_allow_html=True,
        )

    with st.expander("⚙️ Settings"):
        k = st.slider("Context chunks (k)", 1, 8, st.session_state.k)
        temp = st.slider("Creativity", 0.0, 1.0, st.session_state.temp, 0.1)

        if st.session_state.ready and (k != st.session_state.k or temp != st.session_state.temp):
            st.session_state.k = k
            st.session_state.temp = temp
            st.session_state.chain, st.session_state.retriever = build_chain(
                st.session_state.vectorstore, k=k, temperature=temp
            )

    st.markdown("---")
    if st.button("🗑️ Clear chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

    st.markdown(
        f"""<div class="builder-card">
                <div class="builder-line"></div>
                <p class="builder-text">✨ Crafted by <span class="builder-name">{html_lib.escape(BUILDER_NAME)}</span></p>
                <p class="builder-tag">⚡ Groq · Llama 4 Scout &nbsp;|&nbsp; 🧬 FAISS + MiniLM</p>
            </div>""",
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.markdown(
    """
    <div class="header-wrap">
        <h1 class="app-title">DocMind</h1>
        <p class="app-subtitle">Ask anything. Get answers straight from your PDF.</p>
        <span class="hero-pill">⚡ RAG-Powered · Groq Llama 4 Scout</span>
    </div>
    """,
    unsafe_allow_html=True,
)


def render_sources(sources):
    if not sources:
        return
    with st.expander("📄 View sources"):
        for i, doc in enumerate(sources, start=1):
            page = doc.metadata.get("page", "—")
            st.markdown(f"**Source {i} · page {page}**")
            st.caption(doc.page_content[:300].strip() + "…")


# ---------------------------------------------------------------------------
# Chat history
# ---------------------------------------------------------------------------
for msg in st.session_state.messages:
    avatar = "🧑‍💻" if msg["role"] == "user" else "🤖"
    bubble_class = "user-bubble" if msg["role"] == "user" else "ai-bubble"
    with st.chat_message(msg["role"], avatar=avatar):
        st.markdown(f'<div class="{bubble_class}">{esc(msg["content"])}</div>', unsafe_allow_html=True)
        if msg["role"] == "assistant":
            render_sources(msg.get("sources"))

# ---------------------------------------------------------------------------
# Empty-state suggestions
# ---------------------------------------------------------------------------
if st.session_state.ready and not st.session_state.messages:
    st.markdown('<p class="suggestions-label">✨ Try asking</p>', unsafe_allow_html=True)
    suggestions = [
        "Summarize this document in 3 bullet points",
        "Who are the key people or entities mentioned?",
        "What is the main conclusion of this document?",
    ]
    cols = st.columns(3)
    for col, sugg in zip(cols, suggestions):
        if col.button(sugg, use_container_width=True):
            st.session_state.pending_question = sugg

if not st.session_state.ready:
    st.info("👈 Upload a PDF in the sidebar and click **Process** to start chatting.")

# ---------------------------------------------------------------------------
# Chat input
# ---------------------------------------------------------------------------
question = st.chat_input(
    "Message DocMind…" if st.session_state.ready else "Upload & process a PDF first…",
    disabled=not st.session_state.ready,
)
if st.session_state.pending_question:
    question = st.session_state.pending_question
    st.session_state.pending_question = None

if question:
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user", avatar="🧑‍💻"):
        st.markdown(f'<div class="user-bubble fade-in">{esc(question)}</div>', unsafe_allow_html=True)

    sources = get_sources(st.session_state.retriever, question)

    with st.chat_message("assistant", avatar="🤖"):
        placeholder = st.empty()
        placeholder.markdown(
            '<div class="ai-bubble typing-indicator"><span></span><span></span><span></span></div>',
            unsafe_allow_html=True,
        )

        full_response = ""
        try:
            for chunk in stream_answer(st.session_state.chain, question):
                full_response += chunk
                placeholder.markdown(
                    f'<div class="ai-bubble fade-in">{esc(full_response)}▌</div>', unsafe_allow_html=True
                )
        except Exception as e:
            full_response = f"⚠️ Something went wrong while generating the answer: {e}"

        placeholder.markdown(f'<div class="ai-bubble fade-in">{esc(full_response)}</div>', unsafe_allow_html=True)
        render_sources(sources)

    st.session_state.messages.append({"role": "assistant", "content": full_response, "sources": sources})