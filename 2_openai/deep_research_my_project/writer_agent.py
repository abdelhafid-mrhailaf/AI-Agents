from pydantic import BaseModel, Field
from agents import Agent, Runner
from dotenv import load_dotenv


load_dotenv(override=True)

INSTRUCTIONS = (
    "You are a senior researcher tasked with writing a cohesive report for a research query. "
    "You will be provided with the original query, and some initial research done by a research assistant.\n"
    "You should first come up with an outline for the report that describes the structure and "
    "flow of the report. Then, generate the report and return that as your final output.\n"
    "The final output should be in markdown format, and it should be lengthy and detailed. Aim "
    "for 5-10 pages of content, at least 1000 words."
)


class ReportData(BaseModel):
    short_summary: str = Field(description="A short 2-3 sentence summary of the findings.")

    markdown_report: str = Field(description="The final report")

    follow_up_questions: list[str] = Field(description="Suggested topics to research further")


writer_agent = Agent(
    name="WriterAgent",
    instructions=INSTRUCTIONS,
    model="gpt-4o-mini",
    output_type=ReportData,
)

class ReportDataValidator(BaseModel):
    is_completed: bool = Field(description="When it is completed it is gonna return true")
    accuracy_score: str = Field(description="The score from 0 to 10, when the score is above 8 the search is acceptable")
    

VALIDATOR_INSTRUCTIONS = (
    "You are a senior reviewer responsible for validating a research report produced by another agent. "
    "You will receive the original query, any assistant notes, and the final report.\n"
    "Your task is to assess the report’s accuracy, completeness, coherence, and alignment with the query’s intent. "
    "Identify factual errors, logical gaps, or unsupported claims.\n"
    "After your evaluation, you must output a JSON object that matches the following schema:\n\n"
    "{\n"
    '  "is_completed": bool,  // True if validation is done\n'
    '  "accuracy_score": str  // A score from 0 to 10, where scores above 8 indicate acceptable accuracy\n'
    "}\n\n"
    "Before generating the JSON, write a concise markdown evaluation that includes: "
    "1) Summary of purpose, "
    "2) Strengths, "
    "3) Weaknesses, "
    "4) Suggestions for improvement, "
    "and 5) Overall verdict.\n"
    "Be objective, precise, and professional. Focus on factual accuracy and logical consistency. "
    "Keep your evaluation between 600–1000 words. "
    "Finally, append the JSON object in a code block as your output."
)

writer_validator_agent = Agent(
    name = "Writer Validator Agent",
    instructions = VALIDATOR_INSTRUCTIONS,
    model = "gpt-4o-mini",
    output_type = ReportDataValidator
)

async def perform_write(query: str, research: list[str], history=""):
    researches = " ".join(research)
    result = await Runner.run(
        writer_agent,
        f"Query: {query}, research: {researches}, the history in the case it was not validated throw the validator: {history}"
    )
    return result.final_output_as(ReportData)


async def evaluate_raport(query: str, raport: ReportData):
    "the original query, any assistant notes, and the final report."
    assistantNote = raport.short_summary
    finalReport = raport.markdown_report

    evaluation = await Runner.run(
        writer_validator_agent,
        f"This is the Query: {query}, assistant Note: {assistantNote}, final Report: {finalReport}"
    )
    return evaluation.final_output_as(ReportDataValidator)


async def report_writer(query: str, research: list[str]):
    raport = await perform_write(query, research)
    raportEvaluation = await evaluate_raport(query, raport)
    history = ""
    EXTEND_LIMIT_OF_CALL = 0
    raportEvaluation.is_completed = False
    while (not raportEvaluation.is_completed  and (EXTEND_LIMIT_OF_CALL < 10)) or (int(raportEvaluation.accuracy_score) < 8 and (EXTEND_LIMIT_OF_CALL < 10)):
        print("Inside the loop")
        raport = await perform_write(query, research)
        raportEvaluation = await evaluate_raport(query, raport)
        EXTEND_LIMIT_OF_CALL += 1
    return raport
