from fastapi import FastAPI
import yaml
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

with open("skills.yaml", "r") as file:
    loaded_data = yaml.safe_load(file)
app = FastAPI()

# Mount Python files
app.mount("/src", StaticFiles(directory="src"), name="src")
# Mount static files (pyscript.json)
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def root():
    # Reading the data from a YAML file
    return HTMLResponse(content=open("templates/index.html").read())
