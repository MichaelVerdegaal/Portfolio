from fastapi import FastAPI
import yaml
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

with open('skills.yaml', 'r') as file:
        loaded_data = yaml.safe_load(file)
app = FastAPI()

app.mount("/src", StaticFiles(directory="src"), name="src")

@app.get("/")
async def root():
    # Reading the data from a YAML file
    return HTMLResponse(content=open("templates/index.html").read())
