# fastapi主入口
from fastapi import FastAPI

app = FastAPI()

@app.get("/root")
async def get_root():
    return "这是一个基于FastAPI的旅游助手"

@app.post()
