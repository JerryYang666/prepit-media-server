# Copyright (c) 2024.
# -*-coding:utf-8 -*-
"""
@file: MessageUpdateHandler.py
@author: Jerry(Ruihuang)Yang
@email: rxy216@case.edu
@time: 6/27/24 00:35
"""
import boto3
import logging
import os

logging.basicConfig(level=logging.INFO)


class MessageUpdateHandler:
    DYNAMODB_TABLE_NAME = "prepit_chat_msg"

    def __init__(self):
        self.dynamodb = boto3.resource('dynamodb', region_name='us-east-2',
                                       aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID_DYNAMODB"),
                                       aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY_DYNAMODB"))
        self.table = self.dynamodb.Table(self.DYNAMODB_TABLE_NAME)

    def update_message_audio_flag(self, thread_id: str, created_at: str) -> bool:
        """
        Update the message to set has_audio to True.
        If the message did not have that field, create and set to True.
        :param thread_id: The ID of the thread.
        :param created_at: The time when the message was created.
        :return: True if update was successful, False otherwise.
        """
        try:
            # Update the has_audio field to True
            self.table.update_item(
                Key={
                    'thread_id': thread_id,
                    'created_at': created_at
                },
                UpdateExpression="set has_audio = :val",
                ExpressionAttributeValues={
                    ':val': True
                }
            )
            return True
        except Exception as e:
            print(f"Error updating the message audio flag: {e}")
            return False
