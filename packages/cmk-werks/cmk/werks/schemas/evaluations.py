from pydantic import BaseModel, Field


class AggregatedSuggestions(
    BaseModel,
):
    """Aggregated evaluation of a WERK, combining all individual evaluations."""

    grammar_suggestions_to_improve_text: str = Field(
        description="Suggestions to improve the grammar of the WERK text, if any.",
        examples=["Correct the use of commas in the text."],
    )

    user_impact_clarity_suggestions_to_improve_text: str = Field(
        description="Suggestions to improve the clarity of user impact in the WERK text, if any.",
        examples=["Provide more details on how the changes affect users."],
    )

    paragraph_division_suggestions_to_improve_text: str = Field(
        description="Suggestions to improve the paragraph division of the WERK text, if any.",
        examples=["Break long paragraphs into shorter ones for better readability."],
    )

    non_compatible_werk_suggestions_to_improve_text: str | None = Field(
        default=None,
        description="Suggestions to improve the non-compatible werk evaluation of the WERK text, if applicable.",
        examples=["Provide migration instructions for users to adapt to the changes."],
    )

    english_style_suggestions_to_improve_text: str = Field(
        description="Suggestions to improve the English style of the WERK text, if any.",
        examples=["Use more concise language and avoid jargon."],
    )


class AggregatedScores(BaseModel):
    """Aggregated scores for all evaluations of a WERK text."""

    grammar_score: int = Field(
        description="Score for the grammar evaluation of the WERK text.",
        examples=[1, 2, 3],
    )
    user_impact_clarity_score: int = Field(
        description="Score for the user impact clarity evaluation of the WERK text.",
        examples=[1, 2, 3],
    )
    paragraph_division_score: int = Field(
        description="Score for the paragraph division evaluation of the WERK text.",
        examples=[1, 2, 3],
    )
    non_compatible_werk_score: int | None = Field(
        default=None,
        description="Score for the non-compatible werk evaluation of the WERK text, if applicable.",
        examples=[1, 2, 3],
    )
    english_style_score: int = Field(
        description="Score for the English style evaluation of the WERK text.",
        examples=[1, 2, 3],
    )

    @property
    def average_score(self) -> float:
        """Calculate the average score across all aspects."""
        scores = [
            self.grammar_score,
            self.user_impact_clarity_score,
            self.paragraph_division_score,
            self.english_style_score,
        ]
        if self.non_compatible_werk_score is not None:
            scores.append(self.non_compatible_werk_score)
        return sum(scores) / len(scores) if scores else 0.0


class AggregatedEvaluations(BaseModel):
    aggregated_scores: AggregatedScores = Field(
        description="Aggregated scores for all evaluations of a WERK text.",
    )
    aggregated_suggestions: AggregatedSuggestions = Field(
        description="Aggregated suggestions for improving the WERK text based on all evaluations.",
    )
