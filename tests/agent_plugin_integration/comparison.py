# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Plugin output parsing and comparison utilities.

This module provides classes for:
- Parsing agent plugin output into sections
- Comparing outputs between plugins or runs
- Calculating similarity metrics
"""

import re
from collections import Counter
from dataclasses import dataclass


@dataclass
class AgentSection:
    """Represents a single agent section from plugin output."""

    name: str
    content: list[str]
    line_start: int

    def __hash__(self) -> int:
        return hash(self.name)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, AgentSection) and self.name == other.name


class PluginOutput:
    """Parses and manages plugin output split into agent sections."""

    SECTION_PATTERN = re.compile(r"^<<<(.+?)>>>$")

    def __init__(self, output: str) -> None:
        self.raw_output = output
        self.sections: dict[str, AgentSection] = {}
        self._parse()

    def _parse(self) -> None:
        """Parse output into agent sections."""
        lines = self.raw_output.splitlines()
        current_section = None
        current_content: list[str] = []
        line_start = 0

        for i, line in enumerate(lines, 1):
            match = self.SECTION_PATTERN.match(line)
            if match:
                # Save previous section if exists
                if current_section is not None:
                    self.sections[current_section] = AgentSection(
                        name=current_section,
                        content=current_content,
                        line_start=line_start,
                    )

                # Start new section
                current_section = match.group(1)
                current_content = []
                line_start = i
            elif current_section is not None:
                # Add content to current section (skip empty lines)
                if line.strip():
                    current_content.append(line)

        # Save last section
        if current_section is not None:
            self.sections[current_section] = AgentSection(
                name=current_section,
                content=current_content,
                line_start=line_start,
            )

    def get_section_names(self) -> list[str]:
        """Get sorted list of section names."""
        return sorted(self.sections.keys())

    def get_section(self, name: str) -> AgentSection | None:
        """Get a specific section by name."""
        return self.sections.get(name)


class ComparisonResult:
    """Holds comparison results between two plugin outputs."""

    def __init__(
        self,
        old_output: PluginOutput,
        new_output: PluginOutput,
        similarity_threshold: float = 100.0,
    ) -> None:
        self.old_output = old_output
        self.new_output = new_output
        self.similarity_threshold = similarity_threshold
        self.only_in_old: list[str] = []
        self.only_in_new: list[str] = []
        self.different: list[str] = []  # Below threshold
        self.identical: list[str] = []  # At or above threshold
        self.ignored: list[str] = []  # Sections with :cached (ignored from comparison)
        self.section_similarities: dict[str, float] = {}  # Track similarity per section
        self.duplicate_keys: dict[
            str, dict[str, dict[str, int]]
        ] = {}  # Section -> source -> key -> count
        self._compare()
        self._detect_duplicates()

    def _calculate_similarity(self, keys1: set[str], keys2: set[str]) -> float:
        """Calculate similarity ratio between two sets of keys.

        Returns a percentage (0-100) indicating how similar the content is.
        Uses set overlap (Jaccard similarity).
        """
        if not keys1 and not keys2:
            return 100.0

        if not keys1 or not keys2:
            return 0.0

        # Calculate Jaccard similarity: |intersection| / |union|
        intersection = len(keys1 & keys2)
        union = len(keys1 | keys2)

        return (intersection / union) * 100.0

    def _extract_line_key(self, line: str) -> str:
        """Extract comparison key from a pipe-separated line.

        Returns the first 3 fields if available, otherwise the first 2 fields,
        otherwise the full line.
        """
        parts = line.split("|")

        if len(parts) >= 3:
            return "|".join(parts[:3])
        if len(parts) >= 2:
            return "|".join(parts[:2])
        return line

    def _normalize_section_content(self, content: list[str]) -> set[str]:
        """Normalize section content by extracting unique keys.

        For pipe-separated lines, extracts keys based on:
        1. First 3 fields (primary key) if available
        2. First 2 fields if only 2 fields exist
        3. Full line if less than 2 fields

        Returns a set of unique keys for comparison.
        """
        if not content:
            return set()

        keys: set[str] = set()
        for line in content:
            key = self._extract_line_key(line)
            keys.add(key)

        return keys

    def _key_column_counts(self, content: list[str]) -> dict[str, set[int]]:
        """Map each row key to the set of column counts (pipe-field arities) seen.

        Used to detect *structural* differences: two sections may carry the same
        set of row keys yet emit a different number of columns for a row. Only the
        arity is tracked, so volatile field *values* are ignored.
        """
        arities: dict[str, set[int]] = {}
        for line in content:
            key = self._extract_line_key(line)
            arities.setdefault(key, set()).add(len(line.split("|")))
        return arities

    def _compare(self) -> None:
        """Compare the two outputs."""
        old_sections = set(self.old_output.get_section_names())
        new_sections = set(self.new_output.get_section_names())

        # Identify cached sections (to be ignored)
        all_sections = old_sections | new_sections
        cached_sections = {s for s in all_sections if ":cached" in s}
        self.ignored = sorted(cached_sections)

        # Remove cached sections from comparison
        old_sections = old_sections - cached_sections
        new_sections = new_sections - cached_sections

        # Sections only in old
        self.only_in_old = sorted(old_sections - new_sections)

        # Sections only in new
        self.only_in_new = sorted(new_sections - old_sections)

        # Sections in both - check similarity
        for section_name in sorted(old_sections & new_sections):
            old_section = self.old_output.get_section(section_name)
            new_section = self.new_output.get_section(section_name)
            assert old_section is not None and new_section is not None

            # Normalize content for comparison (sort and use key-based matching)
            old_normalized = self._normalize_section_content(old_section.content)
            new_normalized = self._normalize_section_content(new_section.content)

            if self.similarity_threshold >= 100.0:
                # Exact comparison for 100% threshold: the same set of row keys AND
                # the same per-key column counts (structural equivalence, so a row
                # emitted with a different number of fields is caught even when its
                # key is unchanged).
                is_similar = old_normalized == new_normalized and self._key_column_counts(
                    old_section.content
                ) == self._key_column_counts(new_section.content)
                similarity = 100.0 if is_similar else 0.0
            else:
                # Calculate similarity ratio on normalized content
                similarity = self._calculate_similarity(old_normalized, new_normalized)
                is_similar = similarity >= self.similarity_threshold

            self.section_similarities[section_name] = similarity

            if is_similar:
                self.identical.append(section_name)
            else:
                self.different.append(section_name)

    def _detect_duplicates(self) -> None:
        """Detect duplicate keys within sections."""
        # Check all sections from both outputs
        all_sections = set(self.old_output.get_section_names()) | set(
            self.new_output.get_section_names()
        )

        for section_name in all_sections:
            section_duplicates: dict[str, dict[str, int]] = {}

            # Check old output
            old_section = self.old_output.get_section(section_name)
            if old_section:
                key_counts = Counter(self._extract_line_key(line) for line in old_section.content)
                duplicates = {key: count for key, count in key_counts.items() if count > 1}
                if duplicates:
                    section_duplicates["old"] = duplicates

            # Check new output
            new_section = self.new_output.get_section(section_name)
            if new_section:
                key_counts = Counter(self._extract_line_key(line) for line in new_section.content)
                duplicates = {key: count for key, count in key_counts.items() if count > 1}
                if duplicates:
                    section_duplicates["new"] = duplicates

            # Store if any duplicates found
            if section_duplicates:
                self.duplicate_keys[section_name] = section_duplicates

    def is_identical(self) -> bool:
        """Check if outputs are completely identical."""
        return not self.only_in_old and not self.only_in_new and not self.different

    def print_summary(self) -> None:
        """Print a summary of the comparison."""
        print("=== Comparison Summary ===")
        if self.similarity_threshold < 100.0:
            print(f"Similarity threshold:      {self.similarity_threshold:.1f}%")
        print(f"Identical sections:        {len(self.identical)}")
        print(f"Different sections:        {len(self.different)}")
        print(f"Only in old (mk_oracle):   {len(self.only_in_old)}")
        print(f"Only in new (mk-oracle):   {len(self.only_in_new)}")
        print(f"Ignored sections (:cached): {len(self.ignored)}")
        print()

        if self.is_identical():
            print("✓ Outputs are identical.")
        else:
            print("✗ Outputs differ.")

    def print_detailed(
        self, show_diff: bool = False, verbose: bool = False, warn_duplicates: bool = False
    ) -> None:
        """Print detailed comparison results."""
        if self.only_in_old:
            print("\n=== Sections only in OLD (mk_oracle) ===")
            for section in self.only_in_old:
                old_section = self.old_output.get_section(section)
                assert old_section is not None
                print(f"  <<<{section}>>> ({len(old_section.content)} lines)")
                if verbose:
                    self._print_section_verbose(section)

        if self.only_in_new:
            print("\n=== Sections only in NEW (mk-oracle) ===")
            for section in self.only_in_new:
                new_section = self.new_output.get_section(section)
                assert new_section is not None
                print(f"  <<<{section}>>> ({len(new_section.content)} lines)")
                if verbose:
                    self._print_section_verbose(section)

        if self.identical and verbose:
            print("\n=== Identical sections ===")
            for section in self.identical:
                old_section = self.old_output.get_section(section)
                new_section = self.new_output.get_section(section)
                assert old_section is not None and new_section is not None
                print(f"  <<<{section}>>> ({len(old_section.content)} lines)")
                self._print_section_verbose(section)

        if self.different:
            print("\n=== Sections with different content ===")
            for section in self.different:
                old_section = self.old_output.get_section(section)
                new_section = self.new_output.get_section(section)
                assert old_section is not None and new_section is not None
                similarity = self.section_similarities.get(section, 0.0)

                if self.similarity_threshold < 100.0:
                    print(
                        f"  <<<{section}>>> (similarity: {similarity:.1f}%, "
                        f"old: {len(old_section.content)} lines, "
                        f"new: {len(new_section.content)} lines)"
                    )
                else:
                    print(
                        f"  <<<{section}>>> (old: {len(old_section.content)} lines, "
                        f"new: {len(new_section.content)} lines)"
                    )

                if verbose:
                    self._print_section_verbose(section)
                elif show_diff:
                    self._print_section_diff(section)

        if show_diff and self.ignored:
            print("\n=== Ignored sections (:cached) ===")
            for section in self.ignored:
                # Try to get from old output first, then new
                ignored_section = self.old_output.get_section(section)
                if ignored_section is None:
                    ignored_section = self.new_output.get_section(section)

                if ignored_section is not None:
                    print(f"  <<<{section}>>> ({len(ignored_section.content)} lines)")
                else:
                    print(f"  <<<{section}>>>")

        # Print duplicate key warnings if requested
        if warn_duplicates:
            self._print_duplicate_warnings()

    def _print_section_diff(self, section_name: str) -> None:
        """Print diff showing which keys are missing or extra."""
        old_section = self.old_output.get_section(section_name)
        new_section = self.new_output.get_section(section_name)
        assert old_section is not None and new_section is not None

        # Extract keys from both sections
        old_keys = self._normalize_section_content(old_section.content)
        new_keys = self._normalize_section_content(new_section.content)

        # Find differences
        only_in_old = sorted(old_keys - new_keys)
        only_in_new = sorted(new_keys - old_keys)

        # Structural differences: shared keys emitted with different column counts.
        old_arities = self._key_column_counts(old_section.content)
        new_arities = self._key_column_counts(new_section.content)
        arity_mismatches = sorted(
            key
            for key in old_arities.keys() & new_arities.keys()
            if old_arities[key] != new_arities[key]
        )

        if only_in_old or only_in_new or arity_mismatches:
            print(f"\n    Diff for <<<{section_name}>>> (key-based comparison):")

            if only_in_old:
                print(f"      Keys only in OLD (mk_oracle): {len(only_in_old)}")
                for key in only_in_old[:20]:  # Show first 20
                    print(f"        - {key}")
                if len(only_in_old) > 20:
                    print(f"        ... ({len(only_in_old) - 20} more)")

            if only_in_new:
                print(f"      Keys only in NEW (mk-oracle): {len(only_in_new)}")
                for key in only_in_new[:20]:  # Show first 20
                    print(f"        + {key}")
                if len(only_in_new) > 20:
                    print(f"        ... ({len(only_in_new) - 20} more)")

            if arity_mismatches:
                print(f"      Keys with differing column counts: {len(arity_mismatches)}")
                for key in arity_mismatches[:20]:  # Show first 20
                    old_cols = sorted(old_arities[key])
                    new_cols = sorted(new_arities[key])
                    print(f"        ! {key}: old cols={old_cols}, new cols={new_cols}")
                if len(arity_mismatches) > 20:
                    print(f"        ... ({len(arity_mismatches) - 20} more)")

    def _build_key_to_lines(self, content: list[str]) -> dict[str, list[str]]:
        """Build a mapping from extracted key to full lines."""
        key_to_lines: dict[str, list[str]] = {}
        for line in content:
            key = self._extract_line_key(line)
            key_to_lines.setdefault(key, []).append(line)
        return key_to_lines

    def _print_section_verbose(self, section_name: str) -> None:
        """Print all keys in side-by-side format showing full lines."""
        old_section = self.old_output.get_section(section_name)
        new_section = self.new_output.get_section(section_name)

        # Build key-to-lines mappings
        old_key_lines = self._build_key_to_lines(old_section.content) if old_section else {}
        new_key_lines = self._build_key_to_lines(new_section.content) if new_section else {}

        old_keys = set(old_key_lines.keys())
        new_keys = set(new_key_lines.keys())

        # Skip if no keys in either section
        if not old_keys and not new_keys:
            return

        # Find common and unique keys
        common_keys = sorted(old_keys & new_keys)
        only_in_old = sorted(old_keys - new_keys)
        only_in_new = sorted(new_keys - old_keys)

        col_width = 60  # Fixed column width with truncation

        print(f"\n    Side-by-side view for <<<{section_name}>>>:")
        print(f"    {'OLD (mk_oracle)':<{col_width}} | {'NEW (mk-oracle)'}")
        print(f"    {'-' * col_width}-+-{'-' * col_width}")

        def truncate(text: str, width: int) -> str:
            return text[: width - 1] + "~" if len(text) > width else text

        def print_key_with_lines(
            key: str, old_lines: list[str], new_lines: list[str], marker: str
        ) -> None:
            key_display = truncate(key, col_width)
            print(f"    {key_display:<{col_width}} {marker} {key_display}")
            max_count = max(len(old_lines), len(new_lines))
            for i in range(max_count):
                old_text = f"└─ {old_lines[i]}" if i < len(old_lines) else ""
                new_text = f"└─ {new_lines[i]}" if i < len(new_lines) else ""
                old_display = truncate(old_text, col_width)
                new_display = truncate(new_text, col_width)
                print(f"    {old_display:<{col_width}}   {new_display}")

        # Print common keys (pair up lines by position)
        for key in common_keys:
            print_key_with_lines(key, old_key_lines[key], new_key_lines[key], "|")

        # Print keys only in old
        for key in only_in_old:
            print_key_with_lines(key, old_key_lines[key], [], "<")

        # Print keys only in new
        for key in only_in_new:
            print_key_with_lines(key, [], new_key_lines[key], ">")

    def _print_duplicate_warnings(self) -> None:
        """Print warnings for sections with duplicate keys."""
        if not self.duplicate_keys:
            return

        print("\n=== ⚠️  WARNINGS: Duplicate Keys Detected ===")
        print("The following sections contain duplicate keys (same key appears multiple times):")
        print()

        for section_name in sorted(self.duplicate_keys.keys()):
            duplicates = self.duplicate_keys[section_name]
            print(f"  <<<{section_name}>>>:")

            if "old" in duplicates:
                print("    In OLD (mk_oracle):")
                for key, count in sorted(duplicates["old"].items()):
                    print(f"      - '{key}' appears {count} times")

            if "new" in duplicates:
                print("    In NEW (mk-oracle):")
                for key, count in sorted(duplicates["new"].items()):
                    print(f"      - '{key}' appears {count} times")

            print()
