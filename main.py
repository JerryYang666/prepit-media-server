# Copyright (c) 2024.
# -*-coding:utf-8 -*-
"""
@file: main.py.py
@author: Jerry(Ruihuang)Yang
@email: rxy216@case.edu
@time: 6/26/24 15:58
"""
from fastapi import FastAPI, UploadFile

import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s:     %(name)s - %(message)s'
)

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)


@app.get("/")
async def root():
    return {"message": "Hello World"}
