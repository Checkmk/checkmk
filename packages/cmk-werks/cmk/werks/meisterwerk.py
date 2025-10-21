# i/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Checkmk development script to manage werks with the help of AI"""

import datetime
import sys
import uuid
from enum import Enum

import httpx
from rich.box import HORIZONTALS
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .in_out_elements import (
    getch,
    TTY_GREEN,
    TTY_NORMAL,
    TTY_RED,
    TTY_YELLOW,
)
from .schemas.requests import (
    EvaluationRequest,
    RewriteRequest,
    UserUnderstandingRequest,
)
from .schemas.requests import (
    Werk as WerkRequest,
)
from .schemas.responses import (
    EvaluationResponse,
    RewritingResponse,
    UserUnderstandingResponse,
)
from .schemas.werk import Werk as WerkTuple

URL = "http://meisterwerk.lan.checkmk.net/werks/"
VERSION = "1.0.0"  # TODO: Extract from package metadata


def color_from_score(score: int) -> Text:
    """Convert a numeric score into a colored Rich Text bar."""
    width = 7
    bar = Text("█" * width)
    if score == 1:
        bar.stylize("red on red")
    elif score == 2:
        bar.stylize("yellow on yellow")
    elif score == 3:
        bar.stylize("green on green")
    else:
        bar.stylize("grey50")
    return bar


console = Console()


class Choice(Enum):
    APPEND = "append"
    REPLACE = "replace"
    KEEP = "keep"


def generate_headers() -> dict[str, str]:
    return {
        "user-agent": f"werk-tool-v{VERSION}",
        "x-request-id": str(uuid.uuid4()),
    }


def evaluate_werk(werk_request: WerkRequest) -> EvaluationResponse:
    """Call the evaluation endpoint and return its JSON response."""
    client = httpx.Client(base_url=URL, timeout=60.0)

    request = EvaluationRequest(werk=werk_request)

    with console.status("[green]Evaluating WERK...", spinner="dots"):
        resp = client.post(
            "/evaluate/werk", json=request.model_dump(mode="json"), headers=generate_headers()
        )

    resp.raise_for_status()
    return EvaluationResponse.model_validate(resp.json())


def user_understanding_of_werk(werk_request: WerkRequest) -> UserUnderstandingResponse:
    """Call the user understanding endpoint and return its JSON response."""
    client = httpx.Client(base_url=URL, timeout=60.0)

    request = UserUnderstandingRequest(werk=werk_request)

    with console.status("[green]Generating User comprehension of WERK...", spinner="dots"):
        resp = client.post(
            "/generate/user_comprehension",
            json=request.model_dump(mode="json"),
            headers=generate_headers(),
        )

    resp.raise_for_status()
    return UserUnderstandingResponse.model_validate(resp.json())


def build_meisterwerk_payload(werk: WerkTuple) -> WerkRequest:
    return WerkRequest(
        title=str(werk.content.metadata["title"]),
        date=datetime.datetime.fromisoformat(str(werk.content.metadata["date"])),
        level=int(werk.content.metadata["level"]),
        version=str(werk.content.metadata["version"]),
        werk_class=str(werk.content.metadata["class"]),
        component=str(werk.content.metadata["component"]),
        compatible=werk.content.metadata["compatible"] == "yes",
        werk_text=str(werk.content.description),
    )


def rewrite_werk(
    werk_request: WerkRequest,
    evaluation_result: EvaluationResponse,
) -> RewritingResponse:
    """Call the rewrite endpoint and return its JSON response."""
    client = httpx.Client(base_url=URL, timeout=60.0)

    request = RewriteRequest(werk=werk_request, evaluation=evaluation_result.evaluation)

    with console.status("[green]Rewriting WERK...", spinner="dots"):
        resp = client.post(
            "/generate/rewrite",
            json=request.model_dump(mode="json"),
            headers=generate_headers(),
        )
    resp.raise_for_status()
    return RewritingResponse.model_validate(resp.json())


def display_evaluation(evaluation: EvaluationResponse) -> None:
    """Display evaluation scores and improvement suggestions in a formatted table."""
    scores = evaluation.evaluation.aggregated_scores
    suggestions = evaluation.evaluation.aggregated_suggestions

    # Create Rich table with better styling
    table = Table(show_header=True, header_style="bold cyan", title="WERK EVALUATION RESULTS")
    table.add_column("Aspect")
    table.add_column("Score", justify="center")
    table.add_column("Suggestion", overflow="fold")

    # Evaluation aspects
    aspects = [
        (
            "Grammar",
            scores.grammar_score,
            suggestions.grammar_suggestions_to_improve_text or "",
        ),
        (
            "Style",
            scores.english_style_score,
            suggestions.english_style_suggestions_to_improve_text or "",
        ),
        (
            "Clarity",
            scores.user_impact_clarity_score,
            suggestions.user_impact_clarity_suggestions_to_improve_text or "",
        ),
        (
            "Paragraphs",
            scores.paragraph_division_score,
            suggestions.paragraph_division_suggestions_to_improve_text or "",
        ),
    ]

    if scores.non_compatible_werk_score is not None:
        nc_suggestion = suggestions.non_compatible_werk_suggestions_to_improve_text or ""
        aspects.append(("Compatibility", scores.non_compatible_werk_score, nc_suggestion))

    for aspect, score, suggestion in aspects:
        score_display = color_from_score(score or 0)
        table.add_row(aspect, score_display, suggestion or "")

    console.print(table, justify="center")

    overall_assessment = _get_overall_assessment_rich(scores.average_score)
    console.print(f"\n[bold]Overall Assessment:[/bold] {overall_assessment}")


def display_user_understanding(understanding: UserUnderstandingResponse) -> None:
    """Display user understanding paragraph in a formatted panel."""
    # Display using Rich panel with Markdown
    console.print(
        Panel(
            Markdown(understanding.user_understanding), title="User Understanding", box=HORIZONTALS
        ),
        justify="center",
    )


def display_rewritten_werk(rewritten_werk: RewritingResponse) -> None:
    """Display the rewritten werk in a formatted panel with before/after comparison."""
    # Display using Rich panel with Markdown
    console.print(
        Panel(Markdown(rewritten_werk.rewritten_text), title="Rewritten Werk", box=HORIZONTALS),
        justify="center",
    )

    console.print("[bold]Status:[/bold] [green]Werk has been successfully rewritten[/green]")


def propose_rewriting() -> Choice:
    """Propose a rewriting for the werk based on its evaluation."""
    console.print(
        "[bold][red]The Evaluation of Meisterwerk suggests your werk could be improved."
        "We generated some suggested improvements and rewrote it for you.\n\n[/red][/bold]"
    )
    console.print("You can:")

    while True:
        console.print(
            "\n - [bold][green]a[/green][/bold]ppend the rewritten werk and open it to perform the needed edits."
            "\n - [bold][yellow]r[/yellow][/bold]eplace the original werk with the rewritten one."
            "\n - [bold][red]k[/red][/bold]eep the original werk as is and discard the rewritten one. [red](Not recommended)[/red]\n\n"
        )
        sys.stdout.flush()
        ch = getch().lower().strip()
        if ch == "a":
            console.print(
                "[bold][green]Appending the rewritten werk to your werk file...[/green][/bold]"
            )
            return Choice.APPEND
        elif ch == "r":
            console.print(
                "[bold][green]Replacing the original werk with the rewritten one...[/green][/bold]"
            )
            return Choice.REPLACE
        elif ch == "k":
            console.print("[bold][yellow]Keeping the original werk as is...[/yellow][/bold]")
            return Choice.KEEP
        else:
            console.print(
                "[bold][red]Invalid choice. Please choose 'a', 'r', or 'k'.\n[/red][/bold]"
            )


def _get_overall_assessment(avg_score: float) -> str:
    """Provide an overall assessment based on average score."""
    if avg_score >= 3:
        return f"{TTY_GREEN}Excellent - Ready for publication{TTY_NORMAL}"
    elif avg_score >= 2.5:
        return f"{TTY_YELLOW}Good - Minor improvements recommended{TTY_NORMAL}"
    elif avg_score >= 1.5:
        return f"{TTY_YELLOW}Fair - Several improvements needed{TTY_NORMAL}"
    else:
        return f"{TTY_RED}Poor - Significant revision required{TTY_NORMAL}"


def _get_overall_assessment_rich(avg_score: float) -> str:
    """Provide an overall assessment based on average score using Rich markup."""
    if avg_score >= 3:
        return f"[green]{avg_score:.1f} - Excellent - Ready for publication[/green]"
    elif avg_score >= 2.5:
        return f"[yellow]{avg_score:.1f} - Good - Minor improvements recommended[/yellow]"
    elif avg_score >= 1.5:
        return f"[yellow]{avg_score:.1f} - Fair - Several improvements needed[/yellow]"
    else:
        return f"[red]{avg_score:.1f} - Poor - Significant revision required[/red]"
