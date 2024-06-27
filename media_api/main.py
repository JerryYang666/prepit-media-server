# Copyright (c) 2024.
# -*-coding:utf-8 -*-
"""
@file: main.py.py
@author: Jerry(Ruihuang)Yang
@email: rxy216@case.edu
@time: 6/26/24 15:58
"""
from fastapi import FastAPI, UploadFile
import pika
import json
import os

import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s:     %(name)s - %(message)s'
)

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)


async def send_to_queue(file_path, metadata_path):
    connection = pika.BlockingConnection(pika.ConnectionParameters('rabbitmq'))
    channel = connection.channel()

    channel.queue_declare(queue='audio_processing', durable=True)

    message = json.dumps({
        'file_path': file_path,
        'metadata_path': metadata_path
    })
    channel.basic_publish(exchange='',
                          routing_key='audio_processing',
                          body=message,
                          properties=pika.BasicProperties(
                              delivery_mode=2,  # make message persistent
                          ))
    connection.close()


@app.get("/new_audio_processing_task")
async def root(file_path: str, metadata_path: str):
    await send_to_queue(file_path, metadata_path)
    return {"message": "Hello World"}
