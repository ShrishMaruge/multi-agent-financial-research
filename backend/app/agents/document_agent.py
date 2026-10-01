import fitz


class DocumentAgent:
    """
    Document Agent:
    PDF -> page text -> chunks -> vector-database records.
    """

    def parse_pdf(self, file_path: str) -> list[dict]:
        pdf = fitz.open(file_path)
        pages = []

        for page_number, page in enumerate(pdf, start=1):
            text = page.get_text("text").strip()

            if text:
                pages.append(
                    {
                        "page": page_number,
                        "text": text,
                    }
                )

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
            page_number = page_data["page"]
            words = page_data["text"].split()

            start = 0
            part_number = 1

            while start < len(words):
                end = start + chunk_size_words
                chunk_text = " ".join(words[start:end])

                if chunk_text.strip():
                    chunks.append(
                        {
                            "chunk_id": f"document_{document_id}_page_{page_number}_part_{part_number}",
                            "document_id": document_id,
                            "session_id": session_id,
                            "company_name": company_name or "Unknown",
                            "fiscal_year": fiscal_year or "Unknown",
                            "page": page_number,
                            "text": chunk_text,
                        }
                    )

                start += chunk_size_words - overlap_words
                part_number += 1

        return chunks