
# Imports
from pypdf import PdfReader

from langchain_text_splitters import RecursiveCharacterTextSplitter

from google import genai
from dotenv import load_dotenv
import os

from config import EMBEDDING_MODEL



# Read PDF and Extract Text

def load_pdf(pdf_path):
    """
    Reads a PDF file and returns all its text as a single string.
    """

    reader = PdfReader(pdf_path)

    text = ""

    # Read every page
    for page in reader.pages:
        text += page.extract_text() + "\n"

    return text


# Split Text into Chunks



def create_chunks(text, chunk_size=1000, chunk_overlap=200):
    """
    Splits the given text into smaller overlapping chunks.
    """

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )

    chunks = text_splitter.split_text(text)

    return chunks



# Create Gemini Client


def get_gemini_client():
    """
    Creates and returns a Gemini client.
    """

    # Load environment variables
    load_dotenv()

    # Create Gemini client
    client = genai.Client(
        api_key=os.getenv("GEMINI_API_KEY")
    )

    return client



# Generate Embeddings


def create_embeddings(client, chunks):
    """
    Generates embeddings for all chunks and
    returns a list of embedding vectors.
    """

    # Generate embeddings for all chunks
    response = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=chunks
    )

    # Extract only the embedding vectors
    embeddings = [
        embedding.values
        for embedding in response.embeddings
    ]

    return embeddings


# ===========================
# Generate Query Embedding
# ===========================

def create_query_embedding(client, question):
    """
    Generates an embedding for the user's question.
    """

    response = client.models.embed_content(
        model="gemini-embedding-001",
        contents=question
    )

    return response.embeddings[0].values