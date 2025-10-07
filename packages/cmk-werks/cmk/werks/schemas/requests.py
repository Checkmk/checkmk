from datetime import datetime

from pydantic import BaseModel, Field

from .evaluations import AggregatedEvaluations


class Werk(BaseModel):
    title: str = Field(
        description="Title of the WERK.",
        examples=["Werk #18284: ntopng: engaged alerts not always present in api response"],
    )
    date: datetime = Field(
        description="Date of the WERK.",
        examples=["2024-10-10T12:00:00Z", "2024-10-11T15:30:00Z"],
    )
    level: int = Field(
        description="Level of the WERK, indicating its complexity or importance.",
        examples=[1, 2, 3],
    )
    version: str = Field(
        description="Version or edition of checkmk that is interested by this werk.",
        examples=["2.4.0"],
    )
    werk_class: str = Field(
        description="Class of the WERK, indicating its category or type.",
        examples=["Feature", "Bug fix"],
    )
    component: str = Field(
        description="Component affected by the WERK.",
        examples=["Ntopng integration"],
    )
    compatible: bool = Field(
        description="Indicates whether the WERK is compatible or needs some intervention from user.",
        examples=[True, False],
    )
    werk_text: str = Field(
        description="Text of the WERK, containing detailed information about the changes.",
        examples=[
            "Due to changes in the quickstats api response, the engaged alerts field is not always present. "
            "Because of this our code would crash. We now check first if it's "
            "there and provide an alternative value when not."
        ],
    )


class EvaluationRequest(BaseModel):
    werk: Werk = Field(
        description="The WERK object containing structured information about the WERK.",
    )


class RewriteRequest(BaseModel):
    werk: Werk = Field(
        description="The WERK object containing structured information about the WERK.",
    )

    evaluation: AggregatedEvaluations = Field(
        description="The evaluation results for the WERK, which will be used to guide the rewriting process.",
    )


class UserUnderstandingRequest(BaseModel):
    werk: Werk = Field(
        description="The WERK object containing structured information about the WERK.",
    )
