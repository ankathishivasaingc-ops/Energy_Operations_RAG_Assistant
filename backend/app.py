from fastapi import FastAPI
from pydantic import BaseModel
import pandas as pd
from pathlib import Path

app = FastAPI(title='Energy Operations Document RAG Assistant')
BASE = Path(__file__).resolve().parents[1]
DATA = BASE / 'data'

class Query(BaseModel):
    text: str = ''

@app.get('/api/demo')
def demo():
    return {
        'case_study': 'Energy Operations Document RAG Assistant',
        'status': 'starter app running',
        'expected_outcome': 'A working RAG-based assistant that answers operational questions from provided documents with citations, retrieval evidence, and hallucination checks.'
    }

@app.post('/api/run')
def run_case(query: Query):
    # Starter placeholder: candidates should replace this with their ML/RAG/agentic pipeline.
    return {
        'input': query.text,
        'result': 'Implement candidate solution here.',
        'evaluation_hint': 'Return predictions, retrieval evidence, reasoning steps, metrics, and limitations.'
    }
