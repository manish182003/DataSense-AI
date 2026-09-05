"""
Context Store & Fast Hybrid RAG Engine
Optimized for ultra-low latency using parallel dense/sparse search, candidate pruning, and Cross-Encoder reranking.
"""

import os
import re
import uuid
import numpy as np
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor
import pypdf
from app.schemas.payload import RetrievedChunk

# Set low-memory environment variables for PyTorch & OpenMP
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

_EMBED_MODEL = None
_RERANK_MODEL = None
_THREAD_POOL = ThreadPoolExecutor(max_workers=2)

def get_embed_model():
    global _EMBED_MODEL
    if _EMBED_MODEL is None:
        import torch
        torch.set_num_threads(1)
        torch.set_grad_enabled(False)
        from sentence_transformers import SentenceTransformer
        _EMBED_MODEL = SentenceTransformer('BAAI/bge-small-en-v1.5')
    return _EMBED_MODEL

def get_rerank_model():
    global _RERANK_MODEL
    if _RERANK_MODEL is None:
        import torch
        torch.set_num_threads(1)
        torch.set_grad_enabled(False)
        from sentence_transformers import CrossEncoder
        _RERANK_MODEL = CrossEncoder('BAAI/bge-reranker-base')
    return _RERANK_MODEL

class ContextStore:
    def __init__(self):
        self.documents: Dict[str, Dict[str, Any]] = {}
        self.chunks: List[Dict[str, Any]] = []
        self.bm25: Optional[Any] = None
        self.faiss_index: Optional[Any] = None
        self.vector_dimension: int = 384

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
            self.faiss_index = None
            return

        texts = [c["text"] for c in self.chunks]

        # 1. Build Sparse Index (BM25)
        from rank_bm25 import BM25Okapi
        import faiss

        tokenized_corpus = [re.findall(r'\w+', text.lower()) for text in texts]
        self.bm25 = BM25Okapi(tokenized_corpus)

        # 2. Build Dense Index (FAISS Fast Inner Product)
        embedder = get_embed_model()
        embeddings = embedder.encode(texts, convert_to_numpy=True, normalize_embeddings=True).astype(np.float32)

        self.faiss_index = faiss.IndexFlatIP(self.vector_dimension)
        self.faiss_index.add(embeddings)

    def _dense_search(self, q_emb: np.ndarray, top_k: int) -> Dict[int, int]:
        D, I = self.faiss_index.search(q_emb, top_k)
        ranks = {}
        for rank, idx in enumerate(I[0]):
            if idx >= 0 and idx < len(self.chunks):
                ranks[idx] = rank + 1
        return ranks

    def _sparse_search(self, tokenized_query: List[str], top_k: int) -> Dict[int, int]:
        scores = self.bm25.get_scores(tokenized_query)
        top_indices = np.argsort(scores)[::-1][:top_k]
        ranks = {}
        for rank, idx in enumerate(top_indices):
            if scores[idx] > 0:
                ranks[idx] = rank + 1
        return ranks

    def hybrid_search(self, query: str, top_k_dense: int = 10, top_k_sparse: int = 10, final_top_k: int = 4) -> List[RetrievedChunk]:
        """
        Executes Parallel Dense (FAISS) + Sparse (BM25) search, RRF Fusion, and Cross-Encoder Reranking.
        """
        if not self.chunks or not self.faiss_index or not self.bm25:
            return []

        embedder = get_embed_model()
        q_emb = embedder.encode([query], convert_to_numpy=True, normalize_embeddings=True).astype(np.float32)
        tokenized_query = re.findall(r'\w+', query.lower())

        # Parallel Dense & Sparse Search using ThreadPoolExecutor
        future_dense = _THREAD_POOL.submit(self._dense_search, q_emb, min(top_k_dense, len(self.chunks)))
        future_sparse = _THREAD_POOL.submit(self._sparse_search, tokenized_query, min(top_k_sparse, len(self.chunks)))

        dense_ranks = future_dense.result()
        sparse_ranks = future_sparse.result()

        # Reciprocal Rank Fusion (RRF)
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

        fused_indices = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)[:8]

        if not fused_indices:
            return []

        # Cross-Encoder Reranking
        fused_chunks = [self.chunks[i] for i in fused_indices]
        cross_pairs = [[query, chunk["text"]] for chunk in fused_chunks]
        
        reranker = get_rerank_model()
        rerank_scores = reranker.predict(cross_pairs)

        results = []
        for i, chunk in enumerate(fused_chunks):
            results.append(RetrievedChunk(
                chunk_id=chunk["chunk_id"],
                source_doc=chunk["source_doc"],
                page_number=chunk["page_number"],
                text=chunk["text"],
                rrf_score=round(float(rrf_scores[fused_indices[i]]), 4),
                rerank_score=round(float(rerank_scores[i]), 4)
            ))

        results.sort(key=lambda x: x.rerank_score, reverse=True)
        top_results = results[:final_top_k]

        # Expand neighboring chunks for top results to ensure complete context
        return self.expand_neighbor_chunks(top_results)

    def expand_neighbor_chunks(self, retrieved_chunks: List[RetrievedChunk]) -> List[RetrievedChunk]:
        """
        Includes adjacent preceding/succeeding neighbor chunks from the same document for seamless context continuity.
        """
        if not retrieved_chunks or not self.chunks:
            return retrieved_chunks

        # Map chunk_id to index in self.chunks
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

            # Neighbor candidates: idx - 1, idx, idx + 1
            candidate_indices = [idx - 1, idx, idx + 1]
            merged_texts = []

            for c_idx in candidate_indices:
                if 0 <= c_idx < len(self.chunks) and self.chunks[c_idx]["doc_id"] == doc_id:
                    merged_texts.append(self.chunks[c_idx]["text"])

            # Compress text by removing duplicate sentences
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
