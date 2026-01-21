import os
from dotenv import load_dotenv
from langchain_ollama import ChatOllama

load_dotenv()

OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")

def get_llm(temperature: float = 0.0) -> ChatOllama:
    """
    Returns a configured ChatOllama instance.
    """
    return ChatOllama(
        model=OLLAMA_MODEL,
        temperature=temperature
    )
