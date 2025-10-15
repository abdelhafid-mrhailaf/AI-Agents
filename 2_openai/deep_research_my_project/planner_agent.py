from pydantic import BaseModel, Field
from agents import Agent, WebSearchTool, trace, Runner, gen_trace_id, function_tool
from agents.model_settings import ModelSettings


HOW_MANY_SEARCHES = 3


INSTRUCTIONS_PLANNER = f"You are a helpful research assistant. Given a query, come up with a set of web searches \
to perform to best answer the query. Output {HOW_MANY_SEARCHES} terms to query for."

class WebSearchItem(BaseModel):
    reason: str = Field(description="Your reasoning for why this search is important to the query.")
    query: str = Field(description="The search term to use for the web search.")

class WebSearchItemList(BaseModel):
    searches: list[WebSearchItem] = Field(description="A list of web searches to perform to best answer the query.")


class EvaluateWebSearchItem(BaseModel):
    is_accepted: bool
    reason: str =  Field(description="why the suggestion of the AI is accepted or not")


planner_agent = Agent(
    name="PlannerAgent",
    instructions=INSTRUCTIONS_PLANNER,
    model="gpt-4o-mini",
    output_type=WebSearchItemList
)


INSTRUCTIONS_VALIDATOR = "You are an evaluator. Given a query and a WebSearchItem \
                (with its reasoning and query), decide if the search suggestion is good.\
                Return an EvaluateWebSearchItem object with fields: is_accepted (bool) \
                and reason (why the suggestion is accepted or not). \
                Use the query to judge how relevant and useful the search is."


INSTRUCTIONS_REGENERATOR = "You are a regenerator. Given a user query,\
                a rejected WebSearchItem, and validator feedback, generate a new, more relevant\
                and precise search query that fixes the issues noted. Focus on key entities, context, and clarity. Output a WebSearchItem with: reason\
                (why this new search is important to the query) and query (the improved search term to use)."


regenerator_agent = Agent(
    name="RegeneratorAgent",
    instructions=INSTRUCTIONS_REGENERATOR,
    model="gpt-4o-mini",
    output_type=WebSearchItem
)

evaluator_agent = Agent(
    name="EvaluatorAgent",
    instructions=INSTRUCTIONS_VALIDATOR,
    model="gpt-4o-mini",
    output_type=EvaluateWebSearchItem
)



async def perform_plan(query: str) -> WebSearchItemList:
    print("Planning searches...")
    result = await Runner.run(
        planner_agent,
        f"Query: {query}",
    )
    #print(f"Will perform {len(result.final_output.searches)} searches")
    return result.final_output_as(WebSearchItemList)

async def evaluate_websearch_item(query: str, webSearchItem: WebSearchItem) -> EvaluateWebSearchItem:
    result_evaluation = await Runner.run(
        evaluator_agent,
        f"Query: {query}, WebSearchItem: {webSearchItem}"
    )
    return result_evaluation.final_output_as(EvaluateWebSearchItem)

async def regenerator_websearch_item(query: str, rejectedItem: WebSearchItem, evaluationObject: EvaluateWebSearchItem) -> WebSearchItem:
    print("generating a new Item")
    newItem = await Runner.run(
        regenerator_agent,
        f"Query: {query}, Rejected item: {rejectedItem}, validator feedback: {evaluationObject}"
        )
    print(f"Regeneration of the prompt for the keyword result: {rejectedItem.query}")
    return newItem.final_output_as(WebSearchItem)

async def validate_websearch_item(query: str, webSearchItem: WebSearchItem) -> WebSearchItem:
    resultEvaluation = await evaluate_websearch_item(query, webSearchItem)
    EXTEND_LIMIT_OF_CALL = 0
    while not resultEvaluation.is_accepted and EXTEND_LIMIT_OF_CALL != 10:
        webSearchItem = await regenerator_websearch_item(query, webSearchItem, resultEvaluation)
        resultEvaluation = await evaluate_websearch_item(query, webSearchItem)
        EXTEND_LIMIT_OF_CALL += 1
    if EXTEND_LIMIT_OF_CALL >= 10:
        raise RuntimeError("Loop exceeded allowed iteration count (10)")
    return webSearchItem


async def validate_websearch_list(query: str, webSearchItemlist: WebSearchItemList) -> WebSearchItemList:
    validatedWebSearchItemList = []
    for item in webSearchItemlist.searches:
        validatedItem = await validate_websearch_item(query, item)
        validatedWebSearchItemList.append(validatedItem)
    return WebSearchItemList(searches=validatedWebSearchItemList)  

