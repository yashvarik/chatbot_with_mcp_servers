from fastmcp import FastMCP
from tavily import TavilyClient
import os

tavily=TavilyClient(
    api_key=os.getenv("TAVILY_API_KEY")

)


mcp=FastMCP('calulator tool')

@mcp.tool()
def calulator(first:float,sec:float,operation:str):
    """ This is the calulator tool.
    use it for when user ask for the basic arthimatic calculation.
    the availabel operations are:
    -add
    -sub
    -multiply
    -divison"""
    if operation == 'add':
        result= first + sec
        return result
    elif operation == 'sub':
        result = first - sec
        return result
    elif operation == 'multiply':
        result = first * sec
        return result
    elif operation == 'divison':
        result = first / sec
        return result

    else:
        return print(f"{operation} is not availbale")

@mcp.tool()
def tavily_search(query: str) -> str:
    """Search the web using Tavily."""

    response = tavily.search(
        query=query,
        search_depth="basic",
        max_results=1
    )

    output = []

    for result in response["results"]:
        output.append(
            f"""
Title: {result.get("title", "")}

URL: {result.get("url", "")}

Content: {result.get("content", "")}

Score: {result.get("score", "")}
"""
        )

    return " ".join(output)




if __name__ == '__main__':
    mcp.run(transport="http")