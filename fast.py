from contextlib import asynccontextmanager

from fastapi import FastAPI
from pydantic import BaseModel
from langchain_core.messages import HumanMessage, AIMessage

from prac import build_graph   # your file with build_graph() in it


# ------------------------------------------------------------------
# Build the graph ONCE when the server starts (not on every request)
# ------------------------------------------------------------------
graph = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global graph
    graph = await build_graph()   # MCP client + graph built once at startup
    yield
    # (optional) cleanup code here if MultiServerMCPClient needs closing


app = FastAPI(lifespan=lifespan)


class Query(BaseModel):
    query: str


@app.post("/predict")
async def predict(data: Query):
    try:
        result = await graph.ainvoke(
            {"messages": [HumanMessage(content=data.query)]}
        )

        # last message in the returned state is the bot's final reply
        last_msg = result["messages"][-1]
        reply = last_msg.content if isinstance(last_msg, AIMessage) else str(last_msg.content)
        return {"response": reply}
    except Exception as e:
                        print(f"{e}")
                        return None
        
    