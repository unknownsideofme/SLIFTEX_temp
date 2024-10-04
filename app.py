from fastapi import FastAPI
from fuzzywuzzy import fuzz
from googletrans import Translator
import pandas as pd
from pydantic import BaseModel
from typing import List
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
import os

app = FastAPI()

# Serve templates from the 'templates' directory
app.mount("/", StaticFiles(directory="templates", html=True), name="templates")

# CORS configuration
origins = ["*"]  # Allow all origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600
)

# Load the data from the pickle file
df = pd.read_pickle('data.pkl')
existing_titles = df
disallowed_words = ["police", "crime", "corruption", "cbi", "cid", "army"]

# Helper function for string similarity
def get_string_similarity(new_title, existing_title):
    return fuzz.ratio(new_title.lower(), existing_title.lower())

# Check if title contains disallowed words
def has_disallowed_prefix_suffix(title, disallowed_words):
    words = title.lower().split()
    return any(word in disallowed_words for word in words)

# Translate English title to Hindi
def translate_to_hindi(title):
    translator = Translator()
    hindi_title = translator.translate(title, dest='hi')
    return hindi_title.text

# Check if title contains disallowed words
def check_disallowed_words(new_title):
    return any(word.lower() in disallowed_words for word in new_title.split())

# Main function to verify the title
def verify_title(new_title):
    # Translate English title to Hindi
    hindi_title = translate_to_hindi(new_title)

    if check_disallowed_words(new_title) or check_disallowed_words(hindi_title):
        return {"status": "rejected", "reason": "Title contains disallowed words."}

    similarity_scores = []

    for title in existing_titles:
        score = get_string_similarity(new_title, title)
        similarity_scores.append((title, score))
        if score > 80:  # Reject if similarity is above 80%
            return {
                "status": "rejected",
                "reason": f"Title is too similar to existing title '{title}' with {score}% similarity."
            }

        # Also compare with Hindi title
        hindi_score = get_string_similarity(hindi_title, title)
        similarity_scores.append((title, hindi_score))
        if hindi_score > 80:  # Reject if similarity is above 80%
            return {
                "status": "rejected",
                "reason": f"Title is too similar to existing title '{title}' with {hindi_score}% similarity."
            }

    # Provide a similarity probability score
    max_similarity = max([score for _, score in similarity_scores])
    verification_probability = 100 - max_similarity

    return {
        "status": "pending",
        "similarity_score": max_similarity,
        "verification_probability": verification_probability
    }

# Pydantic model for request
class TitleRequest(BaseModel):
    titles: List[str]

templates = Jinja2Templates(directory="templates")

@app.get("/")
async def read_root():
    return templates.TemplateResponse("index.html", {"request": "root"})

@app.post("/")
async def verify_title_endpoint(request: TitleRequest):
    responses = []
    for input_title in request.titles:
        result = verify_title(input_title)
        responses.append(result)
    return responses

# Main entry point for deployment
if __name__ == "__main__":
    import uvicorn
    import os
    
    port = int(os.environ.get("PORT", 8000))  # Get the PORT from environment variables
    uvicorn.run(app, host="0.0.0.0", port=port)