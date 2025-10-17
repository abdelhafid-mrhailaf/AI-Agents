import search_agent
import planner_agent 
import writer_agent 
import email_agent 
from agents import gen_trace_id, trace

class ResearchManager:
    async def run(self, query: str):
        """Run the deep search proces, yielding the status updates and the final report"""
        trace_id = gen_trace_id()
        with trace("Research trace", trace_id=trace_id):
            print("Starting research....")
            search_plan = await planner_agent.plan_deep_search(query)
            search_result = await search_agent.perform_web_search(search_plan)
            #with open("search.md", "r") as file:
            #    text = file.read()
            #report = text
            report = await writer_agent.report_writer(query ,search_result)
            print(report)
            await email_agent.send_email_report(report.markdown_report)


