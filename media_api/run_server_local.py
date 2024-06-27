# Copyright (c) 2024.
# -*-coding:utf-8 -*-
"""
@file: run_server_local.py
@author: Jerry(Ruihuang)Yang
@email: rxy216@case.edu
@time: 6/26/24 16:02
"""
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        reload=True,
    )
