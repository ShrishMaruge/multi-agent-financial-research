from types import SimpleNamespace

from app.agents.report_agent import ReportAgent


def test_report_agent_includes_metrics_and_flags():
    document = SimpleNamespace(
        company_name="Example Corp",
        fiscal_year="2024",
        original_filename="example.pdf",
    )

    metric = SimpleNamespace(
        metric_name="Revenue",
        metric_value="$10,000",
        period="FY 2024",
        source_page=32,
    )

    flag = SimpleNamespace(
        category="Debt and Liquidity",
        severity="medium",
        title="Debt or liquidity risk disclosed",
        source_page=55,
    )

    report = ReportAgent().generate(
        document=document,
        metrics=[metric],
        red_flags=[flag],
    )

    assert report["company_name"] == "Example Corp"
    assert report["key_financials"][0]["metric_name"] == "Revenue"
    assert report["red_flags"][0]["severity"] == "medium"