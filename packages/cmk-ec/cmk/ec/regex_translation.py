#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Our regexes as ones of grep and MongoDB, which understand only some of Python's regexes
alike and fold case unlike it, so the translations spell out case variants as alternatives,
and texts folded like Python's regexes fold case"""

import functools
import re
import string
import sys
from collections.abc import Mapping, Sequence

# Literal characters and dots, escaped or not
_LITERAL_REGEX = re.compile(r"(?:[^.^$*+?{}\[\]\\|()]|\\?\.)*")


def is_literal_regex(regex: str) -> bool:
    """Whether the regex has only literal characters and dots, escaped or not, like for host
    names or IP addresses"""
    return _LITERAL_REGEX.fullmatch(regex) is not None


def grep_regex(regex: str, *, ignore_case: bool) -> str:
    """An extended regex for grep which selects at least the lines with a match of the
    literal regex, see is_literal_regex(), whatever the locale of grep: Its "." matches only a
    single byte in the C locale, but a character has up to four bytes in UTF-8, and its -i
    folds case unlike Python, e.g. not "k" and the Kelvin sign, not even in C.UTF-8."""
    return "".join(
        token
        if token == r"\."
        else ".{1,4}"
        if token == "."
        else translated_text(token, ignore_case=ignore_case)
        for token in re.findall(r"\\\.|.", regex, re.DOTALL)
    )


def pcre_regex(regex: str, *, ignore_case: bool) -> str | None:
    """A regex of PCRE which matches exactly like the given one of Python, without folding case
    itself, None if we can't translate it

    Like Livestatus forwards regexes to us, see isRegexUnderstoodByEC() in its
    TableEventConsole.cc, we take literal characters, ".", "^", "$", "|", groups without "(?",
    ASCII punctuation escaped by a backslash, the quantifiers "*", "+" and "?", also lazy,
    after something to repeat, and character classes without "[" or a backslash inside, which
    PCRE takes like Python. When ignoring case, a class gets the characters it matches only
    then, but a negated one can't be translated, see _class_ignoring_case(). Our "." and "$"
    become ones independent of PCRE's newline convention."""
    translated: list[str] = []
    repeatable = False  # whether a quantifier may follow
    pos = 0
    while pos < len(regex):
        end = pos + 1
        match regex[pos]:
            case "\\":
                if regex[end : end + 1] not in _ASCII_PUNCTUATION:  # also at the end
                    return None
                end += 1
                token, repeatable = regex[pos:end], True
            case "*" | "+" | "?":
                if not repeatable:
                    return None
                if regex[end : end + 1] == "?":  # lazy
                    end += 1
                token, repeatable = regex[pos:end], False
            case "(":
                if regex[end : end + 1] == "?":
                    return None
                token, repeatable = "(", False
            case ")":
                token, repeatable = ")", True
            case "^" | "|":
                token, repeatable = regex[pos], False
            case "$":  # also in front of a final newline
                token, repeatable = r"(?=\n?\z)", False
            case "{" | "}":
                return None
            case "[":
                if (class_end := _character_class_end(regex, pos)) is None:
                    return None
                end = class_end
                char_class = regex[pos:end]
                translated_class = _class_ignoring_case(char_class) if ignore_case else char_class
                if translated_class is None:
                    return None
                token, repeatable = translated_class, True
            case ".":
                token, repeatable = r"[^\n]", True
            case char:
                token, repeatable = translated_text(char, ignore_case=ignore_case), True
        translated.append(token)
        pos = end
    return "".join(translated)


_ASCII_PUNCTUATION = frozenset(string.punctuation)


def _character_class_end(regex: str, start: int) -> int | None:
    """The end of the character class starting at the position, None if it's not one which
    Python and PCRE take alike: PCRE takes "[:", "[." and "[=" as POSIX syntax, and Python
    warns about "[" or a doubled "-", "&", "|" or "~" inside, which may become set
    operations. We don't bother with a "]" right at the start, which is a member."""
    pos = start + 1
    if regex[pos : pos + 1] in {":", ".", "="}:
        return None
    if regex[pos : pos + 1] == "^":
        pos += 1
    if regex[pos : pos + 1] == "]":
        return None
    while pos < len(regex) and regex[pos] != "]":
        if regex[pos] in "[\\" or (regex[pos] in "-&|~" and regex[pos + 1 : pos + 2] == regex[pos]):
            return None
        pos += 1
    return pos + 1 if pos < len(regex) else None


@functools.lru_cache(maxsize=1024)
def _class_ignoring_case(char_class: str) -> str | None:
    """A regex matching the characters which Python's re matches with the character class when
    ignoring case, without folding case itself: The class and the characters it matches only
    then as alternatives, e.g. "K" and the Kelvin sign for "[a-z]". Only the characters with
    another case can differ. None if the class matches a character only when respecting case,
    like a negated one, e.g. "[^a]" matches "A"."""
    respecting_case = re.compile(char_class)
    ignoring_case = re.compile(char_class, re.IGNORECASE)
    only_ignoring_case: list[str] = []
    for c in sorted(_cased_characters()):
        respected = respecting_case.fullmatch(c) is not None
        if respected and ignoring_case.fullmatch(c) is None:
            return None
        if not respected and ignoring_case.fullmatch(c) is not None:
            only_ignoring_case.append(_alternatives([c]))
    return (
        f"(?:{'|'.join([char_class, *only_ignoring_case])})" if only_ignoring_case else char_class
    )


def translated_text(text: str, *, ignore_case: bool) -> str:
    """A regex for the text, with the characters which Python's re takes as equal when
    ignoring case as alternatives if ignoring case, e.g. "(S|s|ſ)" for "s". These are exactly
    the ones it matches, so the regex matches like Python's re without folding case itself."""
    return "".join(
        _alternatives(sorted(_case_variants(char)) if ignore_case else [char]) for char in text
    )


def case_folded(text: str) -> str:
    """The text with each character replaced by one standing for all the characters which
    Python's re takes as equal to it when ignoring case, so two texts are equal ignoring case
    exactly when their folded ones are equal. Unlike str.lower(), it folds e.g. "ſ" and "s" or
    "ı" and "i" together. For ASCII, it is str.lower(), which is much faster."""
    return text.lower() if text.isascii() else text.translate(_case_folding_table())


@functools.cache
def _case_folding_table() -> Mapping[int, str]:
    """For each character with another case, the lower case of the least one which Python's re
    takes as equal to it, e.g. "s" for "S", "s" and "ſ", so it keeps str.lower() for ASCII"""
    cased = "".join(sorted(_cased_characters()))
    table: dict[int, str] = {}
    for char in cased:
        if ord(char) not in table:
            variants = re.findall(re.escape(char), cased, re.IGNORECASE)
            table.update(dict.fromkeys(map(ord, variants), min(variants).lower()))
    return table


def _alternatives(chars: Sequence[str]) -> str:
    escaped = [re.sub(r"[.\[\]()*+?{}|^$\\]", r"\\\g<0>", char) for char in chars]
    return escaped[0] if len(escaped) == 1 else f"({'|'.join(escaped)})"


def _case_variants(char: str) -> frozenset[str]:
    """The characters which Python's re takes as the given one when ignoring case"""
    return _variants_of_cased(char) if char in _cased_characters() else frozenset({char})


# Only for the characters with another case, so the cache stays small, whatever the
# characters in the filters of the clients are.
@functools.cache
def _variants_of_cased(char: str) -> frozenset[str]:
    pattern = re.compile(re.escape(char), re.IGNORECASE)
    return frozenset(c for c in _cased_characters() if pattern.fullmatch(c))


@functools.cache
def _cased_characters() -> frozenset[str]:
    """The characters with another case, the only ones which Python's re folds: It neither
    folds a character without another case nor folds a character to one without it."""
    return frozenset(
        c for c in map(chr, range(sys.maxunicode + 1)) if c.lower() != c or c.upper() != c
    )
