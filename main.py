from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI()

templates = Jinja2Templates(directory="templates")

app.mount("/static", StaticFiles(directory="static"), name="static")

posts: list[dict] = [
    {
        "id": 1,
        "author": "Pedro Magno",
        "title": "FastAPI is Awesome",
        "content": "This framework is really easy to use and super fast",
        "date_posted": "May 18, 2026"
    },
        {
        "id": 2,
        "author": "Amandha Sanabe",
        "title": "Python is Great for Web Development",
        "content": "Python is a great leaguage for web devs, and FastAPI makes it even better!",
        "date_posted": "May 15, 2026"
    }
]

@app.get("/", include_in_schema=False, name="home")
@app.get("/posts", include_in_schema=False, name="posts")
def home(request: Request):
    return templates.TemplateResponse(
    request, 
    "home.html", 
    {"posts": posts, "title": "Home"},
    )

@app.get("/api/posts/{post_id}")
def get_post(post_id: int):
    for post in posts:
        if post.get("id") == post_id:
            return post
    return {"error": "Post not found"}
