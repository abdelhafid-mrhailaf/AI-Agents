import os
from typing import Dict


import sendgrid
from sendgrid.helpers.mail import Email, Mail, Content, To
from agents import Agent, function_tool, Runner

from dotenv import load_dotenv  # pyright: ignore[reportMissingImports]
from pydantic import BaseModel
# 
load_dotenv(override=True)

class EmailContent(BaseModel):
    subject: str
    html_body: str


def send_email(subject: str, html_body: str) -> Dict[str, str]:
    """ Send an email with the given subject and HTML body """
    sg = sendgrid.SendGridAPIClient(api_key=os.environ.get('SENDGRID_API_KEY'))
    from_email = Email("abdelhafid.mrhailaf@stud.h-da.de") # put your verified sender here
    to_email = To("mrhailaf.abdelhafid@gmail.com") # put your recipient here
    content = Content("text/html", html_body)
    mail = Mail(from_email, to_email, subject, content).get()
    response = sg.client.mail.send.post(request_body=mail)
    print("Email response", response.status_code)
    return {"status": "success"}



INSTRUCTIONS = """
You are able to send a nicely formatted HTML email based on a detailed report.
You will be provided with a detailed report. You should format it into a clean, well-presented HTML email
with an appropriate subject line.

Do NOT send the email yourself.
Instead, return an EmailContent object containing:
- subject: a short, clear subject line.
- html_body: the full formatted HTML email body.
"""

email_agent = Agent(
    name="Email agent",
    instructions=INSTRUCTIONS,
    model="gpt-4o-mini",
    output_type = EmailContent
)

async def send_email_report(report):
    print("Writing email...")
    result = await Runner.run(email_agent, report)
    email_data = result.final_output  # already an EmailContent object
    send_email(email_data.subject, email_data.html_body)
    print("Email sent")
    return report

