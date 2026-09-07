from langchain_groq import ChatGroq
from langgraph.graph import StateGraph,START,END,add_messages
from langchain_core.messages import HumanMessage,AIMessage,SystemMessage,BaseMessage
from langchain_core.prompts import ChatPromptTemplate
from typing_extensions import TypedDict,Annotated,List,Literal
import os,asyncio
from langgraph.prebuilt import ToolNode,tools_condition
from langchain_mcp_adapters.client import MultiServerMCPClient
from dotenv import load_dotenv
load_dotenv()

llm=ChatGroq(
    groq_api_key=os.getenv("GROQ_API_KEY"),
    model="openai/gpt-oss-120b",
    temperature=0.5,
    max_tokens=200

    
)



class State(TypedDict):
    messages:Annotated[list[BaseMessage],add_messages]


async def build_graph():
    client=MultiServerMCPClient(
        {
      "calulator tool": {
      "command": "uv",
      "args": [
        "run",
        "--with",
        "fastmcp",
        "fastmcp",
        "run",
        "C:\\Users\\yash\\OneDrive\\Desktop\\mcp_project\\calculator.py"
      ],
      "env": {},
      "transport": "stdio",
            }
        }
        
    )
    tools= await client.get_tools()


    llm_with_tools=llm.bind_tools(tools)
    tool_node=ToolNode(tools)

    
    


    async def chat(state:State):
        messages=state['messages'][-1].content
        response=await llm_with_tools.ainvoke([
            SystemMessage(
                content=(
                    """ You are the helping bot.
                    you help the user to answer the questions.
                    make sure your tone is welcoming and friendly.
                    End the ask
                    'Do you want to know simething else?'"""
                )
            ),
            HumanMessage(content=(messages))
        ])
        return {'messages':[response]}

    q=StateGraph(State)
    q.add_node('chat',chat)
    q.add_node('tools',tool_node)
    q.add_edge(START,'chat')
    q.add_conditional_edges('chat',tools_condition)
    q.add_edge('tools','chat')
    
    return q.compile()



async def main():
    graph = await build_graph()
    async for msg, metadata in graph.astream(
        {"messages": [HumanMessage(content="what is the price of bmw in mumbai")]},
        stream_mode="messages",
    ):
        if msg.content:
            print(msg.content, end="", flush=True)

if __name__=="__main__":
    asyncio.run(main())