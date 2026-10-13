from app.agents.research_agent import ResearchAgent


def create_agent_without_openai():
    """
    Test helper methods without an API key, ChromaDB, or OpenAI call.
    """
    return ResearchAgent.__new__(ResearchAgent)


def source(source_id, page, excerpt=None):
    return {
        "source_id": source_id,
        "document_id": 1,
        "document_name": "Example Corp",
        "page": page,
        "excerpt": excerpt
        or f"Annual report evidence from page {page}.",
    }


def test_multi_part_question_creates_multiple_retrieval_queries():
    agent = create_agent_without_openai()

    queries = agent.build_retrieval_queries(
        "Compare revenue, debt, and liquidity risk."
    )

    assert "Compare revenue, debt, and liquidity risk." in queries
    assert "revenue" in queries
    assert "debt" in queries
    assert "liquidity" in queries


def test_valid_answer_returns_only_retrieved_citations():
    agent = create_agent_without_openai()

    sources = [
        source("S1", 12),
        source("S2", 24),
    ]

    response = agent.parse_model_response(
        question="What happened to revenue?",
        model_text="""
        {
          "answer": "Revenue increased according to the report [S1].",
          "used_source_ids": ["S1"]
        }
        """,
        sources=sources,
    )

    assert response["answer"].endswith("[S1].")
    assert len(response["citations"]) == 1
    assert response["citations"][0]["source_id"] == "S1"
    assert response["citations"][0]["page"] == 12


def test_invalid_citation_uses_source_grounded_fallback():
    agent = create_agent_without_openai()

    sources = [
        source(
            "S1",
            12,
            (
                "The company had $5 billion of outstanding "
                "indebtedness during the year."
            ),
        ),
        source(
            "S2",
            24,
            (
                "Cash and cash equivalents were available to support "
                "liquidity needs."
            ),
        ),
    ]

    response = agent.parse_model_response(
        question="What does the report say about debt and liquidity?",
        model_text="""
        {
          "answer": "Debt increased materially [S99].",
          "used_source_ids": ["S99"]
        }
        """,
        sources=sources,
    )

    assert "Based on the retrieved annual-report evidence" in response["answer"]
    assert "[S99]" not in response["answer"]
    assert "[S1]" in response["answer"]

    returned_source_ids = {
        citation["source_id"]
        for citation in response["citations"]
    }

    assert returned_source_ids.issubset({"S1", "S2"})


def test_answer_without_citation_uses_source_grounded_fallback():
    agent = create_agent_without_openai()

    sources = [
        source(
            "S1",
            12,
            (
                "The company reported $10 billion in total revenue "
                "for the fiscal year."
            ),
        )
    ]

    response = agent.parse_model_response(
        question="What was revenue?",
        model_text="""
        {
          "answer": "The company reported higher revenue.",
          "used_source_ids": ["S1"]
        }
        """,
        sources=sources,
    )

    assert "Based on the retrieved annual-report evidence" in response["answer"]
    assert "[S1]" in response["answer"]
    assert response["citations"][0]["source_id"] == "S1"


def test_source_grounded_fallback_answers_debt_question():
    agent = create_agent_without_openai()

    sources = [
        source(
            "S1",
            40,
            (
                "The company had $7.91 billion in aggregate principal "
                "amount of indebtedness."
            ),
        ),
        source(
            "S2",
            41,
            (
                "Cash and cash equivalents support the company's "
                "liquidity requirements."
            ),
        ),
    ]

    response = agent.build_source_grounded_response(
        question="What does the report say about debt and liquidity?",
        sources=sources,
    )

    assert "Debt" in response["answer"]
    assert "$7.91 billion" in response["answer"]
    assert "[S1]" in response["answer"]
    assert "[S2]" in response["answer"]

    returned_source_ids = {
        citation["source_id"]
        for citation in response["citations"]
    }

    assert returned_source_ids == {"S1", "S2"}