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
from audio_processing import process_recording_metadata, process_audio_file
from dotenv import load_dotenv

UNPROCESSED_MEDIA_DIR = "./unprocessed_media"


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


def callback(ch, method, properties, body):
    message = json.loads(body)
    file_name = message['file_name']
    metadata_name = message['metadata_name']
    try:
        process_audio(file_name, metadata_name)
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        print(f"Error processing {file_name}: {e}")


if __name__ == "__main__":
    time.sleep(15)
    load_dotenv(dotenv_path="/run/secrets/prepit-secret")
    while True:
        try:
            connection = pika.BlockingConnection(pika.ConnectionParameters('rabbitmq'))
            break
        except Exception as e:
            print("Waiting for RabbitMQ to start")
            # retry every 5 seconds
            time.sleep(5)
    channel = connection.channel()

    channel.queue_declare(queue='audio_processing', durable=True)

    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue='audio_processing', on_message_callback=callback)

    print('Waiting for messages. To exit press CTRL+C')
    channel.start_consuming()
