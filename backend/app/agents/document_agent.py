import re

import pymupdf as fitz


class DocumentAgent:
    """
    Validates, reads, chunks, and prepares uploaded annual-report PDFs
    for vector indexing.
    """

    REPORT_IDENTIFIERS = [
        ("Annual Report", r"\bannual\s+report\b"),
        ("Form 10-K", r"\bform\s+10-k\b"),
        ("Form 20-F", r"\bform\s+20-f\b"),
        ("Annual Financial Report", r"\bannual\s+financial\s+report\b"),
        ("Integrated Report", r"\bintegrated\s+report\b"),
    ]

    FINANCIAL_INDICATORS = [
        r"\bconsolidated\s+financial\s+statements\b",
        r"\bbalance\s+sheets?\b",
        r"\bincome\s+statements?\b",
        r"\bstatements?\s+of\s+operations\b",
        r"\bcash\s+flows?\b",
        r"\bmanagement.?s\s+discussion\b",
        r"\bnotes\s+to\s+(the\s+)?financial\s+statements\b",
        r"\bshareholders?\b",
        r"\bstockholders?\b",
        r"\brevenue\b",
        r"\bnet\s+income\b",
        r"\btotal\s+assets\b",
        r"\btotal\s+liabilities\b",
        r"\baudited\b",
    ]

    NON_REPORT_IDENTIFIERS = [
        r"\bform\s+10-q\b",
        r"\bquarterly\s+report\b",
        r"\bearnings\s+presentation\b",
        r"\binvestor\s+presentation\b",
        r"\bpitch\s+deck\b",
        r"\bproduct\s+brochure\b",
        r"\bmeeting\s+minutes\b",
        r"\bresume\b",
        r"\bcurriculum\s+vitae\b",
    ]

    def validate_annual_report(
        self,
        content: bytes,
    ) -> dict:
        """
        Validate that an uploaded PDF is likely an annual report.

        This is a content-based safety gate, not only a filename check.
        It reads the first 15 pages because annual-report identity and
        financial-statement references normally appear near the beginning.
        """
        if not content or not content.startswith(b"%PDF"):
            return {
                "is_valid": False,
                "message": (
                    "The uploaded file is not a valid PDF. "
                    "Please upload a text-based company annual report PDF."
                ),
            }

        pdf = None

        try:
            pdf = fitz.open(stream=content, filetype="pdf")

            if pdf.page_count == 0:
                return {
                    "is_valid": False,
                    "message": "The PDF has no readable pages.",
                }

            sample_text = []

            for page_index in range(min(pdf.page_count, 15)):
                page_text = pdf[page_index].get_text("text").strip()

                if page_text:
                    sample_text.append(page_text)

            text = " ".join(sample_text)
            normalized = re.sub(r"\s+", " ", text).lower()

            if len(normalized) < 500:
                return {
                    "is_valid": False,
                    "message": (
                        "This PDF does not contain enough readable text. "
                        "Upload a text-based annual report, 10-K, or 20-F PDF."
                    ),
                }

            rejected_matches = [
                pattern
                for pattern in self.NON_REPORT_IDENTIFIERS
                if re.search(pattern, normalized, re.IGNORECASE)
            ]

            report_matches = [
                label
                for label, pattern in self.REPORT_IDENTIFIERS
                if re.search(pattern, normalized, re.IGNORECASE)
            ]

            financial_match_count = sum(
                bool(re.search(pattern, normalized, re.IGNORECASE))
                for pattern in self.FINANCIAL_INDICATORS
            )

            if rejected_matches and not report_matches:
                return {
                    "is_valid": False,
                    "message": (
                        "This PDF appears to be a quarterly report, presentation, "
                        "or unrelated document. Upload a company annual report, "
                        "Form 10-K, Form 20-F, or annual financial report."
                    ),
                }

            if not report_matches or financial_match_count < 4:
                return {
                    "is_valid": False,
                    "message": (
                        "This PDF could not be verified as a company annual report. "
                        "It must contain an annual-report identifier and financial "
                        "statement content such as balance sheet, income statement, "
                        "cash flows, revenue, or audited financial statements."
                    ),
                }

            return {
                "is_valid": True,
                "message": (
                    f"Verified as {report_matches[0]} with "
                    f"{financial_match_count} financial-report indicators."
                ),
                "page_count": pdf.page_count,
                "report_type": report_matches[0],
            }

        except Exception:
            return {
                "is_valid": False,
                "message": (
                    "The PDF could not be read. Upload a valid, non-password-"
                    "protected, text-based company annual report."
                ),
            }

        finally:
            if pdf is not None:
                pdf.close()

    def parse_pdf(self, file_path: str) -> list[dict]:
        pdf = fitz.open(file_path)
        pages = []

        try:
            for page_number, page in enumerate(pdf, start=1):
                text = page.get_text("text").strip()

                if text:
                    pages.append(
                        {
                            "page": page_number,
                            "text": text,
                        }
                    )
        finally:
            pdf.close()

        return pages

    def chunk_pages(
        self,
        pages: list[dict],
        document_id: int,
        session_id: int,
        company_name: str | None,
        fiscal_year: str | None,
        chunk_size_words: int = 300,
        overlap_words: int = 50,
    ) -> list[dict]:
        chunks = []

        for page_data in pages:
            words = page_data["text"].split()
            page_number = page_data["page"]
            start = 0
            part_number = 1

            while start < len(words):
                end = start + chunk_size_words
                text = " ".join(words[start:end]).strip()

                if text:
                    chunks.append(
                        {
                            "chunk_id": (
                                f"document_{document_id}_"
                                f"page_{page_number}_part_{part_number}"
                            ),
                            "document_id": document_id,
                            "session_id": session_id,
                            "company_name": company_name or "Unknown",
                            "fiscal_year": fiscal_year or "Unknown",
                            "page": page_number,
                            "text": text,
                        }
                    )

                start += chunk_size_words - overlap_words
                part_number += 1

        return chunks