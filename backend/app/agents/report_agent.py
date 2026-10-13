from app.models import Document, FinancialMetric, RedFlag


class ReportAgent:
    """
    Generates the first two report sections:
    Executive Summary and Key Financials.
    """

    def generate(
        self,
        document: Document,
        metrics: list[FinancialMetric],
        red_flags: list[RedFlag],
    ) -> dict:
        company_name = (
            document.company_name
            or document.original_filename
        )

        important_names = {
            "Revenue",
            "Gross Profit",
            "Operating Income",
            "Net Income",
            "Total Assets",
            "Total Liabilities",
            "Long Term Debt",
            "Operating Cash Flow",
            "Free Cash Flow",
        }

        key_financials = [
            metric
            for metric in metrics
            if metric.metric_name in important_names
        ]

        high_severity_count = sum(
            1
            for flag in red_flags
            if flag.severity.lower() == "high"
        )

        executive_summary = (
            f"{company_name} ({document.fiscal_year or 'annual report period'}) "
            f"was processed through the Document, Extraction, and Red Flag "
            f"Agents. The system extracted {len(metrics)} financial metrics "
            f"and identified {len(red_flags)} source-cited risk signals"
            f"{', including ' + str(high_severity_count) + ' high-severity signals' if high_severity_count else ''}."
        )

        return {
            "company_name": company_name,
            "fiscal_year": document.fiscal_year,
            "executive_summary": executive_summary,
            "key_financials": [
                {
                    "metric_name": metric.metric_name,
                    "metric_value": metric.metric_value,
                    "period": metric.period,
                    "source_page": metric.source_page,
                }
                for metric in key_financials
            ],
            "red_flags": [
                {
                    "category": flag.category,
                    "severity": flag.severity,
                    "title": flag.title,
                    "source_page": flag.source_page,
                }
                for flag in red_flags
            ],
        }