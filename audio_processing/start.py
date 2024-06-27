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

UNPROCESSED_MEDIA_DIR = "./unprocessed_media"


def process_audio(wav_name, metadata_name):
    wav_path = f"{UNPROCESSED_MEDIA_DIR}/{wav_name}"
    metadata_path = f"{UNPROCESSED_MEDIA_DIR}/{metadata_name}"
    print(f"Processing {wav_path} with metadata {metadata_path}")
    try:
        processed_metadata = process_recording_metadata(metadata_path)
        process_audio_file(wav_path, processed_metadata)
    except Exception as e:
        print(f"Error processing {wav_path}: {e}")
    print(f"Finished processing {wav_path}")


def callback(ch, method, properties, body):
    message = json.loads(body)
    file_name = message['file_name']
    metadata_name = message['metadata_name']
    process_audio(file_name, metadata_name)
    ch.basic_ack(delivery_tag=method.delivery_tag)


if __name__ == "__main__":
    time.sleep(15)
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
