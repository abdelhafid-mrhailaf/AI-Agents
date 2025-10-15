from pydantic import BaseModel, Field
from agents import Agent, WebSearchTool, trace, Runner, gen_trace_id, function_tool
from agents.model_settings import ModelSettings


HOW_MANY_SEARCHES = 3


INSTRUCTIONS_PLANNER = f"You are a helpful research assistant. Given a query, come up with a set of web searches \
to perform to best answer the query. Output {HOW_MANY_SEARCHES} terms to query for."

class WebSearchItem(BaseModel):
    reason: str = Field(description="Your reasoning for why this search is important to the query.")
    query: str = Field(description="The search term to use for the web search.")

class WebSeachItemList(BaseModel):
    searches: list[WebSearchItem] = Field(description="A list of web searches to perform to best answer the query.")


class EvaluateWebSearchItem(BaseModel):
    is_accepted: bool
    reason: Field(description="why the sugession of the AI is accepted or not")


planner_agent = Agent(
    name="PlannerAgent",
    instruction=INSTRUCTIONS_PLANNER,
    model="gpt-4o-mini",
    output_type=WebSeachItemList
)


INSTRUCTIONS_VALIDATOR = "You are an evaluator. Given a query and a WebSearchItem \
                (with its reasoning and query), decide if the search suggestion is good.\
                Return an EvaluateWebSearchItem object with fields: is_accepted (bool) \
                and reason (why the suggestion is accepted or not). \
                Use the query to judge how relevant and useful the search is."


INSTRCUTRION_REGENERATOR = "You are a regenerator. Given a user query,\
                a rejected WebSearchItem, and validator feedback, generate a new, more relevant\
                and precise search query that fixes the issues noted. Focus on key entities, context, and clarity. Output a WebSearchItem with: reason\
                (why this new search is important to the query) and query (the improved search term to use)."


regenerator_agent = Agent(
    name="RegeneratorAgent",
    instructions=INSTRCUTRION_REGENERATOR,
    model="gpt-4o-mini",
    output_type=WebSearchItem
)

evaluator_agent = Agent(
    name="EvaluatorAgent",
    instructions=INSTRUCTIONS_VALIDATOR,
    model="gpt-4o-mini",
    output_type=EvaluateWebSearchItem
)




async def perform_search(query: str) -> WebSeachItemList:
    with trace("Search"):
        print("Planning searches...")
        result = await Runner.run(
            planner_agent,
            f"Query: {query}",
        )

async def validate_websearch_item(webSearchItem: WebSearchItem) -> EvaluateWebSearchItem:
    
    EXTEND_LIMIT_OF_CALL = 0
    while not webSearchItem.is_accepted and EXTEND_LIMIT_OF_CALL != 10: