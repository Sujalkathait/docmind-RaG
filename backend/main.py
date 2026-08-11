from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.rag import ask_question
from backend.upload import process_uploaded_pdf


app = FastAPI()


# ================================
# CORS
# ================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ================================
# Question Model
# ================================

class Question(BaseModel):
    question: str


# ================================
# Home
# ================================

@app.get("/")
def home():
    return {
        "message": "PDF RAG Chatbot API"
    }


# ================================
# Ask Question
# ================================

@app.post("/ask")
def ask(question: Question):

    answer = ask_question(
        question.question
    )

    return {
        "answer": answer
    }


# ================================
# Upload PDF
# ================================

@app.post("/upload")
async def upload_pdf(
    file: UploadFile = File(...)
):

    if not file.filename.lower().endswith(".pdf"):

        return {
            "success": False,
            "message": "Only PDF files are allowed."
        }

    pdf_bytes = await file.read()

    try:

        result = process_uploaded_pdf(
            pdf_bytes
        )

        return {
            "success": True,
            "message": "PDF uploaded and processed successfully.",
            "filename": file.filename,
            "chunks": result["chunks"]
        }

    except Exception as e:

        return {
            "success": False,
            "message": str(e)
        }