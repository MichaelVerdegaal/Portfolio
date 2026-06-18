from fastapi import FastAPI
import yaml

with open('skills.yaml', 'r') as file:
        loaded_data = yaml.safe_load(file)
app = FastAPI()


@app.get("/")
async def root():
    # Reading the data from a YAML file
    return dict(loaded_data)