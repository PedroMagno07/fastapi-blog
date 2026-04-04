# fastapi-blog

A full-stack blog application built with **FastAPI** and **SQLAlchemy 2.0**, featuring a JSON REST API alongside server-side rendered HTML pages using Jinja2 templates.

## Features

- Full **CRUD** for users and posts via a RESTful JSON API
- **Server-side rendered** pages (home feed, post detail, user post listing)
- **Async** database access with SQLAlchemy 2.0 + aiosqlite
- **Pydantic v2** schemas for request validation and response serialization
- Global exception handlers that return JSON for API routes and HTML error pages for browser routes
- Automatic database table creation on startup via SQLAlchemy's `create_all`
- Static file serving for CSS/JS assets and user profile pictures

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | FastAPI |
| Database ORM | SQLAlchemy 2.0 (async) |
| Database | SQLite + aiosqlite |
| Validation | Pydantic v2 |
| Templates | Jinja2 |
| Server | Uvicorn |
| Package Manager | uv |

## Project Structure

```
fastapi-blog/
├── main.py              # App entry point, page routes, exception handlers
├── database.py          # Engine, session factory, get_db dependency
├── models.py            # SQLAlchemy ORM models (User, Post)
├── schemas.py           # Pydantic schemas for validation and serialization
├── routers/
│   ├── users.py         # API routes for users  (/api/users)
│   └── posts.py         # API routes for posts  (/api/posts)
├── templates/           # Jinja2 HTML templates
├── static/              # CSS, JS, default profile picture
├── media/
│   └── profile_pics/    # User-uploaded profile pictures
└── pyproject.toml
```

## API Endpoints

### Users — `/api/users`

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/users` | Create a new user |
| `GET` | `/api/users/{user_id}` | Get a user by ID |
| `GET` | `/api/users/{user_id}/posts` | Get all posts by a user |
| `PATCH` | `/api/users/{user_id}` | Partially update a user |
| `DELETE` | `/api/users/{user_id}` | Delete a user (and all their posts) |

### Posts — `/api/posts`

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/posts` | Create a new post |
| `GET` | `/api/posts` | List all posts |
| `GET` | `/api/posts/{post_id}` | Get a post by ID |
| `PUT` | `/api/posts/{post_id}` | Fully replace a post |
| `PATCH` | `/api/posts/{post_id}` | Partially update a post |
| `DELETE` | `/api/posts/{post_id}` | Delete a post |

### Pages

| Path | Description |
|---|---|
| `/` or `/posts` | Home feed — all posts, newest first |
| `/posts/{post_id}` | Post detail page |
| `/users/{user_id}/posts` | All posts by a specific user |

Interactive API documentation is available at `/docs` (Swagger UI) and `/redoc` when the server is running.

## Getting Started

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

### Installation

**With uv (recommended):**

```bash
git clone https://github.com/PedroMagno07/fastapi-blog.git
cd fastapi-blog
uv sync
```

**With pip:**

```bash
git clone https://github.com/PedroMagno07/fastapi-blog.git
cd fastapi-blog
pip install -r requirements.txt
```

### Running the Server

**With uv:**

```bash
uv run fastapi dev main.py
```

**With pip / uvicorn directly:**

```bash
uvicorn main:app --reload
```

The application will be available at `http://localhost:8000`.

Interactive API docs:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

The SQLite database (`blog.db`) is created automatically on first run — no migrations needed.

## About This Project

This is a **study project** built to practice back-end Python development, with a focus on building REST APIs using FastAPI and SQLAlchemy 2.0 async. The goal was to learn real-world patterns such as async database sessions, dependency injection, Pydantic v2 schema design, and proper HTTP semantics (PUT vs PATCH, status codes, error handling).

The HTML and CSS templates used in the server-side rendered pages were created by **Corey Schafer** and are part of his Flask/Python tutorial series on YouTube. Full credit goes to him for the front-end assets — they are not part of the original work developed in this project.

## Author

Pedro Magno — [GitHub](https://github.com/PedroMagno07) · [LinkedIn](https://www.linkedin.com/in/pedro-magno)