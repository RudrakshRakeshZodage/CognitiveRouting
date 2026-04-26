import os
import json
from typing import TypedDict, Annotated, List
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END
from pydantic import BaseModel, Field

load_dotenv()

# --- Phase 2: Mock Tool ---

@tool
def mock_searxng_search(query: str):
    """Returns hardcoded, recent news headlines based on keywords."""
    query = query.lower()
    if "crypto" in query or "bitcoin" in query:
        return "Bitcoin hits new all-time high amid regulatory ETF approvals. Ethereum scaling solutions gain traction."
    elif "ai" in query or "model" in query:
        return "OpenAI announces GPT-5 early alpha testing. NVIDIA stock surges as AI chip demand remains insatiable."
    elif "market" in query or "interest" in query:
        return "Fed maintains interest rates; inflation shows signs of cooling. Stock market hits record highs on earnings growth."
    elif "privacy" in query or "tech" in query:
        return "New antitrust lawsuits filed against major tech monopolies. European regulators introduce stricter data privacy laws."
    else:
        return "Global markets show mixed results today. Tech sector continues to lead innovation in various fields."

# --- Phase 2: LangGraph Orchestrator ---

class GraphState(TypedDict):
    search_results: str
    post_content: str
    critique: str
    iterations: int

class PostOutput(BaseModel):
    bot_id: str = Field(description="The ID of the bot generating the post")
    topic: str = Field(description="The topic the bot decided to post about")
    post_content: str = Field(description="The 280-character post content")

def decide_search(state: GraphState):
    """Node 1: Decide Search. LLM decides topic and search query."""
    llm = ChatOpenAI(model="gpt-4o", temperature=0.7)
    
    prompt = f"""
    You are {state['bot_id']}. Your persona is: {state['persona']}
    Decide what topic you want to post about today based on your interests.
    Provide a search query to get more context on this topic.
    
    Respond in JSON format:
    {{
        "topic": "...",
        "search_query": "..."
    }}
    """
    
    response = llm.invoke([HumanMessage(content=prompt)])
    # In a real scenario, use structured output. For simplicity here:
    data = json.loads(response.content.strip("```json").strip("```"))
    
    return {
        "topic": data["topic"],
        "search_query": data["search_query"]
    }

def web_search(state: GraphState):
    """Node 2: Web Search. Executes mock tool."""
    results = mock_searxng_search.invoke(state["search_query"])
    return {"search_results": results}

def draft_post(state: GraphState):
    """Node 3: Draft Post. Generates opinionated JSON output."""
    # Use structured output for strict JSON
    llm = ChatOpenAI(model="gpt-4o", temperature=0.8).with_structured_output(PostOutput)
    
    system_prompt = f"You are {state['bot_id']}. Your persona is: {state['persona']}"
    content_prompt = f"""
    Based on the following search context: {state['search_results']}
    Draft a highly opinionated, 280-character post about {state['topic']}.
    Make sure it aligns perfectly with your persona.
    """
    
    response = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=content_prompt)
    ])
    
    return {
        "post_content": response.post_content,
        "iterations": state.get("iterations", 0) + 1
    }

def critique_post(state: GraphState):
    """Node 4: Critique Post. Self-correction for maximum persona impact."""
    llm = ChatOpenAI(model="gpt-4o", temperature=0.5)
    
    prompt = f"""
    You are a professional editor for {state['bot_id']}. 
    Persona: {state['persona']}
    
    Current Draft: "{state['post_content']}"
    
    CRITIQUE CRITERIA:
    1. Does it sound like an AI? (e.g., "In the rapidly evolving landscape...") - IF YES, CRITICIZE.
    2. Is it opinionated enough for this persona?
    3. Is it under 280 characters?
    
    If it's perfect, respond with 'APPROVED'. 
    If not, provide specific instructions to make it more raw, aggressive, or aligned with the persona.
    """
    
    response = llm.invoke([HumanMessage(content=prompt)])
    return {"critique": response.content}

def should_continue(state: GraphState):
    """Conditional edge to decide if we need another draft."""
    if "APPROVED" in state["critique"] or state["iterations"] >= 2:
        return "end"
    return "rewrite"

# Build Graph
workflow = StateGraph(GraphState)

workflow.add_node("decide_search", decide_search)
workflow.add_node("web_search", web_search)
workflow.add_node("draft_post", draft_post)
workflow.add_node("critique_post", critique_post)

workflow.set_entry_point("decide_search")
workflow.add_edge("decide_search", "web_search")
workflow.add_edge("web_search", "draft_post")
workflow.add_edge("draft_post", "critique_post")

workflow.add_conditional_edges(
    "critique_post",
    should_continue,
    {
        "rewrite": "draft_post",
        "end": END
    }
)

app = workflow.compile()

def run_content_engine(bot_id: str, persona: str):
    initial_state = {
        "bot_id": bot_id,
        "persona": persona,
        "topic": "",
        "search_query": "",
        "search_results": "",
        "post_content": "",
        "critique": "",
        "iterations": 0
    }
    final_output = app.invoke(initial_state)
    return {
        "bot_id": final_output["bot_id"],
        "topic": final_output["topic"],
        "post_content": final_output["post_content"],
        "critique": final_output.get("critique", "N/A"),
        "iterations": final_output.get("iterations", 0)
    }

if __name__ == "__main__":
    bot_persona = "I believe AI and crypto will solve all human problems. I am highly optimistic about technology, Elon Musk, and space exploration. I dismiss regulatory concerns."
    result = run_content_engine("Bot A (Tech Maximalist)", bot_persona)
    print(json.dumps(result, indent=2))
