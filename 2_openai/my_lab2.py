from dotenv import load_dotenv
from agents import Agent, Runner, trace, function_tool
from httpx import request
from openai.types.responses import ResponseTextDeltaEvent
from typing import Dict
import sendgrid
import os
from sendgrid.helpers.mail import Mail, Email, To, Content
import asyncio

load_dotenv(override=True)


class SRA:
    def send_email(self, subject, email_text):
        sg = sendgrid.SendGridAPIClient(api_key=os.environ.get('SENDGRID_API_KEY'))
        from_email = Email("abdelhafid.mrhailaf@stud.h-da.de")
        to_email = To("mrhailaf.abdelhafid@gmail.com")
        content = Content("text/html", email_text)
        mail = Mail(from_email, to_email, subject, content).get()
        response = sg.client.mail.send.post(request_body=mail)
        print(response.status_code)


    def agent_for_sales_email():
        instruction_email = "You are gonna take the task of being a Sale Agent for SaaS that is responsible for sending the email to the CEO and offering a Software As A Service for the management of the Stocks in the company\
                        For this role you should be precise and you should write an email that is short and it should have the format of human and not look like an AI Email"
        instruction_subject = "You are an Agent that is responsible for receiving an Email and trying to make the best Subject so that the email could be attractive and could be clickable by the customer. i mean you should write a subject more attractive \
                                and pass to the content of the email"
        instruction_verification = "You are an Agent that gets and Email and a Subject and Verify that the pass with each other. and looks a human readable email that is precise and clean"

        agent_email_writer = Agent(name="Email Writer", instructions=instruction_email, model="gpt-4o-mini")
        
        #agent_subject_writer = Agent(name="Subject Writer", instruction=instruction_subject, model="gpt-4o-mini")
        #agent_instruction_writer = Agent(name="Instruction Verfication Writer", instruction=instruction_verification, model="gpt-4o-mini")


        email_result = Runner.run_sync(agent_email_writer, "Write a SaaS Email for customers")
        return agent_email_writer
sra = SRA
obj = sra.agent_for_sales_email()
print(obj)
