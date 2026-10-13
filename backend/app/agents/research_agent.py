import json
import re
import urllib.error
import urllib.request
from openai import OpenAI
from app.config import settings
from app.models import Document, FinancialMetric
from app.rag.vector_store import VectorStore


class ResearchAgent:
    """
    Advanced source-grounded Research Agent.

    Provider order in auto mode:
    1. OpenAI
    2. Local Ollama
    3. Deterministic source-grounded fallback

    All output remains tied to ChromaDB-retrieved report chunks.
    """

    MAX_SOURCES = 12
    MAX_HISTORY_MESSAGES = 8
    MAX_SOURCE_CHARACTERS = 1800

    TOPIC_RULES = [
        {
            "title": "Revenue and Sales",
            "keywords": [
                "revenue",
                "sales",
                "net sales",
                "total revenue",
            ],
        },
        {
            "title": "Profitability and Margins",
            "keywords": [
                "gross profit",
                "gross margin",
                "operating income",
                "operating margin",
                "net income",
                "profit",
                "margin",
            ],
        },
        {
            "title": "Debt",
            "keywords": [
                "debt",
                "indebtedness",
                "borrowings",
                "principal amount",
                "credit facility",
                "debt covenant",
                "maturity",
                "notes payable",
            ],
        },
        {
            "title": "Liquidity and Cash Flow",
            "keywords": [
                "liquidity",
                "cash",
                "cash equivalents",
                "cash flow",
                "working capital",
                "capital resources",
                "operating activities",
            ],
        },
        {
            "title": "Risk and Uncertainty",
            "keywords": [
                "risk",
                "uncertainty",
                "adverse",
                "vulnerability",
                "materially",
                "going concern",
                "material weakness",
            ],
        },
        {
            "title": "Legal and Regulatory Matters",
            "keywords": [
                "litigation",
                "legal proceeding",
                "class action",
                "regulatory",
                "investigation",
            ],
        },
    ]

    def __init__(self):
        self.vector_store = VectorStore()
        self.openai_client = None

        if settings.openai_api_key:
            try:
                self.openai_client = OpenAI(
                    api_key=settings.openai_api_key,
                    max_retries=1,
                    timeout=30.0,
                )
            except Exception:
                self.openai_client = None

    def answer(
        self,
        question: str,
        documents: list[Document],
        metrics: list[FinancialMetric],
        history: list[dict],
    ) -> dict:
        retrieval_queries = self.build_retrieval_queries(question)

        sources = self.retrieve_sources(
            documents=documents,
            queries=retrieval_queries,
        )

        relevant_metrics = self.find_relevant_metrics(
            question=question,
            metrics=metrics,
        )

        if not sources:
            return {
                "answer": (
                    "Not found in the selected documents. No relevant "
                    "source passages were retrieved."
                ),
                "reasoning_steps": [
                    "Used only selected uploaded reports.",
                    "Split the question into searchable financial topics.",
                    "Searched indexed report chunks.",
                    "No relevant evidence was found.",
                ],
                "metrics": [],
                "citations": [],
                "provider": "fallback",
            }

        evidence_text = self.format_evidence(
            sources=sources,
            metrics=relevant_metrics,
        )

        prompt = self.build_prompt(
            question=question,
            history=history,
            evidence_text=evidence_text,
        )

        model_text, provider = self.get_model_response(prompt)

        if model_text:
            result = self.parse_model_response(
                question=question,
                model_text=model_text,
                sources=sources,
            )

            provider_step = (
                f"Generated a cited analyst-style response using "
                f"the {provider} provider."
            )
        else:
            result = self.build_source_grounded_response(
                question=question,
                sources=sources,
            )

            provider = "fallback"
            provider_step = (
                "No external language model was available, so the system "
                "created a direct source-grounded evidence summary."
            )

        return {
            "answer": result["answer"],
            "reasoning_steps": [
                "Identified the financial topics in the question.",
                "Created multiple retrieval queries for multi-part topics.",
                "Retrieved evidence only from selected indexed reports.",
                "Selected source passages relevant to each requested topic.",
                "Validated citations against retrieved source IDs.",
                provider_step,
            ],
            "metrics": [
                {
                    "name": metric.metric_name,
                    "value": metric.metric_value,
                    "period": metric.period,
                    "source_page": metric.source_page,
                }
                for metric in relevant_metrics[:6]
            ],
            "citations": result["citations"],
            "provider": provider,
        }

    def get_model_response(
        self,
        prompt: str,
    ) -> tuple[str | None, str]:
        provider = settings.research_provider.lower().strip()

        if provider == "fallback":
            return None, "fallback"

        if provider in {"auto", "openai"} and self.openai_client:
            try:
                response = self.openai_client.responses.create(
                    model=settings.llm_model,
                    instructions=(
                        "You are a careful financial research assistant. "
                        "Answer only from supplied annual-report evidence."
                    ),
                    input=prompt,
                    temperature=settings.llm_temperature,
                )

                return response.output_text, "openai"
            except Exception:
                if provider == "openai":
                    return None, "openai"

        if provider in {"auto", "ollama"}:
            try:
                return self.call_ollama(prompt), "ollama"
            except Exception:
                return None, "ollama"

        return None, "fallback"

    def call_ollama(
        self,
        prompt: str,
    ) -> str:
        """
        Calls a local Ollama model without requiring another Python package.
        """

        payload = {
            "model": settings.ollama_model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {
                "temperature": settings.llm_temperature,
            },
        }

        request = urllib.request.Request(
            url=(
                settings.ollama_base_url.rstrip("/")
                + "/api/generate"
            ),
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(
                request,
                timeout=settings.ollama_timeout_seconds,
            ) as response:
                raw_response = response.read().decode("utf-8")
        except urllib.error.URLError as error:
            raise RuntimeError(
                "Local Ollama service is unavailable."
            ) from error

        result = json.loads(raw_response)
        text = result.get("response", "")

        if not text:
            raise RuntimeError("Ollama returned an empty response.")

        return text

    def build_retrieval_queries(self, question: str) -> list[str]:
        pieces = re.split(
            r",|\band\b|\bor\b|\bversus\b|\bcompare\b",
            question,
            flags=re.IGNORECASE,
        )

        queries = [question.strip()]

        for piece in pieces:
            cleaned = piece.strip()

            if (
                len(cleaned) >= 4
                and cleaned.lower() != question.strip().lower()
            ):
                queries.append(cleaned)

        question_lower = question.lower()

        for rule in self.TOPIC_RULES:
            for keyword in rule["keywords"]:
                if keyword in question_lower:
                    queries.append(keyword)

        unique_queries = []

        for query in queries:
            if query not in unique_queries:
                unique_queries.append(query)

        return unique_queries[:5]

    def retrieve_sources(
        self,
        documents: list[Document],
        queries: list[str],
    ) -> list[dict]:
        sources = []
        seen = set()

        for document in documents:
            for query in queries:
                chunks = self.vector_store.search_document(
                    document_id=document.id,
                    query=query,
                    limit=3,
                )

                for chunk in chunks:
                    key = (
                        document.id,
                        chunk["page"],
                        chunk["text"][:250],
                    )

                    if key in seen:
                        continue

                    seen.add(key)

                    sources.append(
                        {
                            "source_id": f"S{len(sources) + 1}",
                            "document_id": document.id,
                            "document_name": (
                                document.company_name
                                or document.original_filename
                            ),
                            "page": chunk["page"],
                            "excerpt": chunk["text"][
                                : self.MAX_SOURCE_CHARACTERS
                            ],
                        }
                    )

                    if len(sources) >= self.MAX_SOURCES:
                        return sources

        return sources

    def find_relevant_metrics(
        self,
        question: str,
        metrics: list[FinancialMetric],
    ) -> list[FinancialMetric]:
        question_words = {
            word.strip("?,.!:;()[]").lower()
            for word in question.split()
            if len(word) > 2
        }

        matches = []

        for metric in metrics:
            metric_words = set(metric.metric_name.lower().split())

            if question_words.intersection(metric_words):
                matches.append(metric)

        return matches or metrics[:5]

    def format_evidence(
        self,
        sources: list[dict],
        metrics: list[FinancialMetric],
    ) -> str:
        metric_lines = []

        for metric in metrics[:8]:
            metric_lines.append(
                f"- {metric.metric_name}: {metric.metric_value} "
                f"({metric.period or 'Annual report period'}, "
                f"page {metric.source_page})"
            )

        source_sections = []

        for source in sources:
            source_sections.append(
                f"[{source['source_id']}]\n"
                f"Document: {source['document_name']}\n"
                f"Page: {source['page']}\n"
                f"Excerpt: {source['excerpt']}"
            )

        return (
            "EXTRACTED METRICS:\n"
            + ("\n".join(metric_lines) or "No extracted metrics.")
            + "\n\nRETRIEVED SOURCE PASSAGES:\n"
            + "\n\n".join(source_sections)
        )

    def build_prompt(
        self,
        question: str,
        history: list[dict],
        evidence_text: str,
    ) -> str:
        history_text = "\n".join(
            f"{item['role'].upper()}: {item['content']}"
            for item in history[-self.MAX_HISTORY_MESSAGES:]
        )

        return f"""
You are the Research Agent in a financial research system.

Answer ONLY using supplied evidence.
Never use external knowledge.
Never invent financial data, trends, conclusions, or citations.

If evidence does not answer a topic, say:
"Not found in the selected documents."

The user may ask a multi-part question. Address every answerable part.

Every factual statement must have one or more citations:
[S1], [S2], and so on.

Use only source IDs in the supplied evidence.

Return valid JSON only:

{{
  "answer": "Direct, clear analyst-style answer with citations.",
  "used_source_ids": ["S1", "S2"]
}}

Conversation history:
{history_text or "No previous messages."}

Current question:
{question}

Evidence:
{evidence_text}
""".strip()

    def build_source_grounded_response(
        self,
        question: str,
        sources: list[dict],
    ) -> dict:
        """
        Produces a direct answer when no LLM is available.

        It selects exact relevant annual-report sentences for every
        topic requested by the user.
        """

        requested_topics = self.find_requested_topics(question)

        answer_lines = [
            "Based on the retrieved annual-report evidence:"
        ]

        used_sources = []
        matched_topics = 0

        for topic in requested_topics:
            match = self.find_best_evidence_sentence(
                sources=sources,
                keywords=topic["keywords"],
            )

            if not match:
                answer_lines.append(
                    f"- {topic['title']}: Not found in the retrieved "
                    "source passages."
                )
                continue

            matched_topics += 1
            source = match["source"]

            if source["source_id"] not in {
                item["source_id"] for item in used_sources
            }:
                used_sources.append(source)

            answer_lines.append(
                f"- {topic['title']}: The report states, "
                f"“{match['sentence']}” [{source['source_id']}]"
            )

        if matched_topics == 0:
            used_sources = sources[:3]

            source_ids = " ".join(
                f"[{source['source_id']}]"
                for source in used_sources
            )

            answer_lines = [
                "Relevant evidence was retrieved from the selected annual "
                "reports, but no retrieved sentence directly matched every "
                f"topic in the question. {source_ids}"
            ]

        return {
            "answer": "\n".join(answer_lines),
            "citations": used_sources,
        }

    def find_requested_topics(
        self,
        question: str,
    ) -> list[dict]:
        question_lower = question.lower()
        topics = []

        for rule in self.TOPIC_RULES:
            if any(
                keyword in question_lower
                for keyword in rule["keywords"]
            ):
                topics.append(rule)

        if topics:
            return topics

        return [
            {
                "title": "Relevant Report Evidence",
                "keywords": [
                    word.strip("?,.!:;()[]").lower()
                    for word in question.split()
                    if len(word) > 3
                ],
            }
        ]

    def find_best_evidence_sentence(
        self,
        sources: list[dict],
        keywords: list[str],
    ) -> dict | None:
        best_match = None
        best_score = 0

        for source in sources:
            sentences = self.split_into_sentences(source["excerpt"])

            for sentence in sentences:
                sentence_lower = sentence.lower()

                score = sum(
                    2 if " " in keyword and keyword in sentence_lower else 1
                    for keyword in keywords
                    if keyword in sentence_lower
                )

                if score > best_score:
                    best_score = score
                    best_match = {
                        "source": source,
                        "sentence": sentence[:650],
                    }

        return best_match if best_score > 0 else None

    @staticmethod
    def split_into_sentences(text: str) -> list[str]:
        cleaned_text = " ".join(text.split())

        sentences = re.split(
            r"(?<=[.!?])\s+",
            cleaned_text,
        )

        return [
            sentence.strip()
            for sentence in sentences
            if len(sentence.strip()) >= 25
        ]

    def parse_model_response(
        self,
        question: str,
        model_text: str,
        sources: list[dict],
    ) -> dict:
        """
        Rejects invalid or missing citations from OpenAI or Ollama.
        """

        parsed = self.load_json_response(model_text)

        source_by_id = {
            source["source_id"]: source
            for source in sources
        }

        answer = str(parsed.get("answer", "")).strip()

        declared_source_ids = [
            source_id
            for source_id in parsed.get("used_source_ids", [])
            if source_id in source_by_id
        ]

        citation_ids_in_answer = re.findall(r"\[(S\d+)\]", answer)

        has_invalid_citation = any(
            source_id not in source_by_id
            for source_id in citation_ids_in_answer
        )

        valid_citation_ids = []

        for source_id in citation_ids_in_answer:
            if (
                source_id in source_by_id
                and source_id not in valid_citation_ids
            ):
                valid_citation_ids.append(source_id)

        citation_safe = (
            bool(answer)
            and bool(valid_citation_ids)
            and not has_invalid_citation
            and set(valid_citation_ids).issubset(
                set(declared_source_ids)
            )
        )

        if not citation_safe:
            return self.build_source_grounded_response(
                question=question,
                sources=sources,
            )

        return {
            "answer": answer,
            "citations": [
                source_by_id[source_id]
                for source_id in valid_citation_ids
            ],
        }

    @staticmethod
    def load_json_response(model_text: str) -> dict:
        cleaned = model_text.strip()

        if cleaned.startswith("```"):
            cleaned = re.sub(
                r"^```(?:json)?\s*|\s*```$",
                "",
                cleaned,
                flags=re.IGNORECASE,
            ).strip()

        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError:
            return {
                "answer": "",
                "used_source_ids": [],
            }

        if not isinstance(parsed, dict):
            return {
                "answer": "",
                "used_source_ids": [],
            }

        return parsed