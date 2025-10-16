from agents import Agent, WebSearchTool, ModelSettings
from dotenv import load_dotenv

load_dotenv(override=True)
VALIDATOR_INSTRUCTION = "You are a validation assistant. Given a search term and a generated summary, your task is to verify whether the summary adheres to the INSTRUCTIONS. The summary should be 2–3 paragraphs, under 300 words, concise, and focused only on the essential points from the web search results. Writing should be compact, possibly using fragments or short phrases, and free of commentary, filler, or unnecessary detail. The output must contain only the summary itself, no explanations or formatting. You will assess compliance and quality. If the summary violates any rule, briefly describe the issues. Always output your evaluation in three parts: Compliance (Yes/No), Issues (if any), and Quality Score (0–10). Be objective, professional, and concise in your assessment."


search_agent_validator = Agent(
    name="Search agent validator",
    instructions = VALIDATOR_INSTRUCTION,
    model = "gpt-4o-mini"
)

search_validator_tool = search_agent_validator.as_tool(tool_name="search_validator", tool_description="Validates whether a generated web search summary complies with the defined formatting and content INSTRUCTIONS. "
    "It checks that the summary is 2–3 paragraphs, under 300 words, concise, and focused only on key findings without commentary or filler. "
    "The tool outputs an objective evaluation including compliance status (Yes/No), a brief description of any issues, "
    "and a quality score from 0–10 based on clarity, conciseness, and adherence to the guidelines.")


INSTRUCTIONS = (
    "You are a research assistant. Given a search term, you search the web for that term and "
    "produce a concise summary of the results. The summary must 2-3 paragraphs and less than 300 "
    "words. Capture the main points. Write succintly, no need to have complete sentences or good "
    "grammar. This will be consumed by someone synthesizing a report, so its vital you capture the "
    "essence and ignore any fluff. Do not include any additional commentary other than the summary itself."
    "After producing the summary (and just after producing the summary), always use the search_validator tool to check compliance with the INSTRUCTIONS before finalizing your answer."
)

search_agent = Agent(
    name="Search agent",
    instructions=INSTRUCTIONS,
    tools=[WebSearchTool(search_context_size="low"), search_validator_tool],
    model="gpt-4o-mini",
    model_settings=ModelSettings(tool_choice="required"),
)