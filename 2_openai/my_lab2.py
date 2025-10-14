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


    async def agent_for_sales_email():
        instruction_email = """
            You are a senior B2B SaaS sales copywriter.

            Goal: Write one short, natural cold email to a CEO offering a SaaS that manages company stocks (use `stock_context`: "inventory" or "equity"). Be concrete, respectful, and human.

            Input (JSON):
            {
            "ceo_first_name": "...",
            "company_name": "...",
            "industry": "...",
            "stock_context": "inventory|equity",
            "pain_point": "...",
            "value_prop": "...",
            "proof_point": "...",          // optional, credible & brief
            "cta_times": ["...", "..."],   // optional two time windows
            "sender_name": "...",
            "sender_title": "...",
            "sender_company": "...",
            "sender_url": "..."            // optional
            }

            Instructions:
            - 75–110 words, 3 short paragraphs (2–3 sentences each).
            - Structure: greeting → problem & impact → how we help + proof → one specific CTA.
            - Use plain language and contractions; vary sentence length; sound human.
            - No subject line. No bullets. No emojis. No invented numbers.
            - Forbidden: "I hope this finds you well", "I’m reaching out", "synergy", "cutting‑edge", "utilize", "As an AI".
            - If a field is missing, don’t invent it; write around it.
            - CTA: propose a 15‑minute chat; include `cta_times` if provided.

            Output:
            Return only the email body as plain text:
            Hi {{ceo_first_name}},

            [body]

            Best,
            {{sender_name}}
            {{sender_title}} — {{sender_company}}
            {{sender_url}}
            """.strip()
        instruction_subject = """
            You are a B2B subject‑line optimizer for executive cold email.

            Input (JSON):
            {
            "email_text": "...",          // plain text from Prompt 1
            "company_name": "...",        // optional
            "ceo_first_name": "..."       // optional
            }

            Instructions:
            - Reflect the core benefit/problem in the email; be honest, not clickbait.
            - ≤ 45 characters OR ≤ 7 words (use the stricter limit).
            - If personalization is possible, include EITHER {{company_name}} OR {{ceo_first_name}}—not both.
            - Sentence case. No “Re:”/“Fwd:”, emojis, ALL CAPS, exclamation marks, or trailing period.
            - Avoid spam terms: free, discount, offer, trial, limited time, guarantee.

            Output:
            Return only the subject line as plain text; nothing else.
            """.strip()
        instruction_verification = """
            You are QA for email–subject pairs.

            Input (JSON):
            {
            "email_text": "...",
            "subject_line": "..."
            }

            Checks:
            1) Alignment: subject truthfully reflects the email’s main value/problem.
            2) Clarity & length: email 65–130 words; exactly one CTA; concrete next step.
            3) Human tone: natural greeting/sign‑off, contractions, no hype/jargon.
            4) Mechanics: clean grammar/spelling; no AI/self‑disclosure; no invented stats.
            5) Subject quality: ≤45 chars/≤7 words; no "Re:"/"Fwd:"/"!"/emojis; avoids spam terms.

            Output (JSON only):
            {
            "pass": true|false,
            "score": 0-100,
            "issues": ["..."],                 // empty if pass and score ≥ 80
            "suggested_subject": "...",        // include only if subject weak or fails
            "suggested_email": "...",          // include only if email fails; minimal edits
            "notes": "one concise sentence"
            }
            """.strip()

        #Agents
        agent_email_writer = Agent(name="Email Writer", instructions=instruction_email, model="gpt-4o-mini")
        agent_subject_writer = Agent(name="Subject Writer", instructions=instruction_subject, model="gpt-4o-mini")
        agent_instruction_writer = Agent(name="Instruction Verfication Writer", instructions=instruction_verification, model="gpt-4o-mini")

        #email_result = Runner.run_sync(agent_email_writer, "Write a SaaS Email for customers")
        with trace("Call of the Agents"):
            results_email = await asyncio.gather(
                Runner.run(agent_email_writer, "Write a professional email")
            )
            email_text = results_email[0].final_output 
            print(email_text)

            result_subject = await asyncio.gather(
                Runner.run(agent_subject_writer, f"Write a subject for the folliwing email input json:  email_text:" + email_text)
            )
            subject = result_subject[0].final_output
            print(subject)

            verification = await asyncio.gather(
                Runner.run(agent_instruction_writer, f"email : " + email_text + ", subject :" + subject) 
            )
            verification_text = verification[0].final_output
            print(verification_text)
        
sra = SRA
asyncio.run(sra.agent_for_sales_email())