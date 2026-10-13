# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re

import pytest
from update_confluence_vscode_page import (
    _escape,
    _inline,
    _md_to_confluence,
    _status_macro,
    _table_to_xhtml,
    README_PATH,
    STATUS_COLORS,
)

SEPARATOR_RE = re.compile(r"^\|[\s\-:|]+\|$")


class TestEscape:
    def test_escapes_all_three_entities(self) -> None:
        assert _escape("a & b < c > d") == "a &amp; b &lt; c &gt; d"

    def test_ampersand_is_escaped_before_the_angles(self) -> None:
        assert _escape("<") == "&lt;"

    def test_is_not_idempotent(self) -> None:
        assert _escape(_escape("&")) == "&amp;amp;"


class TestInline:
    def test_code_span(self) -> None:
        assert _inline("run `bazel test` now") == "run <code>bazel test</code> now"

    def test_angles_inside_a_code_span_are_escaped(self) -> None:
        assert _inline("`a<b>`") == "<code>a&lt;b&gt;</code>"

    def test_bare_angles_are_escaped(self) -> None:
        assert _inline("a < b > c") == "a &lt; b &gt; c"

    def test_bold(self) -> None:
        assert _inline("**yes** no") == "<strong>yes</strong> no"

    def test_strikethrough(self) -> None:
        assert _inline("~~gone~~") == "<s>gone</s>"

    def test_link(self) -> None:
        assert _inline("[docs](https://example.com)") == '<a href="https://example.com">docs</a>'

    def test_ampersand_in_a_link_target_is_escaped(self) -> None:
        assert _inline("[x](http://h/p?a=1&b=2)") == '<a href="http://h/p?a=1&amp;b=2">x</a>'

    def test_strikethrough_wrapping_a_code_span(self) -> None:
        assert _inline("~~ESLint `bazel-*` scan~~") == "<s>ESLint <code>bazel-*</code> scan</s>"

    def test_bold_wrapping_a_code_span(self) -> None:
        assert (
            _inline("**mypy `follow_imports` override**")
            == "<strong>mypy <code>follow_imports</code> override</strong>"
        )

    @pytest.mark.xfail(
        strict=True,
        reason="_inline runs the bold/strike/link substitutions after building code spans, "
        "so markdown inside inline code is rewritten instead of kept literal",
    )
    def test_markdown_inside_a_code_span_stays_literal(self) -> None:
        assert _inline("`**not bold**`") == "<code>**not bold**</code>"


class TestStatusMacro:
    @pytest.mark.parametrize(
        "value, colour",
        [
            pytest.param("Match", "Green", id="match"),
            pytest.param("Version risk", "Yellow", id="version-risk"),
            pytest.param("Partial", "Yellow", id="partial"),
            pytest.param("Broken", "Red", id="broken"),
            pytest.param("Not configured", "Grey", id="not-configured"),
            pytest.param("Not evaluated", "Grey", id="not-evaluated"),
            pytest.param("Known limitation", "Yellow", id="known-limitation"),
        ],
    )
    def test_known_value_renders_a_status_macro(self, value: str, colour: str) -> None:
        rendered = _status_macro(value)
        assert '<ac:structured-macro ac:name="status">' in rendered
        assert f'<ac:parameter ac:name="title">{value}</ac:parameter>' in rendered
        assert f'<ac:parameter ac:name="colour">{colour}</ac:parameter>' in rendered

    def test_every_known_status_value_is_covered_above(self) -> None:
        assert set(STATUS_COLORS) == {
            "Match",
            "Version risk",
            "Partial",
            "Broken",
            "Not configured",
            "Not evaluated",
            "Known limitation",
        }

    def test_surrounding_whitespace_is_stripped(self) -> None:
        assert '<ac:parameter ac:name="title">Match</ac:parameter>' in _status_macro("  Match  ")

    def test_unknown_value_falls_back_to_inline(self) -> None:
        assert _status_macro("Mostly `fine`") == "Mostly <code>fine</code>"


class TestTableToXhtml:
    def test_header_cells_become_th(self) -> None:
        assert "<tr><th>A</th><th>B</th></tr>" in _table_to_xhtml("| A | B |", "|---|---|", [])

    def test_body_cells_become_td(self) -> None:
        rendered = _table_to_xhtml("| A | B |", "|---|---|", ["| x | y |"])
        assert "<tr><td>x</td><td>y</td></tr>" in rendered

    def test_parity_column_renders_a_status_macro(self) -> None:
        rendered = _table_to_xhtml("| Item | Parity |", "|---|---|", ["| a | Match |"])
        assert '<ac:parameter ac:name="colour">Green</ac:parameter>' in rendered
        assert "<td>a</td>" in rendered

    def test_parity_header_is_matched_case_insensitively(self) -> None:
        rendered = _table_to_xhtml("| Item | PARITY |", "|---|---|", ["| a | Broken |"])
        assert '<ac:parameter ac:name="colour">Red</ac:parameter>' in rendered

    def test_without_a_parity_column_every_cell_stays_plain(self) -> None:
        rendered = _table_to_xhtml("| Item | Note |", "|---|---|", ["| a | Match |"])
        assert "<td>Match</td>" in rendered
        assert "structured-macro" not in rendered

    def test_cell_content_goes_through_inline(self) -> None:
        rendered = _table_to_xhtml("| Item |", "|---|", ["| `x` and <y> |"])
        assert "<td><code>x</code> and &lt;y&gt;</td>" in rendered

    def test_table_is_wrapped_in_a_tbody(self) -> None:
        rendered = _table_to_xhtml("| A |", "|---|", [])
        assert rendered.startswith('<table class="wrapped">')
        assert rendered.endswith("</tbody></table>")


class TestMdToConfluence:
    @pytest.mark.parametrize("level", [1, 2, 3, 4, 5, 6], ids=lambda level: f"h{level}")
    def test_heading_levels(self, level: int) -> None:
        assert _md_to_confluence(f"{'#' * level} Title") == f"<h{level}>Title</h{level}>"

    def test_paragraph_fallback(self) -> None:
        assert _md_to_confluence("just text") == "<p>just text</p>"

    def test_blank_lines_are_dropped(self) -> None:
        assert _md_to_confluence("a\n\n\nb") == "<p>a</p>\n<p>b</p>"

    def test_ordered_list_items_are_grouped(self) -> None:
        assert _md_to_confluence("1. one\n2. two") == "<ol>\n<li>one</li>\n<li>two</li>\n</ol>"

    def test_unordered_list_accepts_dash_and_star(self) -> None:
        assert _md_to_confluence("- a\n* b") == "<ul>\n<li>a</li>\n<li>b</li>\n</ul>"

    def test_a_pipe_line_without_a_separator_is_not_a_table(self) -> None:
        assert "<table" not in _md_to_confluence("| a | b |\nnot a separator")

    def test_table_body_stops_at_the_first_non_pipe_line(self) -> None:
        rendered = _md_to_confluence("| A |\n|---|\n| x |\nafter")
        assert "<td>x</td>" in rendered
        assert "<p>after</p>" in rendered

    @pytest.mark.xfail(
        strict=True,
        reason="fenced code blocks are not implemented, so the ``` delimiters and the "
        "code body leak through as paragraphs",
    )
    def test_fenced_code_block_is_not_emitted_verbatim(self) -> None:
        assert "```" not in _md_to_confluence("```sh\nls -l\n```")


class TestCiParityDocument:
    def test_source_document_resolves(self) -> None:
        assert README_PATH.is_file()

    def test_no_markdown_table_row_leaks_into_a_paragraph(self) -> None:
        assert "<p>|" not in _md_to_confluence(README_PATH.read_text())

    def test_every_markdown_table_becomes_a_table_element(self) -> None:
        text = README_PATH.read_text()
        expected = sum(1 for line in text.splitlines() if SEPARATOR_RE.match(line.strip()))
        assert expected > 0
        assert _md_to_confluence(text).count("<table") == expected

    def test_parity_values_render_as_status_macros(self) -> None:
        assert '<ac:structured-macro ac:name="status">' in _md_to_confluence(
            README_PATH.read_text()
        )
