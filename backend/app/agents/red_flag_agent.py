import re


class RedFlagAgent:
    """
    Finds directly disclosed risk signals in annual reports.

    The confidence score is a transparent rule-based evidence score:
    - direct phrase strength,
    - risk context in the same source sentence,
    - corroboration on multiple report pages.

    It is not an audit opinion or a statistically measured accuracy score.
    """

    RULES = [
        {
            "category": "Auditor and Controls",
            "severity": "high",
            "title": "Auditor, going-concern, or internal-control warning",
            "signals": [
                {
                    "label": "Qualified audit opinion",
                    "pattern": r"\bqualified\s+opinion\b",
                    "base_confidence": 0.90,
                },
                {
                    "label": "Adverse audit opinion",
                    "pattern": r"\badverse\s+opinion\b",
                    "base_confidence": 0.94,
                },
                {
                    "label": "Going concern disclosure",
                    "pattern": r"\bgoing\s+concern\b",
                    "base_confidence": 0.90,
                },
                {
                    "label": "Material weakness",
                    "pattern": r"\bmaterial\s+weakness\b",
                    "base_confidence": 0.88,
                },
                {
                    "label": "Ineffective internal control",
                    "pattern": r"\bineffective\s+internal\s+control\b",
                    "base_confidence": 0.86,
                },
            ],
        },
        {
            "category": "Debt and Liquidity",
            "severity": "medium",
            "title": "Debt or liquidity risk disclosed",
            "signals": [
                {
                    "label": "Substantial indebtedness",
                    "pattern": r"\bsubstantial\s+indebtedness\b",
                    "base_confidence": 0.84,
                },
                {
                    "label": "Debt covenant risk",
                    "pattern": r"\bdebt\s+covenant\b",
                    "base_confidence": 0.78,
                },
                {
                    "label": "Liquidity risk",
                    "pattern": r"\bliquidity\s+risk\b",
                    "base_confidence": 0.80,
                },
                {
                    "label": "Potential default",
                    "pattern": r"\bdefault\s+under\b",
                    "base_confidence": 0.84,
                },
                {
                    "label": "Covenant breach",
                    "pattern": r"\bbreach\s+of.{0,50}\bcovenant\b",
                    "base_confidence": 0.86,
                },
                {
                    "label": "Liquidity uncertainty",
                    "pattern": r"\bliquidity.{0,50}\buncertain\b",
                    "base_confidence": 0.82,
                },
            ],
        },
        {
            "category": "Margins",
            "severity": "medium",
            "title": "Margin pressure disclosed",
            "signals": [
                {
                    "label": "Gross-margin decline",
                    "pattern": r"\bgross\s+margin.{0,40}\bdeclin",
                    "base_confidence": 0.82,
                },
                {
                    "label": "Operating-margin decline",
                    "pattern": r"\boperating\s+margin.{0,40}\bdeclin",
                    "base_confidence": 0.82,
                },
                {
                    "label": "Margin decrease",
                    "pattern": r"\bmargin.{0,40}\bdecreas",
                    "base_confidence": 0.76,
                },
                {
                    "label": "Lower margin",
                    "pattern": r"\blower\s+margin\b",
                    "base_confidence": 0.72,
                },
                {
                    "label": "Margin pressure",
                    "pattern": r"\bmargin\s+pressure\b",
                    "base_confidence": 0.74,
                },
            ],
        },
        {
            "category": "Revenue",
            "severity": "medium",
            "title": "Revenue decline disclosed",
            "signals": [
                {
                    "label": "Revenue decline",
                    "pattern": r"\brevenue.{0,40}\bdeclin",
                    "base_confidence": 0.82,
                },
                {
                    "label": "Net-sales decline",
                    "pattern": r"\bnet\s+sales.{0,40}\bdeclin",
                    "base_confidence": 0.82,
                },
                {
                    "label": "Sales decrease",
                    "pattern": r"\bsales.{0,40}\bdecreas",
                    "base_confidence": 0.76,
                },
                {
                    "label": "Decrease in revenue",
                    "pattern": r"\bdecrease\s+in\s+revenue\b",
                    "base_confidence": 0.82,
                },
            ],
        },
        {
            "category": "Legal and Regulatory",
            "severity": "medium",
            "title": "Potential material legal or regulatory exposure",
            "signals": [
                {
                    "label": "Material legal proceeding",
                    "pattern": r"\bmaterial\s+legal\s+proceeding\b",
                    "base_confidence": 0.82,
                },
                {
                    "label": "Class action",
                    "pattern": r"\bclass\s+action\b",
                    "base_confidence": 0.74,
                },
                {
                    "label": "Regulatory investigation",
                    "pattern": r"\bregulatory\s+investigation\b",
                    "base_confidence": 0.80,
                },
                {
                    "label": "Material litigation",
                    "pattern": r"\bmaterial\s+litigation\b",
                    "base_confidence": 0.84,
                },
            ],
        },
    ]

    RISK_CONTEXT_PATTERN = re.compile(
        r"\b(material|significant|may|could|adversely|uncertain|"
        r"risk|default|breach|unable|loss)\b",
        re.IGNORECASE,
    )

    @staticmethod
    def _sentences(page_text: str) -> list[str]:
        text = re.sub(r"\s+", " ", page_text).strip()

        if not text:
            return []

        return [
            sentence.strip()
            for sentence in re.split(r"(?<=[.!?])\s+", text)
            if len(sentence.strip()) >= 20
        ]

    @staticmethod
    def _evidence_window(
        sentences: list[str],
        sentence_index: int,
    ) -> str:
        start = max(0, sentence_index - 1)
        end = min(len(sentences), sentence_index + 2)
        return " ".join(sentences[start:end])[:1400]

    @staticmethod
    def _severity_from_confidence(
        configured_severity: str,
        confidence: float,
    ) -> str:
        if configured_severity == "high" or confidence >= 0.88:
            return "high"

        if confidence >= 0.70:
            return "medium"

        return "low"

    def run(
        self,
        pages: list[dict],
        extracted_metrics: list[dict],
    ) -> list[dict]:
        del extracted_metrics

        candidates = []
        seen = set()

        for page in pages:
            page_number = page["page"]
            sentences = self._sentences(page["text"])

            for sentence_index, sentence in enumerate(sentences):
                for rule in self.RULES:
                    matched_signals = []

                    for signal in rule["signals"]:
                        if re.search(
                            signal["pattern"],
                            sentence,
                            re.IGNORECASE,
                        ):
                            matched_signals.append(signal)

                    if not matched_signals:
                        continue

                    signal_labels = sorted(
                        {signal["label"] for signal in matched_signals}
                    )

                    unique_key = (
                        rule["category"],
                        page_number,
                        sentence.lower(),
                    )

                    if unique_key in seen:
                        continue

                    seen.add(unique_key)

                    candidates.append(
                        {
                            "category": rule["category"],
                            "configured_severity": rule["severity"],
                            "title": rule["title"],
                            "source_page": page_number,
                            "evidence": self._evidence_window(
                                sentences,
                                sentence_index,
                            ),
                            "signal_labels": signal_labels,
                            "base_confidence": max(
                                signal["base_confidence"]
                                for signal in matched_signals
                            ),
                            "has_risk_context": bool(
                                self.RISK_CONTEXT_PATTERN.search(sentence)
                            ),
                        }
                    )

        page_counts_by_category = {}

        for candidate in candidates:
            category = candidate["category"]
            page_counts_by_category.setdefault(category, set()).add(
                candidate["source_page"]
            )

        findings = []

        for candidate in candidates:
            corroborating_pages = len(
                page_counts_by_category[candidate["category"]]
            )

            context_bonus = (
                0.06 if candidate["has_risk_context"] else 0.0
            )

            corroboration_bonus = min(
                max(corroborating_pages - 1, 0) * 0.03,
                0.09,
            )

            confidence = min(
                candidate["base_confidence"]
                + context_bonus
                + corroboration_bonus,
                0.98,
            )

            score_parts = [
                (
                    f"{round(candidate['base_confidence'] * 100)}% "
                    "from the direct matched disclosure phrase"
                )
            ]

            if candidate["has_risk_context"]:
                score_parts.append(
                    "+6% because the same sentence contains risk context"
                )

            if corroboration_bonus > 0:
                score_parts.append(
                    (
                        f"+{round(corroboration_bonus * 100)}% because "
                        f"this category appears on {corroborating_pages} "
                        "report pages"
                    )
                )

            confidence_explanation = (
                f"Rule-based evidence confidence: "
                f"{round(confidence * 100)}%. "
                + "; ".join(score_parts)
                + ". This score measures evidence relevance in the PDF; "
                "it is not an audit opinion or a prediction."
            )

            findings.append(
                {
                    "category": candidate["category"],
                    "severity": self._severity_from_confidence(
                        candidate["configured_severity"],
                        confidence,
                    ),
                    "title": candidate["title"],
                    "explanation": (
                        "The Red Flag Agent found a direct disclosure that "
                        "may require analyst review. Read the cited PDF "
                        "evidence before reaching a conclusion."
                    ),
                    "source_page": candidate["source_page"],
                    "evidence": candidate["evidence"],
                    "confidence": round(confidence, 2),
                    "confidence_explanation": confidence_explanation,
                    "matched_signals": ", ".join(
                        candidate["signal_labels"]
                    ),
                }
            )

        return sorted(
            findings,
            key=lambda finding: (
                finding["severity"] != "high",
                -finding["confidence"],
                finding["source_page"],
            ),
        )[:25]