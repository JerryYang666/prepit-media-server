# Copyright (c) 2024.
# -*-coding:utf-8 -*-
"""
@file: FileUploadHandler.py.py
@author: Jerry(Ruihuang)Yang
@email: rxy216@case.edu
@time: 6/27/24 00:53
"""
import boto3
from botocore.exceptions import ClientError
import os
import mimetypes


class FileUploadHandler:
    BUCKET_NAME = 'bucket-57h03x'  # Specify your S3 bucket name here
    S3_FOLDER = 'prepit_data/audio/'  # Base folder in S3 to store uploaded files

    def __init__(self):
        self.s3_client = boto3.client('s3')

    def upload_file(self, local_file_path: str, s3_folder_path: str, is_public: bool = False) -> bool:
        """
        Upload a file to a specified path in S3 with the same filename.
        Make it publicly accessible and set the content type based on the file extension.
        :param local_file_path: The local path of the file to upload.
        :param s3_folder_path: The desired folder path in S3 (relative to the base folder).
        :param is_public: Whether the file should be publicly accessible.
        :return: The public URL to the file in S3.
        """
        file_name = os.path.basename(local_file_path)
        object_name = f"{self.S3_FOLDER}{s3_folder_path}{file_name}"

        if local_file_path.lower().endswith('.mp3'):
            content_type = 'audio/mpeg'
        else:
            # Determine the content type based on the file extension
            content_type, _ = mimetypes.guess_type(local_file_path)
            if content_type is None:
                content_type = 'application/octet-stream'  # Default to binary stream if MIME type can't be determined

        try:
            # Upload the file with content type specified
            with open(local_file_path, 'rb') as file:
                self.s3_client.upload_fileobj(file, self.BUCKET_NAME, object_name,
                                              ExtraArgs={'ContentType': content_type})

            if is_public:
                # Set the file's ACL to public-read
                self.s3_client.put_object_acl(ACL='public-read', Bucket=self.BUCKET_NAME, Key=object_name)

            return True
        except ClientError as e:
            print(f"An error occurred: {e}")
            return False
