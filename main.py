from fastapi import FastAPI
import yaml
from fastapi import Request
from fastapi.responses import HTMLResponse

with open('skills.yaml', 'r') as file:
        loaded_data = yaml.safe_load(file)
app = FastAPI()

# app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    # Reading the data from a YAML file
    return HTMLResponse(content=open("templates/index.html").read())
