# 🧠 AI Image Editor API  
> A modern FastAPI backend for AI-powered image generation and editing — powered by **FAL AI**.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi)
![PostgreSQL](https://img.shields.io/badge/Database-PostgreSQL-336791?logo=postgresql)
![License](https://img.shields.io/badge/License-MIT-green)
![Status](https://img.shields.io/badge/Status-Production_Ready-success)

---

## 🌟 Overview

The **AI Image Editor API** lets users **generate and edit images** using FAL AI models such as  
🪄 `fal-ai/nano-banana` (text-to-image)  
🎨 `fal-ai/nano-banana/edit` (image-to-image)

It supports:

- 🔐 **JWT Authentication** (Login / Register / Token)
- 🧑‍💻 **User-specific job tracking**s
- 🖼️ **Image upload and validation**
- ⏳ **Asynchronous job monitoring**
- 💾 **SQLAlchemy ORM integration**
- ⚡ **Fully asynchronous FastAPI endpoints**

---

## 🧰 Tech Stack

| Layer | Technology |
|-------|-------------|
| **Backend** | [FastAPI](https://fastapi.tiangolo.com/) |
| **Auth** | JWT |
| **Database** | SQLite |
| **AI Provider** | [FAL AI](https://fal.ai) |
| **Async Tasks** | FastAPI `BackgroundTasks` |
| **Image Processing** | Pillow (PIL) |
| **Validation** | Pydantic Schemas |

---

## ⚙️ Installation & Setup


```env
python -m venv venv

pip install --upgrade -r requirements.txt

uvicorn app.main:app --port 3434 --reload

```
# Example `.env` file

```env
DATABASE_URL=sqlite:///./jobs.db
FAL_KEY=YOURAPIKEY
JWT_SECRET=YOURSECRET
JWT_ALGORITHM=HS256
