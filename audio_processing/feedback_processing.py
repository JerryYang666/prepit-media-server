# Copyright (c) 2024.
# -*-coding:utf-8 -*-
"""
@file: feedback_processing.py
@author: Jerry(Ruihuang)Yang
@email: rxy216@case.edu
@time: 6/29/24 22:53
"""
import json
import os
from AgentPromptHandler import AgentPromptHandler
from FeedbackStorageHandler import FeedbackStorageHandler
from openai import OpenAI
from anthropic import Anthropic

PROCESSED_MEDIA_DIR = "./processed_media"
FEEDBACK_SYSTEM_PROMPT_TEMPLATE = """
You are a experienced Management Consultant at a top-tier consulting firm. You just conducted a case interview with a candidate. You need to write a feedback for the candidate.
Your feedback should be structured, and can include the following aspects (you can also add more aspects, or remove some aspects if you think they are not relevant):
1. if the candidate's response was structured and logical
2. if the candidate asked the right questions
3. if the candidate's math was correct
4. if the candidate's communication was clear
5. if the candidate's overall performance was good
6. if the candidate's response was creative (especially for brainstorming questions)
7. if the candidate's final recommendation was good
Your feedback should be constructive and provide actionable advice for the candidate to improve.
Your feedback should be around 200 words.
Your feedback should NOT consider spelling or grammar mistakes, as the candidate's response was verbal and the text here is transcribed from the audio.
"""
FEEDBACK_USER_PROMPT_TEMPLATE = """
Here is the case background: {case_background}
You are writing feedback for this part of the interview: {feedback_step_name}
This step was conducted based on the following instructions: {feedback_step_instructions}
And this is the information (might also include best responses) that the was provided to the interviewer by the case book: {feedback_step_info}
Here is the interview transcript between the interviewer and the candidate:
{feedback_step_transcript}
Please write feedback for the candidate based on the information above. You should directly start the feedback and should not include any extra sentence at the start or the end of your response.
"""
FEEDBACK_AI_PROVIDER = "openai"
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
anthropic_client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
agent_prompt_handler = AgentPromptHandler()
feedback_storage_handler = FeedbackStorageHandler()


def parse_messages_file(messages_file_path: str) -> str:
    """
    Parse the messages file and return the messages for AI to provide feedback
    :param messages_file_path:
    :return: structured string of messages
    """
    with open(messages_file_path, 'r') as file:
        messages = json.load(file)
    result = ""
    for _, value in messages.items():
        role = "Interviewer: " if value['role'] == 'assistant' else 'Candidate: '
        result += f"{role}{value['content']}\n"
    print("msg_parse: ", result)
    return result


def gather_feedback_prompts(agent_id: str, step_id: int) -> dict:
    """
    Gather feedback prompts for AI to provide feedback
    :param agent_id: agent id
    :param step_id: step id
    :return: feedback prompts
    """
    current_step_prompt = agent_prompt_handler.get_agent_prompt(agent_id, str(step_id))
    current_step_prompt = json.loads(current_step_prompt)
    feedback_step_name = current_step_prompt['title']
    feedback_step_instructions = current_step_prompt['instruction']
    feedback_step_info = current_step_prompt['information']
    case_background_step = agent_prompt_handler.get_agent_prompt(agent_id, "0")
    case_background_step = json.loads(case_background_step)
    case_background = case_background_step['information']
    return {
        "case_background": case_background,
        "feedback_step_name": feedback_step_name,
        "feedback_step_instructions": feedback_step_instructions,
        "feedback_step_info": feedback_step_info
    }


def openai_generate_feedback(template_contents: dict, formatted_messages: str) -> str:
    """
    Generate feedback using OpenAI
    :param template_contents: feedback prompts
    :param formatted_messages: formatted messages
    :return: feedback
    """
    template_contents['feedback_step_transcript'] = formatted_messages
    openai_messages = [
        {"role": "system", "content": FEEDBACK_SYSTEM_PROMPT_TEMPLATE},
        {"role": "user", "content": FEEDBACK_USER_PROMPT_TEMPLATE.format(**template_contents)}
    ]
    completion = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=openai_messages
    )
    print("openai messages: ", openai_messages)
    print("openai feedback: ", completion.choices[0].message)
    return str(completion.choices[0].message)


def anthropic_generate_feedback(template_contents: dict, formatted_messages: str) -> str:
    """
    Generate feedback using Anthropic
    :param template_contents: feedback prompts
    :param formatted_messages: formatted messages
    :return: feedback
    """
    template_contents['feedback_step_transcript'] = formatted_messages
    anthropic_messages = [
        {"role": "user", "content": FEEDBACK_USER_PROMPT_TEMPLATE.format(**template_contents)}
    ]
    completion = anthropic_client.messages.create(
        model="claude-3-5-sonnet-20240620",
        system=FEEDBACK_SYSTEM_PROMPT_TEMPLATE,
        messages=anthropic_messages,
        max_tokens=1024
    )
    print(anthropic_messages)
    print(completion.content[0].text)
    return str(completion.content[0].text)


def get_feedback(messages_file_path: str, thread_id: str, agent_id: str, step_id: int):
    """
    Process feedback
    :param messages_file_path: messages file path
    :param thread_id: thread id
    :param agent_id: agent id
    :param step_id: step id
    """
    formatted_messages = parse_messages_file(messages_file_path)
    feedback_prompts = gather_feedback_prompts(agent_id, step_id)
    if FEEDBACK_AI_PROVIDER == "openai":
        feedback = openai_generate_feedback(feedback_prompts, formatted_messages)
    elif FEEDBACK_AI_PROVIDER == "anthropic":
        feedback = anthropic_generate_feedback(feedback_prompts, formatted_messages)
    else:
        raise ValueError(f"Unknown feedback AI provider: {FEEDBACK_AI_PROVIDER}")
    print(feedback)
    feedback_storage_handler.put_feedback(thread_id, agent_id, step_id, feedback)
    feedback_dict = {
        "thread_id": thread_id,
        "agent_id": agent_id,
        "step_id": step_id,
        "feedback": feedback
    }
    # Save the feedback to the processed media directory
    feedback_file_path = f"{PROCESSED_MEDIA_DIR}/{thread_id}/step_{str(step_id)}_feedback.json"
    os.makedirs(os.path.dirname(feedback_file_path), exist_ok=True)
    with open(feedback_file_path, 'w') as file:
        json.dump(feedback_dict, file, indent=2)
    print(f"Feedback saved to {feedback_file_path}")
    return
