from app.models import Document, FinancialMetric


class ComparisonAgent:
    """
    Produces a transparent side-by-side comparison using only
    metrics already extracted from uploaded reports.
    """

    def compare(
        self,
        documents: list[Document],
        metrics: list[FinancialMetric],
    ) -> dict:
        metric_names = sorted(
            {metric.metric_name for metric in metrics}
        )

        rows = []

        for metric_name in metric_names:
            values = []

            for document in documents:
                metric = next(
                    (
                        item
                        for item in metrics
                        if item.document_id == document.id
                        and item.metric_name == metric_name
                    ),
                    None,
                )

                values.append(
                    {
                        "document_id": document.id,
                        "company_name": (
                            document.company_name
                            or document.original_filename
                        ),
                        "value": (
                            metric.metric_value
                            if metric
                            else "Not found"
                        ),
                        "source_page": (
                            metric.source_page
                            if metric
                            else None
                        ),
                    }
                )

            rows.append(
                {
                    "metric_name": metric_name,
                    "values": values,
                }
            )

        return {
            "documents": [
                {
                    "id": document.id,
                    "company_name": (
                        document.company_name
                        or document.original_filename
                    ),
                    "fiscal_year": document.fiscal_year,
                }
                for document in documents
            ],
            "rows": rows,
        }