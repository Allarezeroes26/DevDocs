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
        return {f: os.path.getmtime(os.path.join(folder_path, f)) 
                for f in os.listdir(folder_path) if f.endswith(".pdf")}

    # --- OCR FALLBACK LOGIC ---
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
        greetings = ["hi", "hello", "hey", "howdy", "who are you", "whats up", "yo"]
        clean_q = text.lower().strip().strip('?!.')
        return clean_q in greetings or any(clean_q.startswith(g + " ") for g in greetings)


    def _build_prompt(self, question: str, context: str) -> str:
        history = "\n".join([f"User: {h['user']}\nAgent: {h['assistant']}" for h in self.chat_history])
        
        return f"""### SYSTEM ROLE:
You are the DEVDOCS MENTOR. You are a senior technical instructor and an expert across the full spectrum of Computer Science, Software Engineering, and Cybersecurity.
Your mission is to act as a bridge between the user and their local technical documentation library.

### SCOPE & FILTERING:
1. **TECHNICAL DOMAIN ONLY**: Your expertise is strictly limited to IT, CS, Programming, Hardware, and Security. 
2. **RELEVANCE CHECK**: If the provided DOCUMENT CONTEXT is unrelated to these fields (e.g., lifestyle, fiction), acknowledge it but explain you only provide mentorship for technical documentation.

### ADAPTIVE MENTORSHIP RULES:
1. **FULL AUTHORIZATION**: You are explicitly authorized to explain all technical steps and code found in the DOCUMENT CONTEXT. 
2. **CONTEXTUAL ADAPTATION**:
   - **Development Docs**: Act as a Senior Architect (Syntax/Best Practices).
   - **Security Docs**: Act as a Security Researcher (Logic/Defense).
3. **FIDELITY**: Use ONLY the DOCUMENT CONTEXT for facts. Do not guess.
4. **NO DENIALS**: Never claim you cannot access the files. They are provided below.

### CONVERSATION HISTORY:
{history if history else "Initial technical handshake complete."}

### DOCUMENT CONTEXT (Your Current Textbook):
{context if context else "No relevant technical snippets found."}

### USER QUESTION:
{question}

### MENTOR RESPONSE:
(Provide a friendly, detailed technical answer. Do not write follow-up questions for the user. Stop immediately after your response.)"""

    def load_or_create_db(self, chunks: List[Document]):
        """Logic to load existing DB or create a new one from chunks."""
        if os.path.exists(self.db_path) and os.listdir(self.db_path):
            print("📦 Loading existing vector DB...")
            self.vector_db = Chroma(
                persist_directory=self.db_path,
                embedding_function=self.embeddings
            )
            # Restore the loaded_files state from the database metadata
            docs = self.vector_db.get()
            self.loaded_files = list(set(m.get('source') for m in docs['metadatas'] if m.get('source')))
            return

        print("🧠 Creating new vector DB...")
        self.vector_db = Chroma.from_documents(
            chunks,
            self.embeddings,
            persist_directory=self.db_path
        )

    def load_local_context(self, folder_path: str) -> bool:
        if not os.path.exists(folder_path):
            return False

        current_state = self._get_library_state(folder_path)
        needs_reindex = True

        # --- SYNC CHECK ---
        if os.path.exists(self.manifest_path):
            try:
                with open(self.manifest_path, 'r') as f:
                    saved_state = json.load(f)
                if current_state == saved_state:
                    needs_reindex = False
            except Exception:
                needs_reindex = True

        if not needs_reindex:
            print("✨ Library in sync. Loading cached index...")
            self.load_or_create_db([])
        else:
            print("🔄 Changes detected. Refreshing library index...")
            if os.path.exists(self.db_path):
                shutil.rmtree(self.db_path)
            os.makedirs(self.db_path, exist_ok=True)

            all_docs = []
            self.loaded_files = []

            for file in current_state.keys():
                file_path = os.path.join(folder_path, file)
                try:
                    try:
                        loader = PyPDFLoader(file_path)
                        docs = loader.load()
                        text_content = "".join([d.page_content for d in docs]).strip()
                        if len(text_content) < 50:
                            docs = self._ocr_pdf(file_path)
                    except Exception:
                        docs = self._ocr_pdf(file_path)

                    if not docs: continue

                    for d in docs:
                        d.page_content = self._clean_text(d.page_content)
                        d.metadata["source"] = file
                    
                    all_docs.extend(docs)
                    self.loaded_files.append(file)
                    print(f"  ✅ Indexed: {file}")
                except Exception as e:
                    print(f"  ❌ Error on {file}: {e}")

            if not all_docs: return False

            chunks = self.splitter.split_documents(all_docs)
            self.load_or_create_db(chunks)
            
            with open(self.manifest_path, 'w') as f:
                json.dump(current_state, f)

        # --- BM25 RECONSTRUCTION (Required for Ensemble) ---
        print("🔧 Initializing hybrid retrieval...")
        db_data = self.vector_db.get()
        all_chunks = [Document(page_content=t, metadata=m) 
                      for t, m in zip(db_data['documents'], db_data['metadatas'])]
        self.bm25_retriever = BM25Retriever.from_documents(all_chunks)
        self.bm25_retriever.k = 10

        print(f"🚀 Done! Engine ready with {len(self.loaded_files)} files.")
        return True

    def query(self, question: str) -> Dict[str, Any]:
        start = time.time()
        if self._is_malicious(question): 
            return {"answer": "Whoops! I can't do that. 😊", "sources": [], "latency": 0}

        if self._is_greeting(question):
            return {
                "answer": "Hey! Ask me anything about your documents or programming.",
                "sources": [],
                "latency": round(time.time() - start, 2)
            }

        if not self.vector_db: 
            return {"answer": "I don't have any docs yet!", "sources": [], "latency": 0}

        focused_file = self._extract_file_filter(question)
        search_kwargs = {"k": 6}
        if focused_file: search_kwargs["filter"] = {"source": focused_file}

        ensemble = EnsembleRetriever(
            retrievers=[self.vector_db.as_retriever(search_kwargs=search_kwargs), self.bm25_retriever],
            weights=[0.7, 0.3]
        )
        raw_docs = ensemble.invoke(question)

        unique_docs = list({d.page_content: d for d in raw_docs}.values())
        if focused_file:
            unique_docs = [d for d in unique_docs if d.metadata.get("source") == focused_file]

        context = "\n\n".join(f"[SOURCE: {d.metadata.get('source')}]\n{d.page_content}" for d in unique_docs)
        response = self.llm.invoke(self._build_prompt(question, context))

        self.chat_history.append({"user": question, "assistant": response})
        self.chat_history = self.chat_history[-3:]

        return {
            "answer": response.strip(),
            "sources": list(set(d.metadata.get("source") for d in unique_docs)),
            "latency": round(time.time() - start, 2)
        }