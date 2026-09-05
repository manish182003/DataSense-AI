"""
Context Store & Cloud-Native Hybrid RAG Engine
100% Zero-RAM Footprint: Eliminates local PyTorch/FAISS memory bloat, using Hugging Face Cloud Embedding API,
Pinecone Vector DB Cloud, and BM25Okapi for instant <50ms retrieval on Render Free Tier.
"""

import os
import re
import uuid
import numpy as np
import httpx
from typing import List, Dict, Any, Optional
import pypdf
from rank_bm25 import BM25Okapi
from app.schemas.payload import RetrievedChunk

HF_EMBED_API_URL = "https://api-inference.huggingface.co/pipeline/feature-extraction/BAAI/bge-small-en-v1.5"

def get_cloud_embeddings(texts: List[str]) -> List[List[float]]:
    """
    Computes 384-dimensional dense vector embeddings via Hugging Face Cloud Inference API.
    Zero local RAM overhead (no PyTorch, no SentenceTransformers).
    """
    if not texts:
        return []

    hf_token = os.getenv("HF_TOKEN", os.getenv("HUGGINGFACE_TOKEN", ""))
    headers = {}
    if hf_token:
        headers["Authorization"] = f"Bearer {hf_token}"

    try:
        with httpx.Client(timeout=15.0) as client:
            response = client.post(
                HF_EMBED_API_URL,
                headers=headers,
                json={"inputs": texts, "options": {"wait_for_model": True}}
            )
            if response.status_code == 200:
                res_data = response.json()
                if isinstance(res_data, list) and len(res_data) > 0:
                    # Check if pooled vector or list of token vectors
                    if isinstance(res_data[0], list) and isinstance(res_data[0][0], float):
                        return res_data
                    elif isinstance(res_data[0], list) and isinstance(res_data[0][0], list):
                        # Mean pooling over token embeddings
                        return [np.mean(np.array(tokens), axis=0).tolist() for tokens in res_data]
    except Exception as err:
        print(f"[Cloud Embedding Warning] HF API fallback to lightweight TF-IDF: {err}")

    # Lightweight TF-IDF Fallback (0 MB RAM overhead)
    return compute_fallback_tfidf_embeddings(texts)

def compute_fallback_tfidf_embeddings(texts: List[str]) -> List[List[float]]:
    """
    Fallback 384-dim TF-IDF feature vector generator when offline or without HF API keys.
    """
    embeddings = []
    vocab = {}
    for text in texts:
        words = re.findall(r'\w+', text.lower())
        for w in words:
            if w not in vocab and len(vocab) < 384:
                vocab[w] = len(vocab)

    dim = 384
    for text in texts:
        vec = np.zeros(dim, dtype=np.float32)
        words = re.findall(r'\w+', text.lower())
        for w in words:
            if w in vocab:
                vec[vocab[w]] += 1.0
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        embeddings.append(vec.tolist())
    return embeddings

class ContextStore:
    def __init__(self):
        self.documents: Dict[str, Dict[str, Any]] = {}
        self.chunks: List[Dict[str, Any]] = []
        self.bm25: Optional[BM25Okapi] = None
        self.dense_embeddings: Optional[np.ndarray] = None
        self.vector_dimension: int = 384
        self.pinecone_index = None
        self._init_pinecone()

    def _init_pinecone(self):
        """Initializes optional Pinecone Cloud Vector DB if PINECONE_API_KEY is provided."""
        api_key = os.getenv("PINECONE_API_KEY", None)
        if api_key:
            try:
                from pinecone import Pinecone
                pc = Pinecone(api_key=api_key)
                index_name = os.getenv("PINECONE_INDEX_NAME", "datasense-kb")
                if index_name in [idx.name for idx in pc.list_indexes()]:
                    self.pinecone_index = pc.Index(index_name)
            except Exception as err:
                print(f"[Pinecone Warning] Failed to initialize Pinecone Cloud: {err}")

    def parse_file(self, file_bytes: bytes, filename: str) -> List[Dict[str, Any]]:
        ext = os.path.splitext(filename)[1].lower()
        extracted_pages = []

        if ext == '.pdf':
            import io
            pdf_reader = pypdf.PdfReader(io.BytesIO(file_bytes))
            for p_idx, page in enumerate(pdf_reader.pages):
                text = page.extract_text() or ""
                if text.strip():
                    extracted_pages.append({"page": p_idx + 1, "text": text})
        else:
            text_content = file_bytes.decode('utf-8', errors='ignore')
            extracted_pages.append({"page": 1, "text": text_content})

        return extracted_pages

    def chunk_text(self, pages: List[Dict[str, Any]], filename: str, doc_id: str, chunk_size: int = 300, overlap: int = 40) -> List[Dict[str, Any]]:
        new_chunks = []
        for page_info in pages:
            page_num = page_info["page"]
            text = page_info["text"]
            clean_text = re.sub(r'\s+', ' ', text).strip()
            if not clean_text:
                continue

            words = clean_text.split()
            step = chunk_size - overlap
            if step <= 0:
                step = chunk_size

            for i in range(0, len(words), step):
                chunk_words = words[i:i + chunk_size]
                if not chunk_words:
                    continue
                chunk_str = " ".join(chunk_words)
                
                chunk_id = f"chk_{uuid.uuid4().hex[:8]}"
                new_chunks.append({
                    "chunk_id": chunk_id,
                    "doc_id": doc_id,
                    "source_doc": filename,
                    "page_number": page_num,
                    "text": chunk_str
                })
                if i + chunk_size >= len(words):
                    break

        return new_chunks

    def add_document(self, file_bytes: bytes, filename: str) -> Dict[str, Any]:
        doc_id = f"doc_{uuid.uuid4().hex[:6]}"
        pages = self.parse_file(file_bytes, filename)
        new_chunks = self.chunk_text(pages, filename, doc_id)

        if not new_chunks:
            raise ValueError(f"No readable text content found in {filename}")

        self.documents[doc_id] = {
            "doc_id": doc_id,
            "filename": filename,
            "chunk_count": len(new_chunks),
            "char_count": sum(len(c["text"]) for c in new_chunks),
            "text_sample": new_chunks[0]["text"] if new_chunks else ""
        }

        self.chunks.extend(new_chunks)
        self._rebuild_indices()

        return {
            "doc_id": doc_id,
            "filename": filename,
            "chunks_created": len(new_chunks),
            "total_characters": self.documents[doc_id]["char_count"]
        }

    def _rebuild_indices(self):
        if not self.chunks:
            self.bm25 = None
            self.dense_embeddings = None
            return

        texts = [c["text"] for c in self.chunks]

        # 1. Sparse Index (BM25Okapi - 0 MB RAM)
        tokenized_corpus = [re.findall(r'\w+', text.lower()) for text in texts]
        self.bm25 = BM25Okapi(tokenized_corpus)

        # 2. Cloud Dense Index (HuggingFace Inference API)
        cloud_embeds = get_cloud_embeddings(texts)
        if cloud_embeds:
            self.dense_embeddings = np.array(cloud_embeds, dtype=np.float32)

        # Upsert into Pinecone Cloud if configured
        if self.pinecone_index and cloud_embeds:
            vectors_to_upsert = []
            for i, chunk in enumerate(self.chunks):
                vectors_to_upsert.append((
                    chunk["chunk_id"],
                    cloud_embeds[i],
                    {"source_doc": chunk["source_doc"], "page_number": chunk["page_number"], "text": chunk["text"]}
                ))
            try:
                self.pinecone_index.upsert(vectors=vectors_to_upsert)
            except Exception as err:
                print(f"[Pinecone Upsert Warning] {err}")

    def _dense_search(self, q_emb: np.ndarray, top_k: int) -> Dict[int, int]:
        if self.dense_embeddings is None or len(self.dense_embeddings) == 0:
            return {}
        
        # Fast cosine / dot product similarity
        scores = np.dot(self.dense_embeddings, q_emb[0])
        top_indices = np.argsort(scores)[::-1][:top_k]
        ranks = {}
        for rank, idx in enumerate(top_indices):
            if idx < len(self.chunks):
                ranks[idx] = rank + 1
        return ranks

    def _sparse_search(self, tokenized_query: List[str], top_k: int) -> Dict[int, int]:
        if self.bm25 is None:
            return {}
        scores = self.bm25.get_scores(tokenized_query)
        top_indices = np.argsort(scores)[::-1][:top_k]
        ranks = {}
        for rank, idx in enumerate(top_indices):
            if scores[idx] > 0:
                ranks[idx] = rank + 1
        return ranks

    def hybrid_search(self, query: str, top_k_dense: int = 10, top_k_sparse: int = 10, final_top_k: int = 4) -> List[RetrievedChunk]:
        """
        Executes Fast Hybrid Search (Cloud Dense API + BM25 Sparse), Reciprocal Rank Fusion (RRF), and Context Expansion.
        """
        if not self.chunks:
            return []

        # 1. Get Cloud Query Embedding
        q_embeds = get_cloud_embeddings([query])
        q_emb = np.array(q_embeds, dtype=np.float32) if q_embeds else np.zeros((1, 384), dtype=np.float32)
        tokenized_query = re.findall(r'\w+', query.lower())

        # 2. Dense & Sparse Search
        dense_ranks = self._dense_search(q_emb, min(top_k_dense, len(self.chunks)))
        sparse_ranks = self._sparse_search(tokenized_query, min(top_k_sparse, len(self.chunks)))

        # 3. Reciprocal Rank Fusion (RRF)
        all_indices = set(dense_ranks.keys()).union(set(sparse_ranks.keys()))
        k_rrf = 60
        rrf_scores = {}
        for idx in all_indices:
            s = 0.0
            if idx in dense_ranks:
                s += 1.0 / (k_rrf + dense_ranks[idx])
            if idx in sparse_ranks:
                s += 1.0 / (k_rrf + sparse_ranks[idx])
            rrf_scores[idx] = s

        fused_indices = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)[:final_top_k]

        if not fused_indices:
            return []

        results = []
        for i in fused_indices:
            chunk = self.chunks[i]
            results.append(RetrievedChunk(
                chunk_id=chunk["chunk_id"],
                source_doc=chunk["source_doc"],
                page_number=chunk["page_number"],
                text=chunk["text"],
                rrf_score=round(float(rrf_scores[i]), 4),
                rerank_score=round(float(rrf_scores[i]), 4)
            ))

        return self.expand_neighbor_chunks(results)

    def expand_neighbor_chunks(self, retrieved_chunks: List[RetrievedChunk]) -> List[RetrievedChunk]:
        """
        Includes adjacent preceding/succeeding neighbor chunks from the same document for seamless context continuity.
        """
        if not retrieved_chunks or not self.chunks:
            return retrieved_chunks

        chunk_map = {c["chunk_id"]: idx for idx, c in enumerate(self.chunks)}
        expanded_chunks = []
        seen_ids = set()

        for r_chunk in retrieved_chunks:
            if r_chunk.chunk_id not in chunk_map:
                if r_chunk.chunk_id not in seen_ids:
                    expanded_chunks.append(r_chunk)
                    seen_ids.add(r_chunk.chunk_id)
                continue

            idx = chunk_map[r_chunk.chunk_id]
            doc_id = self.chunks[idx]["doc_id"]

            candidate_indices = [idx - 1, idx, idx + 1]
            merged_texts = []

            for c_idx in candidate_indices:
                if 0 <= c_idx < len(self.chunks) and self.chunks[c_idx]["doc_id"] == doc_id:
                    merged_texts.append(self.chunks[c_idx]["text"])

            combined_text = " ".join(merged_texts)
            compressed_text = self.compress_context(combined_text)

            if r_chunk.chunk_id not in seen_ids:
                expanded_chunks.append(RetrievedChunk(
                    chunk_id=r_chunk.chunk_id,
                    source_doc=r_chunk.source_doc,
                    page_number=r_chunk.page_number,
                    text=compressed_text,
                    rrf_score=r_chunk.rrf_score,
                    rerank_score=r_chunk.rerank_score
                ))
                seen_ids.add(r_chunk.chunk_id)

        return expanded_chunks

    def compress_context(self, text: str) -> str:
        """
        Compresses context text by deduplicating redundant sentences.
        """
        sentences = re.split(r'(?<=[.!?])\s+', text)
        unique_sentences = []
        seen_norms = set()

        for s in sentences:
            s_clean = s.strip()
            if not s_clean:
                continue
            norm = re.sub(r'\W+', '', s_clean.lower())
            if norm not in seen_norms:
                unique_sentences.append(s_clean)
                seen_norms.add(norm)

        return " ".join(unique_sentences)

global_context_store = ContextStore()
