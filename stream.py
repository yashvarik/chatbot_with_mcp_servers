import asyncio
import os

import streamlit as st
from dotenv import load_dotenv

from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, START, add_messages
from langchain_core.messages import HumanMessage, SystemMessage, BaseMessage, AIMessage
from typing_extensions import TypedDict, Annotated, List
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_mcp_adapters.client import MultiServerMCPClient

load_dotenv()

# ------------------------------------------------------------------
# Page config
# ------------------------------------------------------------------
st.set_page_config(
    page_title="MCP Assistant",
    page_icon="🤖",
    layout="centered",
)

# ------------------------------------------------------------------
# Styling
# ------------------------------------------------------------------
st.markdown(
    """
    <style>
    .stApp {
        background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%);
    }
    .main-title {
        text-align: center;
        font-size: 2.2rem;
        font-weight: 800;
        background: linear-gradient(90deg, #60a5fa, #a78bfa);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    .subtitle {
        text-align: center;
        color: #94a3b8;
        font-size: 0.95rem;
        margin-bottom: 1.5rem;
    }
    .stChatMessage {
        border-radius: 14px;
        padding: 0.4rem 0.2rem;
    }
    div[data-testid="stChatInput"] textarea {
        border-radius: 12px !important;
    }
    .status-pill {
        display: inline-block;
        padding: 2px 10px;
        border-radius: 999px;
        background: rgba(34,197,94,0.15);
        color: #4ade80;
        font-size: 0.75rem;
        font-weight: 600;
        border: 1px solid rgba(74,222,128,0.35);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown("<div class='main-title'>🤖 MCP-Powered Assistant</div>", unsafe_allow_html=True)
st.markdown(
    "<div class='subtitle'>Groq · LangGraph · MCP tools (calculator &amp; search)</div>",
    unsafe_allow_html=True,
)

# ------------------------------------------------------------------
# State definition
# ------------------------------------------------------------------
class State(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]

SYSTEM_PROMPT = """You are a helpful, friendly assistant.
You help the user answer questions, using tools (like the calculator) when needed.
Keep your tone warm and welcoming.
End every reply by asking: 'Do you want to know something else?'"""

# ------------------------------------------------------------------
# Build the graph once per session (cached resource)
# ------------------------------------------------------------------
@st.cache_resource(show_spinner=False)
def get_event_loop():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    return loop

async def _build_graph():
    llm = ChatGroq(
        groq_api_key=os.getenv("GROQ_API_KEY"),
        model="openai/gpt-oss-120b",
        temperature=0.5,
        max_tokens=500,
    )

    client = MultiServerMCPClient(
        {
            "calulator tool": {
                "command": "uv",
                "args": [
                    "run", "--with", "fastmcp", "fastmcp", "run",
                    "C:\\Users\\yash\\OneDrive\\Desktop\\mcp_project\\calculator.py",
                ],
                "env": {},
                "transport": "stdio",
            }
        }
    )

    tools = await client.get_tools()
    llm_with_tools = llm.bind_tools(tools)
    tool_node = ToolNode(tools)

    async def chat(state: State):
        response = await llm_with_tools.ainvoke(
            [SystemMessage(content=SYSTEM_PROMPT), *state["messages"]]
        )
        return {"messages": [response]}

    q = StateGraph(State)
    q.add_node("chat", chat)
    q.add_node("tools", tool_node)
    q.add_edge(START, "chat")
    q.add_conditional_edges("chat", tools_condition)
    q.add_edge("tools", "chat")
    return q.compile()

@st.cache_resource(show_spinner=False)
def get_graph():
    loop = get_event_loop()
    return loop.run_until_complete(_build_graph())

def run_async(coro):
    loop = get_event_loop()
    return loop.run_until_complete(coro)

# ------------------------------------------------------------------
# Sidebar
# ------------------------------------------------------------------
with st.sidebar:
    st.markdown("### ⚙️ Status")
    if os.getenv("GROQ_API_KEY"):
        st.markdown("<span class='status-pill'>GROQ_API_KEY loaded</span>", unsafe_allow_html=True)
    else:
        st.error("GROQ_API_KEY not found in .env")

    st.markdown("### 🧰 Tools available")
    st.markdown("- ➕ Calculator (add / sub / multiply / divide)")
    st.markdown("- 🔎 Web search (if configured)")

    st.divider()
    if st.button("🗑️ Clear chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

# ------------------------------------------------------------------
# Chat history
# ------------------------------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    role = "user" if isinstance(msg, HumanMessage) else "assistant"
    avatar = "🧑" if role == "user" else "🤖"
    with st.chat_message(role, avatar=avatar):
        st.markdown(msg.content)

# ------------------------------------------------------------------
# Chat input
# ------------------------------------------------------------------
user_input = st.chat_input("Ask me anything — I can even do calculations…")

if user_input:
    st.session_state.messages.append(HumanMessage(content=user_input))
    with st.chat_message("user", avatar="🧑"):
        st.markdown(user_input)

    with st.chat_message("assistant", avatar="🤖"):
        placeholder = st.empty()
        full_text = ""
        try:
            graph = get_graph()

            async def stream_response():
                nonlocal_text = ""
                async for msg, metadata in graph.astream(
                    {"messages": st.session_state.messages},
                    stream_mode="messages",
                ):
                    if getattr(msg, "content", None):
                        yield msg.content

            async def collect():
                text = ""
                async for chunk in stream_response():
                    text += chunk
                    placeholder.markdown(text + "▌")
                return text

            full_text = run_async(collect())
            placeholder.markdown(full_text)
        except Exception as e:
            full_text = f"⚠️ Something went wrong: {e}"
            placeholder.markdown(full_text)

    st.session_state.messages.append(AIMessage(content=full_text))