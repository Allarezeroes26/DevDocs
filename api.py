import os
import asyncio
import traceback
import aiofiles
from fastapi import FastAPI, HTTPException, UploadFile, File, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.concurrency import run_in_threadpool
from contextlib import asynccontextmanager

from main import MainEngine
from models import QueryRequest, QueryResponse

engine = MainEngine()
is_indexing = False 
MAX_FILE_SIZE = 50 * 1024 * 1024

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handles startup logic like folder creation and model warmup."""
    global is_indexing
    docs_path = "./docs"
    
    if not os.path.exists(docs_path):
        os.makedirs(docs_path)
    
    print("🚀 Warming up LLM and indexing context...")
    is_indexing = True
    try:
        # Load local PDFs on startup
        await run_in_threadpool(engine.load_local_context, docs_path)
    except Exception as e:
        print(f"⚠️ Startup warning: {e}")
    finally:
        is_indexing = False
        
    yield
    print("🛑 System offline.")

app = FastAPI(title="DevDocs Pro API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def get_status():
    """Returns engine metadata for the frontend. Matches 'devDocsApi.getStatus'."""
    return {
        "status": "online",
        "loaded_files": getattr(engine, 'loaded_files', []),
        "model": getattr(engine, 'llm_model', "phi4")
    }

@app.post("/ask", response_model=QueryResponse)
async def ask_question(request: QueryRequest):
    """Handles RAG queries. Matches 'devDocsApi.askQuestion'."""
    if is_indexing:
        raise HTTPException(
            status_code=503, 
            detail="Engine is updating library. Please try again in a moment."
        )

    try:
        # Offload heavy inference to threadpool
        result = await run_in_threadpool(engine.query, request.question)
        
        return QueryResponse(
            answer=result.get("answer", "No response generated."),
            sources=result.get("sources", []),
            latency=result.get("latency", 0.0)
        )
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Inference engine failure.")

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """Matches 'devDocsApi.uploadFile'."""
    global is_indexing
    
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File exceeds 50MB limit.")

    try:
        file_path = os.path.join("./docs", file.filename)
        
        async with aiofiles.open(file_path, "wb") as out_file:
            await out_file.write(content)

        is_indexing = True
        await run_in_threadpool(engine.load_local_context, "./docs")
        
        return {"message": f"Successfully indexed {file.filename}"}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal indexing failure.")
    finally:
        is_indexing = False

@app.delete("/delete/{filename}")
async def delete_file(filename: str):
    """Matches 'devDocsApi.deleteFile'."""
    global is_indexing
    file_path = os.path.join("./docs", filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found.")

    try:
        is_indexing = True
        os.remove(file_path)
        
        await run_in_threadpool(engine.load_local_context, "./docs")
        
        return {"message": f"Removed {filename}", "files": engine.loaded_files}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Failed to delete file.")
    finally:
        is_indexing = False

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)