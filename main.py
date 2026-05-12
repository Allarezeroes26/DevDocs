import os
import re
import time
import shutil
import json
from typing import List, Dict, Any, Optional

# Dependencies for OCR and Core Documents
import pytesseract
from pdf2image import convert_from_path
from langchain_core.documents import Document

# LangChain Suite
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
        self.chunk_size = 500
        self.chunk_overlap = 100

        # MODELS
        self.embeddings = OllamaEmbeddings(model=self.embedding_model)
        self.llm = OllamaLLM(model=self.llm_model, temperature=0.7, stop=["### USER QUESTION:", "USER:", "###"])

        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""]
        )

        # STATE
        self.vector_db = None
        self.bm25_retriever = None
        self.loaded_files = []
        self.chat_history = []

    def _clean_text(self, text: str) -> str:
        text = re.sub(r"\s+", " ", text)
        text = text.replace("\x00", "")
        return text.strip()

    def _get_library_state(self, folder_path: str) -> Dict[str, float]:
        """Returns a map of filename -> last_modified_time for sync tracking."""
        if not os.path.exists(folder_path): return {}
        return {f: os.path.getmtime(os.path.join(folder_path, f)) 
                for f in os.listdir(folder_path) if f.endswith(".pdf")}

    def _ocr_pdf(self, file_path: str) -> List[Document]:
        """Converts scanned PDF pages to images and performs OCR."""
        print(f"  ⚙️  OCR fallback triggered: {os.path.basename(file_path)}")
        documents = []
        try:
            images = convert_from_path(file_path)
            for i, image in enumerate(images):
                text = pytesseract.image_to_string(image)
                documents.append(Document(
                    page_content=text,
                    metadata={"source": os.path.basename(file_path), "page": i}
                ))
        except Exception as e:
            print(f"  ❌ OCR Failed: {e}")
        return documents

    def _extract_file_filter(self, question: str) -> Optional[str]:
        if not self.loaded_files: return None
        q = question.lower()
        best_file, best_score = None, 0
        for file in self.loaded_files:
            file_base = file.lower().replace(".pdf", "")
            score = 0
            for token in file_base.split():
                if token in q: score += 2
            if file_base[:6] in q: score += 1
            if score > best_score:
                best_score, best_file = score, file
        return best_file if best_score > 0 else None

    def _is_malicious(self, text: str) -> bool:
        patterns = [r"ignore.*instructions", r"system prompt", r"reveal.*rules", r"bypass"]
        return any(re.search(p, text.lower()) for p in patterns)

    def _is_greeting(self, text: str) -> bool:
        greetings = ["hi", "hello", "hey", "howdy", "whats up", "yo"]
        clean_q = text.lower().strip().strip('?!.')
        return clean_q in greetings or any(clean_q.startswith(g + " ") for g in greetings)

    def _build_prompt(self, question: str, context: str) -> str:
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

    def load_or_create_db(self, chunks: List[Document]):
        if os.path.exists(self.db_path) and os.listdir(self.db_path):
            print("📦 Loading existing vector DB...")
            self.vector_db = Chroma(persist_directory=self.db_path, embedding_function=self.embeddings)
            docs = self.vector_db.get()
            self.loaded_files = list(set(m.get('source') for m in docs['metadatas'] if m.get('source')))
            return
        print("🧠 Creating new vector DB...")
        self.vector_db = Chroma.from_documents(chunks, self.embeddings, persist_directory=self.db_path)

    def load_local_context(self, folder_path: str) -> bool:
        if not os.path.exists(folder_path): return False
        current_state = self._get_library_state(folder_path)
        needs_reindex = True
        if os.path.exists(self.manifest_path):
            try:
                with open(self.manifest_path, 'r') as f:
                    saved_state = json.load(f)
                if current_state == saved_state: needs_reindex = False
            except Exception: needs_reindex = True

        if not needs_reindex:
            print("✨ Library in sync. Loading cached index...")
            self.load_or_create_db([])
        else:
            print("🔄 Changes detected. Refreshing library index...")
            if os.path.exists(self.db_path): shutil.rmtree(self.db_path)
            os.makedirs(self.db_path, exist_ok=True)
            all_docs = []
            for file in current_state.keys():
                file_path = os.path.join(folder_path, file)
                try:
                    try:
                        loader = PyPDFLoader(file_path)
                        docs = loader.load()
                        if len("".join([d.page_content for d in docs]).strip()) < 50:
                            docs = self._ocr_pdf(file_path)
                    except Exception: docs = self._ocr_pdf(file_path)
                    if not docs: continue
                    for d in docs:
                        d.page_content = self._clean_text(d.page_content)
                        d.metadata["source"] = file
                    all_docs.extend(docs)
                    print(f"  ✅ Indexed: {file}")
                except Exception as e: print(f"  ❌ Error on {file}: {e}")
            if not all_docs: return False
            chunks = self.splitter.split_documents(all_docs)
            self.load_or_create_db(chunks)
            with open(self.manifest_path, 'w') as f: json.dump(current_state, f)

        db_data = self.vector_db.get()
        all_chunks = [Document(page_content=t, metadata=m) for t, m in zip(db_data['documents'], db_data['metadatas'])]
        self.bm25_retriever = BM25Retriever.from_documents(all_chunks)
        self.bm25_retriever.k = 10
        return True

    def query(self, question: str) -> Dict[str, Any]:
        start = time.time()
        q_lower = question.lower().strip()

        # --- IDENTITY & CAPABILITY CHECK ---
        if "what can you do" in q_lower or "who are you" in q_lower:
            return {
                "answer": "I am a DevDocs Agent! 🚀 My mission is to help you understand developer tools documentation better. I can analyze the PDFs in your local library to answer complex technical questions or provide summaries.",
                "sources": [], "latency": round(time.time() - start, 2)
            }

        if self._is_malicious(question): 
            return {"answer": "Whoops! I can't do that. 😊", "sources": [], "latency": 0}

        if self._is_greeting(q_lower):
            return {"answer": "Hey! I'm ready. Ask me about your technical docs or developer tools.", "sources": [], "latency": 0}

        if not self.vector_db: 
            return {"answer": "I don't have any docs yet! Please upload technical PDFs to your 'docs' folder.", "sources": [], "latency": 0}

        # Retrieval
        focused_file = self._extract_file_filter(question)
        search_kwargs = {"k": 6}
        if focused_file: search_kwargs["filter"] = {"source": focused_file}

        ensemble = EnsembleRetriever(
            retrievers=[self.vector_db.as_retriever(search_kwargs=search_kwargs), self.bm25_retriever],
            weights=[0.7, 0.3]
        )
        raw_docs = ensemble.invoke(question)
        unique_docs = list({d.page_content: d for d in raw_docs}.values())
        
        context = ""
        if unique_docs:
            context = "\n\n".join(f"[SOURCE: {d.metadata.get('source')}]\n{d.page_content}" for d in unique_docs)

        # Generation
        response = self.llm.invoke(self._build_prompt(question, context))
        self.chat_history.append({"user": question, "assistant": response})
        self.chat_history = self.chat_history[-3:]

        return {
            "answer": response.strip(),
            "sources": list(set(d.metadata.get("source") for d in unique_docs)) if context else [],
            "latency": round(time.time() - start, 2)
        }