# PDF RAG Chatbot

A Retrieval-Augmented Generation (RAG) chatbot built with Python, Google Gemini, and ChromaDB.

The application allows users to ask questions about a PDF document. Instead of answering from the LLM's general knowledge, the system retrieves relevant information from the PDF and uses that context to generate an answer.

## Features

- Extracts text from PDF documents
- Splits text into smaller chunks
- Generates embeddings using Google Gemini
- Stores embeddings in ChromaDB
- Performs semantic similarity search
- Retrieves relevant PDF chunks
- Generates context-based answers using Gemini
- Persistent vector database
- Supports multiple questions in a chat loop
- Prevents answers when information is not available in the document

## RAG Pipeline

PDF
↓
Text Extraction
↓
Text Chunking
↓
Embeddings
↓
ChromaDB Vector Store
↓
User Question
↓
Query Embedding
↓
Similarity Search
↓
Relevant Chunks
↓
Gemini
↓
Answer

## Tech Stack

- Python
- Google Gemini API
- ChromaDB
- PyPDF
- LangChain Text Splitters
- python-dotenv

## Project Structure

```text
10_PDF_RAG_CHATBOT/
│
├── index.py
├── chat.py
├── utils.py
├── config.py
├── sample.pdf
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

## Installation

Clone the repository and install the dependencies:

```bash
pip install -r requirements.txt
```

Create a `.env` file and add your Gemini API key:

```env
GEMINI_API_KEY=your_gemini_api_key_here
```

## Usage

First, index the PDF:

```bash
python index.py
```

Then start the chatbot:

```bash
python chat.py
```

Type:

```text
exit
```

to stop the chatbot.

## Example

```text
Ask your question: What is a constructor?

Answer:
A constructor is a special member function used to initialize
objects of a class.
```

If the requested information is not available in the document:

```text
I couldn't find the answer in the provided document.
```

## What I Learned

Through this project, I learned how a complete RAG pipeline works, including text extraction, chunking, embeddings, vector databases, semantic retrieval, context construction, and LLM-based answer generation.

I also learned how to organize a GenAI project into reusable modules and use a persistent vector database instead of recreating embeddings for every question.

## Future Improvements

- Web interface
- FastAPI backend
- PDF upload support
- Source citations
- Conversation history
- Deployment
