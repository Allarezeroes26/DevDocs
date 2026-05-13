import os
import re
import time
import json
import hashlib
import pickle
from typing import List, Dict, Any, Optional

# Dependencies
import pytesseract
from pdf2image import convert_from_path
from langchain_core.documents import Document
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings, OllamaLLM
from langchain_community.retrievers import BM25Retriever
from langchain_classic.retrievers import EnsembleRetriever

class MainEngine:
    def __init__(self):
        # CONFIG
        self.embedding_model = "nomic-embed-text:latest"
        self.llm_model = "phi4-mini:latest"
        self.db_path = "docs_db"
        self.manifest_path = os.path.join(self.db_path, "manifest.json")
        self.bm25_cache_path = os.path.join(self.db_path, "bm25.pkl")
        
        # MODELS
        self.embeddings = OllamaEmbeddings(model=self.embedding_model)
        self.llm = OllamaLLM(
            model=self.llm_model, 
            temperature=0.7, 
            num_ctx=4096, 
            stop=["### USER QUESTION:", "USER:", "###"]
        )

        self.splitter = RecursiveCharacterTextSplitter(chunk_size=600, chunk_overlap=100)

        # PERSISTENT STATE
        self.vector_db = None
        self.ensemble_retriever = None
        self.loaded_files = []
        self.chat_history = []

    def _get_file_hash(self, filepath: str) -> str:
        """SHA256 hashing for reliable sync tracking."""
        hasher = hashlib.sha256()
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    def _smart_ocr_pdf(self, file_path: str) -> List[Document]:
        """OCRs only if standard extraction yields no text."""
        print(f"  ⚙️  Running Smart OCR: {os.path.basename(file_path)}")
        documents = []
        try:
            images = convert_from_path(file_path, thread_count=2)
            for i, image in enumerate(images):
                text = pytesseract.image_to_string(image)
                if len(text.strip()) > 5:
                    documents.append(Document(
                        page_content=text,
                        metadata={"source": os.path.basename(file_path), "page": i}
                    ))
        except Exception as e:
            print(f"  ❌ OCR Failed: {e}")
        return documents

    def load_local_context(self, folder_path: str) -> bool:
        if not os.path.exists(folder_path): return False
        if not os.path.exists(self.db_path): os.makedirs(self.db_path, exist_ok=True)
        
        current_files = [f for f in os.listdir(folder_path) if f.endswith(".pdf")]
        current_state = {f: self._get_file_hash(os.path.join(folder_path, f)) for f in current_files}
        
        saved_state = {}
        if os.path.exists(self.manifest_path):
            with open(self.manifest_path, 'r') as f:
                saved_state = json.load(f)

        # Identify Incremental Changes
        added_or_changed = [f for f, h in current_state.items() if saved_state.get(f) != h]
        deleted = [f for f in saved_state.keys() if f not in current_state]

        self.vector_db = Chroma(persist_directory=self.db_path, embedding_function=self.embeddings)

        if added_or_changed or deleted:
            print(f"🔄 Syncing Library: {len(added_or_changed)} updated, {len(deleted)} removed.")
            
            # 1. Clean old data
            for f in deleted:
                self.vector_db.delete(where={"source": f})

            # 2. Process new/changed files
            new_chunks = []
            for file in added_or_changed:
                if file in saved_state:
                    self.vector_db.delete(where={"source": file})
                
                file_path = os.path.join(folder_path, file)
                loader = PyPDFLoader(file_path)
                try:
                    docs = loader.load()
                    if len("".join([d.page_content for d in docs]).strip()) < 100:
                        docs = self._smart_ocr_pdf(file_path)
                except:
                    docs = self._smart_ocr_pdf(file_path)
                
                for d in docs: d.metadata["source"] = file
                new_chunks.extend(self.splitter.split_documents(docs))
                print(f"  📥 Indexed: {file}")

            if new_chunks:
                self.vector_db.add_documents(new_chunks)
            
            # 3. Save Manifest and Rebuild/Cache BM25
            with open(self.manifest_path, 'w') as f:
                json.dump(current_state, f)
            
            print("💾 Caching Hybrid Search Index...")
            all_data = self.vector_db.get(include=['documents', 'metadatas'])
            docs_for_bm25 = [Document(page_content=d, metadata=m) for d, m in zip(all_data['documents'], all_data['metadatas'])]
            bm25 = BM25Retriever.from_documents(docs_for_bm25)
            with open(self.bm25_cache_path, 'wb') as f:
                pickle.dump(bm25, f)
        else:
            print("✨ Library in sync. Loading cached indexes...")

        # Load BM25 from pickle (Prevents heavy RAM usage)
        if os.path.exists(self.bm25_cache_path):
            with open(self.bm25_cache_path, 'rb') as f:
                bm25 = pickle.load(f)
        else:
            # Fallback if cache is missing but DB exists
            all_data = self.vector_db.get(include=['documents', 'metadatas'])
            docs_for_bm25 = [Document(page_content=d, metadata=m) for d, m in zip(all_data['documents'], all_data['metadatas'])]
            bm25 = BM25Retriever.from_documents(docs_for_bm25)

        bm25.k = 4
        self.loaded_files = list(current_state.keys())
        self.ensemble_retriever = EnsembleRetriever(
            retrievers=[self.vector_db.as_retriever(search_kwargs={"k": 4}), bm25],
            weights=[0.7, 0.3]
        )
        return True
    
    def _build_prompt(self, question: str, context: str) -> str:
        """Constructs the final instruction string for the LLM."""
        history = "\n".join([f"User: {h['user']}\nAgent: {h['assistant']}" for h in self.chat_history])
        files_list = ", ".join(self.loaded_files) if self.loaded_files else "No files loaded"

        return f"""### SYSTEM ROLE:
You are the DEVDOCS AGENT, a senior technical instructor. Your purpose is to help users understand developer tools and technical documentation better.

### OPERATIONAL RULES:
1. **TECHNICAL DOMAIN ONLY**: Your expertise is strictly limited to Computer Science, Software Engineering, and IT.
2. **THE REDIRECT RULE**: If a user asks about unrelated topics (e.g., cooking, lifestyle), acknowledge briefly then redirect them to the loaded library: [{files_list}].
3. **ALLOWED META-QUESTIONS**: Questions about the content or summaries of the loaded PDFs (e.g., "What is in sicp.pdf?") are ON-TOPIC.
4. **MISSING CONTEXT RULE**: If a technical topic is asked but not found in the DOCUMENT CONTEXT below, inform the user you don't have that specific data and remind them to **put or upload a technical PDF** into the 'docs' folder.
5. **FIDELITY**: Do not hallucinate. Use only the provided context for technical facts.

### LOADED LIBRARY:
{files_list}

### CONVERSATION HISTORY:
{history if history else "Handshake complete."}

### DOCUMENT CONTEXT:
{context if context else "--- NO RELEVANT TECHNICAL SNIPPETS FOUND IN LIBRARY ---"}

### USER QUESTION:
{question}

### MENTOR RESPONSE:
"""

    def query(self, question: str) -> Dict[str, Any]:
        start = time.time()
        q_lower = question.lower().strip()
        
        # NOTE: Using keyword-based interceptors for O(1) speed. 
        # Future upgrade: Semantic Routing via Cosine Similarity for intent detection.
        
        if any(word in q_lower for word in ["who made you", "creator", "developer", "author"]):
            return {
                "answer": (
                    "I was developed by **Erwin Bacani** as a specialized RAG portfolio project. "
                    "You can connect with him or view his other projects here:\n\n"
                    "🚀 [Portfolio](https://portfolio-j0qq.onrender.com/)\n"
                    "💻 [GitHub](https://github.com/Allarezeroes26)\n"
                    "👔 [LinkedIn](https://www.linkedin.com/in/john-erwin-bacani-90853a359/)"
                ),
                "sources": ["System Identity"], "latency": round(time.time() - start, 2)
            }

        if any(word in q_lower for word in ["what do you do", "purpose", "how do you work"]):
            return {
                "answer": "I am a **DevDocs Assistant**. I analyze your local technical PDF library to provide precise, context-aware answers and summaries, helping you learn complex documentation faster.",
                "sources": ["System Capability"], "latency": round(time.time() - start, 2)
            }

        if "tech stack" in q_lower or "how are you built" in q_lower:
            return {
                "answer": (
                    "My architecture includes:\n"
                    "• **LLM:** Phi-4-mini (Local via Ollama)\n"
                    "• **Vector DB:** ChromaDB with Nomic Embeddings\n"
                    "• **Retrieval:** Hybrid Ensemble (Semantic + BM25 Keyword)\n"
                    "• **Framework:** LangChain & Next.js"
                ),
                "sources": ["System Architecture"], "latency": round(time.time() - start, 2)
            }

        if not self.vector_db: 
            return {"answer": "I don't have any docs yet!", "sources": [], "latency": 0}

        try:
            raw_docs = self.ensemble_retriever.invoke(question)
        except Exception:
            raw_docs = self.vector_db.similarity_search(question, k=4)

        unique_docs = list({d.page_content: d for d in raw_docs}.values())
        context = "\n\n".join(f"[SOURCE: {d.metadata.get('source')}]\n{d.page_content}" for d in unique_docs)

        response = self.llm.invoke(self._build_prompt(question, context))
        
        self.chat_history.append({"user": question, "assistant": response})
        self.chat_history = self.chat_history[-6:] 

        return {
            "answer": response.strip(),
            "sources": list(set(d.metadata.get("source") for d in unique_docs)),
            "latency": round(time.time() - start, 2)
        }