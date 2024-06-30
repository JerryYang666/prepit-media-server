# Copyright (c) 2024.
# -*-coding:utf-8 -*-
"""
@file: start.py.py
@author: Jerry(Ruihuang)Yang
@email: rxy216@case.edu
@time: 6/26/24 20:54
"""
import pika
import json
import time
import os
from audio_processing import process_recording_metadata, process_audio_file
from feedback_processing import get_feedback
from dotenv import load_dotenv

load_dotenv(dotenv_path="/run/secrets/prepit-secret")

UNPROCESSED_MEDIA_DIR = "./unprocessed_media"
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
RABBITMQ_QUEUE = os.getenv("RABBITMQ_QUEUE", "prepit_processing")


def process_audio(wav_name, metadata_name):
    wav_path = f"{UNPROCESSED_MEDIA_DIR}/{wav_name}"
    metadata_path = f"{UNPROCESSED_MEDIA_DIR}/{metadata_name}"
    print(f"Processing {wav_path} with metadata {metadata_path}")
    processed_metadata = process_recording_metadata(metadata_path)
    if processed_metadata is False:
        print(f"Skipping processing {wav_path}")
        return
    process_audio_file(wav_path, processed_metadata)
    print(f"Finished processing {wav_path}")


def process_feedback(messages_filename, thread_id, agent_id, step_id):
    messages_path = f"{UNPROCESSED_MEDIA_DIR}/{messages_filename}"
    print(f"Processing feedback for {messages_path}")
    get_feedback(messages_path, thread_id, agent_id, step_id)
    print(f"Finished processing feedback for {messages_path}")


def callback(ch, method, properties, body):
    message = json.loads(body)
    task_type = message['task_type']
    if task_type == 'audio_processing':
        file_name = message['file_name']
        metadata_name = message['metadata_name']
        try:
            process_audio(file_name, metadata_name)
            ch.basic_ack(delivery_tag=method.delivery_tag)
        except Exception as e:
            print(f"Error processing audio {file_name}: {e}")
    elif task_type == 'feedback_processing':
        messages_filename = message['messages_filename']
        thread_id = message['thread_id']
        agent_id = message['agent_id']
        step_id = message['step_id']
        try:
            process_feedback(messages_filename, thread_id, agent_id, step_id)
            ch.basic_ack(delivery_tag=method.delivery_tag)
        except Exception as e:
            print(f"Error processing feedback for {messages_filename}: {e}")
    else:
        print(f"Unknown task type {task_type}")


if __name__ == "__main__":
    print("Starting prepit processing worker")
    # wait for RabbitMQ to start
    print("Waiting for RabbitMQ to start")
    time.sleep(15)
    print("Trying to connect to RabbitMQ")
    while True:
        try:
            connection = pika.BlockingConnection(pika.ConnectionParameters(RABBITMQ_HOST))
            break
        except Exception as e:
            print(f"RabbitMQ connection failed {e}, retrying in 5 seconds")
            # retry every 5 seconds
            time.sleep(5)
    channel = connection.channel()

    channel.queue_declare(queue=RABBITMQ_QUEUE, durable=True)

    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue=RABBITMQ_QUEUE, on_message_callback=callback)

    print(f'Waiting for messages in {RABBITMQ_QUEUE}. To exit press CTRL+C')
    channel.start_consuming()
