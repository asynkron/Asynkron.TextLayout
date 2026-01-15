from __future__ import annotations

from typing import Iterable

from .extraction_context import ExtractionContext
from .extraction_result import ExtractionResult


class ExtractorAggregator:
    @staticmethod
    def ExtractBest(
        texts: Iterable[str],
        context: ExtractionContext,
        extractors: Iterable["IExtractor"],
    ) -> str | None:
        votes: dict[str, int] = {}

        for text in texts:
            text_context = context.with_text(text)
            for extractor in extractors:
                for result in extractor.ExtractAll(text_context):
                    if not result.HasValue:
                        continue

                    current = votes.get(result.Value, 0)
                    votes[result.Value] = current + result.Votes

        if not votes:
            return None

        return max(votes.items(), key=lambda item: item[1])[0]

    @staticmethod
    def ExtractAll(
        texts: Iterable[str],
        context: ExtractionContext,
        extractors: Iterable["IExtractor"],
    ) -> list[tuple[str, int]]:
        votes: dict[str, int] = {}

        for text in texts:
            text_context = context.with_text(text)
            for extractor in extractors:
                for result in extractor.ExtractAll(text_context):
                    if not result.HasValue:
                        continue

                    current = votes.get(result.Value, 0)
                    votes[result.Value] = current + result.Votes

        return sorted(votes.items(), key=lambda item: item[1], reverse=True)


class IExtractor:
    Name: str

    def Extract(self, context: ExtractionContext) -> ExtractionResult:
        raise NotImplementedError

    def ExtractAll(self, context: ExtractionContext) -> list[ExtractionResult]:
        result = self.Extract(context)
        return [result] if result.HasValue else []
