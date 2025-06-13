from fastapi import FastAPI

from home_task.api import router

app = FastAPI()
app.include_router(router)
