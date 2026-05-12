import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from main import MainEngine  # Importing your existing class

class QueryRequest(BaseModel):
    question: str

class QueryResponse(BaseModel):
    answer: str
    sources: List[str]
    latency: float

app = FastAPI(title="DevDocs Mentor API")
engine = MainEngine()

@app.on_event("startup")
async def startup_event():
    docs_path = "./docs"
    if not os.path.exists(docs_path):
        os.makedirs(docs_path)
    
    print(f"Initializing Engine with folder: {docs_path}")
    success = engine.load_local_context(docs_path)
    if not success:
        print("Warning: No PDFs found in /docs folder during startup.")

@app.get("/")
async def root():
    return {
        "status": "online",
        "loaded_files": engine.loaded_files,
        "model": engine.llm_model
    }

@app.post("/ask", response_model=QueryResponse)
async def ask_question(request: QueryRequest):
    try:
        # Using your existing query logic
        result = engine.query(request.question)
        return QueryResponse(
            answer=result["answer"],
            sources=result["sources"],
            latency=result["latency"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/refresh")
async def refresh_library():
    """Trigger a re-index of the /docs folder."""
    success = engine.load_local_context("./docs")
    return {
        "success": success,
        "files": engine.loaded_files
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)