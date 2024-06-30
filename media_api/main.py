# Copyright (c) 2024.
# -*-coding:utf-8 -*-
"""
@file: main.py.py
@author: Jerry(Ruihuang)Yang
@email: rxy216@case.edu
@time: 6/26/24 15:58
"""
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
import pika
import json
import os
import time
import hashlib

import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s:     %(name)s - %(message)s'
)

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
RABBITMQ_QUEUE = os.getenv("RABBITMQ_QUEUE", "prepit_processing")
UNPROCESSED_MEDIA_DIR = "./unprocessed_media"


async def send_audio_to_queue(file_name, metadata_name):
    connection = pika.BlockingConnection(pika.ConnectionParameters(RABBITMQ_HOST))
    channel = connection.channel()

    channel.queue_declare(queue=RABBITMQ_QUEUE, durable=True)

    message = json.dumps({
        'task_type': 'audio_processing',  # 'audio_processing' or 'feedback_processing'
        'file_name': file_name,
        'metadata_name': metadata_name
    })
    channel.basic_publish(exchange='',
                          routing_key=RABBITMQ_QUEUE,
                          body=message,
                          properties=pika.BasicProperties(
                              delivery_mode=2,  # make message persistent
                          ))
    connection.close()


async def send_feedback_to_queue(messages_filename, thread_id, agent_id, step_id):
    connection = pika.BlockingConnection(pika.ConnectionParameters(RABBITMQ_HOST))
    channel = connection.channel()

    channel.queue_declare(queue=RABBITMQ_QUEUE, durable=True)

    message = json.dumps({
        'task_type': 'feedback_processing',  # 'audio_processing' or 'feedback_processing
        'messages_filename': messages_filename,
        'thread_id': thread_id,
        'agent_id': agent_id,
        'step_id': step_id
    })
    channel.basic_publish(exchange='',
                          routing_key=RABBITMQ_QUEUE,
                          body=message,
                          properties=pika.BasicProperties(
                              delivery_mode=2,  # make message persistent
                          ))
    connection.close()


async def generate_dynamic_auth_code():
    step = 30  # dynamic auth token 30 seconds window
    salt = "prepit_jerry_salt"  # Salt for the dynamic auth token
    time_step = int(time.time() // step)
    time_based_key = str(time_step) + salt  # Combine time step with salt
    return hashlib.sha256(time_based_key.encode()).hexdigest()


@app.post("/new_audio_processing_task")
async def audio_processing_task(
        metadata_file: UploadFile = File(...),
        wav_file: UploadFile = File(...),
        thread_id: str = Form(...),
        ws_sid: str = Form(...),
        dynamic_auth_token: str = Form(...)
):
    # Validate the dynamic auth token
    expected_dynamic_auth_token = await generate_dynamic_auth_code()
    if dynamic_auth_token != expected_dynamic_auth_token:
        return HTTPException(status_code=401, detail="Access Denied")
    try:
        # Save metadata file
        metadata_path = os.path.join(UNPROCESSED_MEDIA_DIR, metadata_file.filename)
        with open(metadata_path, "wb") as f:
            f.write(await metadata_file.read())

        # Save wav file
        wav_file_path = os.path.join(UNPROCESSED_MEDIA_DIR, wav_file.filename)
        with open(wav_file_path, "wb") as f:
            f.write(await wav_file.read())

        await send_audio_to_queue(wav_file.filename, metadata_file.filename)

        return {"message": f"Audio processing queued for {wav_file.filename}, {metadata_file.filename}",
                "wav_file_name": wav_file.filename,
                "metadata_file_name": metadata_file.filename,
                "thread_id": thread_id,
                "ws_sid": ws_sid}
    except Exception as e:
        logging.error(f"Error processing audio: {e}")
        return HTTPException(status_code=500, detail="Error processing audio")


@app.post("/new_feedback_processing_task")
async def feedback_processing_task(
        messages_file: UploadFile = File(...),
        thread_id: str = Form(...),
        agent_id: str = Form(...),
        step_id: int = Form(...),
        dynamic_auth_token: str = Form(...)
):
    # Validate the dynamic auth token
    expected_dynamic_auth_token = await generate_dynamic_auth_code()
    if dynamic_auth_token != expected_dynamic_auth_token:
        return HTTPException(status_code=401, detail="Access Denied")
    try:
        # Save metadata file
        metadata_path = os.path.join(UNPROCESSED_MEDIA_DIR, messages_file.filename)
        with open(metadata_path, "wb") as f:
            f.write(await messages_file.read())

        await send_feedback_to_queue(messages_file.filename, thread_id, agent_id, step_id)

        return {"message": f"Feedback processing queued for {messages_file.filename}",
                "messages_filename": messages_file.filename,
                "thread_id": thread_id,
                "agent_id": agent_id,
                "step_id": step_id}
    except Exception as e:
        logging.error(f"Error processing feedback: {e}")
        return HTTPException(status_code=500, detail="Error processing feedback")


@app.get("/tttt12341234")
async def root():
    return {"message": "Hello World"}
