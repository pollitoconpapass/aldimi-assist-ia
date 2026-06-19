from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import auth, chat, users, vision

app = FastAPI()

origins = [
    "http://localhost:3000",
    "http://localhost:5000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"],
)

PREFIX_API_VERSION = "/api"

app.include_router(auth.router, prefix=PREFIX_API_VERSION) # -> url: http://localhost:8000/api/auth
app.include_router(chat.router, prefix=PREFIX_API_VERSION) # -> url: http://localhost:8000/api/chat
app.include_router(users.router, prefix=PREFIX_API_VERSION) # -> url: http://localhost:8000/api/users
app.include_router(vision.router, prefix=PREFIX_API_VERSION) # -> url: http://localhost:8000/api/vision

@app.get(f"{PREFIX_API_VERSION}/")
def hello():
    return{ "message": "Estamos vivos y coleando"}