"""
Long-term memory manager — ChromaDB only.

Two Chroma collections per deployment:
  mem_{client_id}  — one embedded doc per conversation turn
  user_summaries   — one summary doc per user (document ID == client_id)

Graceful degradation:
  - If Chroma / Ollama embedding unavailable → all memory ops are silent no-ops
  - Never raises to the caller
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_SUMMARY_PROMPT = (
    "You are a memory assistant. Your task is to maintain a concise, factual memory "
    "profile for a user. Given the existing memory and new conversation turns, produce "
    "an UPDATED memory (maximum 400 words). Cover: name/nickname, preferred language, "
    "occupation/job, hobbies, location, key facts, past decisions, and recurring topics. "
    "Output ONLY the updated memory text — no commentary, no headings."
)

_SUMMARIES_COLLECTION = "user_summaries"


class MemoryManager:
    """
    ChromaDB-backed long-term memory, scoped per client_id.

    Collections:
      mem_{client_id}  — embedded conversation turns (one doc per turn)
      user_summaries   — one summary doc per user (ID == client_id)
    """

    CHROMA_PERSIST_DIR = "artifacts/chroma"
    TOP_K_RETRIEVAL = 5
    RECENT_TURNS_LIMIT = 20
    SUMMARY_INTERVAL_TURNS = 5  # run LLM summary every N complete turns

    def __init__(
        self,
        ollama_base_url: str = "http://localhost:11434",
        model_name: str = "mistral",
        embed_model: str = "nomic-embed-text",
        chroma_persist_dir: str | None = None,
    ) -> None:
        self._chroma_persist_dir = chroma_persist_dir or self.CHROMA_PERSIST_DIR
        self._ollama_base_url = ollama_base_url
        self._model_name = model_name
        self._embed_model = embed_model

        self._chroma_client: Any = None
        self._embeddings: Any = None
        self._chat_llm: Any = None
        self._chroma_available = False

        self._init_chroma(ollama_base_url, embed_model)
        self._init_llm(ollama_base_url, model_name)

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------

    def _init_chroma(self, ollama_base_url: str, embed_model: str) -> None:
        try:
            import chromadb
            from langchain_ollama import OllamaEmbeddings

            persist_dir = Path(self._chroma_persist_dir)
            persist_dir.mkdir(parents=True, exist_ok=True)

            self._embeddings = OllamaEmbeddings(
                model=embed_model,
                base_url=ollama_base_url,
            )
            self._chroma_client = chromadb.PersistentClient(path=str(persist_dir))
            self._chroma_available = True
            logger.info("[MemoryManager] ChromaDB initialized at '%s'", persist_dir)
        except Exception as exc:
            logger.warning("[MemoryManager] Chroma/embedding unavailable — memory disabled: %s", exc)
            self._chroma_available = False

    def _init_llm(self, ollama_base_url: str, model_name: str) -> None:
        try:
            from langchain_ollama import ChatOllama

            self._chat_llm = ChatOllama(
                model=model_name,
                base_url=ollama_base_url,
                temperature=0.2,
            )
            logger.info("[MemoryManager] ChatOllama initialized (model=%s)", model_name)
        except Exception as exc:
            logger.warning("[MemoryManager] ChatOllama unavailable: %s", exc)
            self._chat_llm = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load_context(self, client_id: str, current_query: str) -> list[dict[str, str]]:
        """
        Return system-role messages to prepend to the LLM context.
        Returns [] gracefully if Chroma is unavailable.
        """
        if not self._chroma_available:
            return []

        messages: list[dict[str, str]] = []

        summary = self._load_summary(client_id)
        if summary:
            messages.append({
                "role": "system",
                "content": f"[Long-term memory about this user]\n{summary}",
            })

        relevant_turns = self._retrieve_similar_turns(client_id, current_query)
        if relevant_turns:
            turns_text = "\n".join(
                f"{t['role'].capitalize()}: {t['content']}" for t in relevant_turns
            )
            messages.append({
                "role": "system",
                "content": f"[Relevant past conversation turns]\n{turns_text}",
            })

        return messages

    def save_exchange(
        self,
        client_id: str,
        session_id: str,
        user_msg: str,
        assistant_msg: str,
    ) -> None:
        """
        Embed and persist a completed user<->assistant exchange into Chroma.
        Called synchronously after each response; failures are swallowed.
        """
        if not self._chroma_available:
            return
        self._embed_turns(client_id, session_id, user_msg, assistant_msg)

    def run_summary_update(self, client_id: str) -> None:
        """
        Background task: regenerate the user memory summary via LLM and store
        the result back into the user_summaries Chroma collection.

        Only triggers the LLM every SUMMARY_INTERVAL_TURNS complete turns
        (i.e. every SUMMARY_INTERVAL_TURNS * 2 Chroma documents) to avoid
        running a full LLM call after every single message.
        """
        if not self._chroma_available or self._chat_llm is None:
            return

        # Throttle: only update summary every N turns (each turn = 2 docs)
        turns_collection = self._turns_collection(client_id)
        if turns_collection is not None:
            doc_count = turns_collection.count()
            interval = self.SUMMARY_INTERVAL_TURNS * 2
            if doc_count == 0 or doc_count % interval != 0:
                return

        recent = self._get_recent_turns(client_id, self.RECENT_TURNS_LIMIT)
        if not recent:
            return

        existing_summary = self._load_summary(client_id) or ""
        turns_text = "\n".join(
            f"{m['role'].capitalize()}: {m['content']}" for m in recent
        )

        try:
            from langchain_core.messages import HumanMessage, SystemMessage

            user_content = (
                f"Existing memory:\n{existing_summary}\n\nNew conversation turns:\n{turns_text}"
                if existing_summary
                else f"Conversation turns:\n{turns_text}"
            )
            result = self._chat_llm.invoke([
                SystemMessage(content=_SUMMARY_PROMPT),
                HumanMessage(content=user_content),
            ])
            new_summary = result.content.strip()
            if new_summary:
                self._upsert_summary(client_id, new_summary)
                logger.info(
                    "[MemoryManager] Summary updated for client_id='%s' (%d chars)",
                    client_id, len(new_summary),
                )
        except Exception as exc:
            logger.warning("[MemoryManager] Summary update failed for client_id='%s': %s", client_id, exc)

    # ------------------------------------------------------------------
    # Chroma: conversation turns collection
    # ------------------------------------------------------------------

    def _turns_collection(self, client_id: str) -> Any | None:
        try:
            # ChromaDB collection names must be 3-63 chars; apply slice to the
            # full string (including the "mem_" prefix) to guarantee the limit.
            safe = ("mem_" + "".join(c if c.isalnum() else "_" for c in client_id))[:63]
            return self._chroma_client.get_or_create_collection(safe)
        except Exception as exc:
            logger.warning("[MemoryManager] Chroma turns collection error: %s", exc)
            return None

    def _embed_turns(
        self, client_id: str, session_id: str, user_msg: str, assistant_msg: str
    ) -> None:
        collection = self._turns_collection(client_id)
        if collection is None:
            return
        try:
            now_ts = datetime.now(tz=timezone.utc).isoformat()
            docs = [user_msg, assistant_msg]
            embeddings = self._embeddings.embed_documents(docs)
            ids = [f"{session_id}_user_{now_ts}", f"{session_id}_asst_{now_ts}"]
            metadatas = [
                {"client_id": client_id, "session_id": session_id, "role": "user", "timestamp": now_ts},
                {"client_id": client_id, "session_id": session_id, "role": "assistant", "timestamp": now_ts},
            ]
            collection.add(embeddings=embeddings, documents=docs, ids=ids, metadatas=metadatas)
        except Exception as exc:
            logger.warning("[MemoryManager] Chroma embed failed: %s", exc)

    def _get_recent_turns(self, client_id: str, limit: int) -> list[dict[str, str]]:
        """Retrieve the most recent N turns for a user, sorted by timestamp."""
        collection = self._turns_collection(client_id)
        if collection is None or collection.count() == 0:
            return []
        try:
            result = collection.get(
                where={"client_id": {"$eq": client_id}},
                include=["documents", "metadatas"],
            )
            paired = sorted(
                zip(result["documents"], result["metadatas"]),
                key=lambda x: x[1].get("timestamp", ""),
            )
            recent = paired[-limit:]
            return [{"role": m.get("role", "user"), "content": doc} for doc, m in recent]
        except Exception as exc:
            logger.warning("[MemoryManager] Chroma recent turns failed: %s", exc)
            return []

    def _retrieve_similar_turns(self, client_id: str, query: str) -> list[dict[str, str]]:
        """Retrieve top-K semantically similar past turns for the current query."""
        if not query:
            return []
        collection = self._turns_collection(client_id)
        if collection is None or collection.count() == 0:
            return []
        try:
            query_embedding = self._embeddings.embed_query(query)
            n_results = min(self.TOP_K_RETRIEVAL, collection.count())
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                include=["documents", "metadatas"],
            )
            return [
                {"role": meta.get("role", "user"), "content": doc}
                for doc, meta in zip(results["documents"][0], results["metadatas"][0])
            ]
        except Exception as exc:
            logger.warning("[MemoryManager] Chroma retrieval failed: %s", exc)
            return []

    # ------------------------------------------------------------------
    # Chroma: summaries collection
    # ------------------------------------------------------------------

    def _summaries_collection(self) -> Any | None:
        """Shared collection holding one summary document per user (ID == client_id)."""
        try:
            return self._chroma_client.get_or_create_collection(_SUMMARIES_COLLECTION)
        except Exception as exc:
            logger.warning("[MemoryManager] Chroma summaries collection error: %s", exc)
            return None

    def _load_summary(self, client_id: str) -> str | None:
        collection = self._summaries_collection()
        if collection is None:
            return None
        try:
            result = collection.get(ids=[client_id], include=["documents"])
            docs = result.get("documents") or []
            return docs[0] if docs and docs[0] else None
        except Exception as exc:
            logger.warning("[MemoryManager] Chroma summary load failed: %s", exc)
            return None

    def _upsert_summary(self, client_id: str, memory_text: str) -> None:
        collection = self._summaries_collection()
        if collection is None:
            return
        try:
            now_ts = datetime.now(tz=timezone.utc).isoformat()
            embedding = self._embeddings.embed_documents([memory_text])[0]
            existing = collection.get(ids=[client_id], include=["documents"])
            has_existing = bool(existing.get("documents") and existing["documents"][0])
            if has_existing:
                collection.update(
                    ids=[client_id],
                    documents=[memory_text],
                    embeddings=[embedding],
                    metadatas=[{"client_id": client_id, "updated_at": now_ts}],
                )
            else:
                collection.add(
                    ids=[client_id],
                    documents=[memory_text],
                    embeddings=[embedding],
                    metadatas=[{"client_id": client_id, "updated_at": now_ts}],
                )
        except Exception as exc:
            logger.warning("[MemoryManager] Chroma summary upsert failed: %s", exc)
