from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
from dotenv import load_dotenv
import requests
import re
import json

app = FastAPI()







@app.get("/")
def home():
    return {"message": "API is running!"}

    load_dotenv()  # Load environment variables

API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL_ID = os.getenv("MODEL_ID")


# Store user session data
session_story = {}
user_initial_input = {}

class StoryRequest(BaseModel):
    user_id: str
    story_start: str

class ContinueRequest(BaseModel):
    user_id: str
    selected_plot: str

class SaveRequest(BaseModel):
    user_id: str

def generate_plots(user_id, user_input, previous_story=""):
    """Generate 3 meaningful story plot options using OpenRouter API."""
    if user_id not in user_initial_input:
        user_initial_input[user_id] = user_input

    limited_context = previous_story if previous_story else user_input

    prompt = (
        f"Story so far: {limited_context}\n\n"
        "Continue the story by generating exactly three different possible next developments.\n"
        "Each response should follow this format strictly:\n"
        "Option 1: <Short but meaningful continuation of the story>\n"
        "Option 2: <Another completely different continuation>\n"
        "Option 3: <Another different possibility>\n\n"
        "Keep each option within 4-5 sentences. Do NOT explain your choices, just provide the options."
    )

    response = requests.post(
        url="https://openrouter.ai/api/v1/chat/completions",
        headers={"Authorization": f"Bearer {API_KEY}"},
        data=json.dumps({
            "model": MODEL_ID,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 600,
            "temperature": 0.8,
            "top_p": 0.9,
        })
    )

    if response.status_code == 200:
        ai_text = response.json()["choices"][0]["message"]["content"]
        matches = re.findall(r"Option\s+\d+:\s*(.*)", ai_text)
        plots = [match.strip() for match in matches]

        if len(plots) < 3:
            return {"error": "AI response is incomplete. Please retry."}
        
        return {"plots": plots}
    
    else:
        return {"error": f"API Error: {response.status_code}"}

@app.post("/generate")
def generate_story(request: StoryRequest):
    """Generate the first 3 story plot options."""
    user_id = request.user_id
    story_start = request.story_start

    session_story[user_id] = []
    return generate_plots(user_id, story_start)

@app.post("/continue")
def continue_story(request: ContinueRequest):
    """Continue the story with the selected plot."""
    user_id = request.user_id
    selected_plot = request.selected_plot

    if user_id not in session_story:
        raise HTTPException(status_code=400, detail="No story session found. Start a new story first.")
    
    session_story[user_id].append(selected_plot)
    previous_story = " ".join(session_story[user_id])
    return generate_plots(user_id, "", previous_story)

@app.post("/save")
def save_story(request: SaveRequest):
    """Save the full story and return it."""
    user_id = request.user_id

    if user_id not in session_story:
        raise HTTPException(status_code=400, detail="No story session found. Start a new story first.")
    
    final_story = user_initial_input.get(user_id, "") + " " + " ".join(session_story[user_id])
    
    del session_story[user_id]
    del user_initial_input[user_id]

    return {"final_story": final_story}

