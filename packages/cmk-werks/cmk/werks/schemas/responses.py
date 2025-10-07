from datetime import datetime, UTC

from pydantic import BaseModel, Field

from .evaluations import AggregatedEvaluations


class EvaluationResponse(BaseModel):
    """
    Response schema for evaluation endpoints.
    """

    user_id: str = Field(
        description="Unique identifier for the user making the request.",
        examples=["user123", "user456"],
    )
    request_id: str = Field(
        description="Unique identifier for the request.",
        examples=["req789", "req101112"],
    )
    response_datetime: datetime = Field(
        default=datetime.now(UTC),
        description="Timestamp of the response.",
        examples=["2023-10-01T12:00:00Z", "2023-10-02T15:30:00Z"],
    )
    evaluation: AggregatedEvaluations = Field(
        description="The evaluation results for the WERK.",
    )


class RewritingResponse(BaseModel):
    """
    Response schema for rewriting endpoints.
    """

    user_id: str = Field(
        description="Unique identifier for the user making the request.",
        examples=["user123", "user456"],
    )
    request_id: str = Field(
        description="Unique identifier for the request.",
        examples=["req789", "req101112"],
    )
    response_datetime: datetime = Field(
        default=datetime.now(UTC),
        description="Timestamp of the response.",
        examples=["2023-10-01T12:00:00Z", "2023-10-02T15:30:00Z"],
    )
    rewritten_text: str = Field(
        description="The rewritten text of the WERK.",
        examples=[
            "Due to changes in the quickstats API response, the engaged alerts field is not always present. "
            "Because of this, our code would crash. We now check first if it's there and provide an alternative value when not."
        ],
    )


class UserUnderstandingResponse(BaseModel):
    """
    Response schema for user understanding endpoints.
    """

    user_id: str = Field(
        description="Unique identifier for the user making the request.",
        examples=["user123", "user456"],
    )
    request_id: str = Field(
        description="Unique identifier for the request.",
        examples=["req789", "req101112"],
    )
    response_datetime: datetime = Field(
        default=datetime.now(UTC),
        description="Timestamp of the response.",
        examples=["2023-10-01T12:00:00Z", "2023-10-02T15:30:00Z"],
    )
    user_understanding: str = Field(
        description="A summary of the user's understanding of the WERK.",
        examples=[
            "My understanding of the werk is that it addresses a compatibility issue with the quickstats API."
        ],
    )


class HealthCheckResponse(BaseModel):
    """
    Response schema for health check endpoints.
    """

    status: str = Field(
        default="healthy",
        description="Health status of the service.",
        examples=["healthy", "unhealthy"],
    )

    response_datetime: datetime = Field(
        default=datetime.now(UTC),
        description="Timestamp of the health check response.",
        examples=["2023-10-01T12:00:00Z", "2023-10-02T15:30:00Z"],
    )
