from app.agents.red_flag_agent import RedFlagAgent


def test_red_flag_agent_returns_source_grounded_finding():
    pages = [
        {
            "page": 12,
            "text": (
                "Management identified a material weakness in internal "
                "control over financial reporting."
            ),
        }
    ]

    findings = RedFlagAgent().run(
        pages=pages,
        extracted_metrics=[],
    )

    assert len(findings) == 1
    assert findings[0]["source_page"] == 12
    assert "material weakness" in findings[0]["evidence"].lower()
    assert findings[0]["severity"] == "high"