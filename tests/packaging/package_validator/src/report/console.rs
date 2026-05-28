// Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

//! Formats and prints report summaries to the console.

use comfy_table::{Cell, Table};
use std::io::IsTerminal;
use std::path::Path;

use super::finding::Finding;
use super::utils::find_common_prefix;
use super::Report;

/// A path-keyed section sourced from `report.findings`: extract the path and a
/// pre-rendered right-hand value for the findings of one variant, or `None` for
/// findings of other variants.
type FindingRow<'a> = Option<(&'a Path, String)>;

/// A single path-keyed finding section: its column headers, its summary label,
/// and a matcher that turns a single finding into a [`FindingRow`].
type FindingSection = (
    (&'static str, &'static str),
    &'static str,
    for<'a> fn(&Finding<'a>) -> FindingRow<'a>,
);

/// The path-keyed finding sections, in display order. Each entry is its column
/// headers, its summary label, and a matcher that turns a single finding into a
/// table row (or `None` if the finding belongs to a different section). Adding a
/// section is one entry here, not a new hand-written block in `summarize_report`.
///
/// Every variant is one finding per ELF, so each matcher yields at most one row
/// per file and the "Total: N ELF file(s)" labels are accurate counts of files.
///
/// `SystemDependencyFoundInPackage` is absent on purpose: it is keyed by
/// dependency name rather than a path, so it gets its own table below. The
/// `every_finding_is_rendered` guard keeps this list exhaustive.
const FINDING_SECTIONS: &[FindingSection] = &[
    (
        ("ELF File", "Missing Dependencies"),
        "ELF file(s) with missing dependencies",
        |f| match f {
            Finding::MissingDependency { path, dependencies } => {
                Some((*path, dependencies.join(", ")))
            }
            _ => None,
        },
    ),
    (
        ("ELF File", "Invalid Entries"),
        "ELF file(s) with invalid RPATH/RUNPATH entries",
        |f| match f {
            Finding::RpathShape { path, paths } => Some((*path, paths.join("\n"))),
            _ => None,
        },
    ),
    (
        ("ELF File", "Parse Error"),
        "ELF file(s) that could not be parsed",
        |f| match f {
            Finding::UnreadableElf { path, message } => Some((*path, (*message).to_string())),
            _ => None,
        },
    ),
    (
        ("ELF File", "Dependency Errors"),
        "ELF file(s) with dependency resolution errors",
        |f| match f {
            Finding::DependencyResolutionError { path, errors } => Some((
                *path,
                errors
                    .iter()
                    .map(|(dependency, message)| format!("{dependency}: {message}"))
                    .collect::<Vec<_>>()
                    .join("\n"),
            )),
            _ => None,
        },
    ),
];

/// Compile-time guard that every `Finding` variant is rendered by this module.
/// Adding a variant breaks this exhaustive match until it is wired up — either as
/// a [`FINDING_SECTIONS`] entry (path-keyed) or its own table like the
/// dependency-name-keyed `SystemDependencyFoundInPackage`. Never called.
#[allow(dead_code)]
fn every_finding_is_rendered(f: &Finding<'_>) {
    match f {
        // Rendered via FINDING_SECTIONS.
        Finding::MissingDependency { .. }
        | Finding::RpathShape { .. }
        | Finding::UnreadableElf { .. }
        | Finding::DependencyResolutionError { .. } => {}
        // Rendered via its own dependency-name-keyed table below.
        Finding::SystemDependencyFoundInPackage { .. } => {}
    }
}

/// Summarize the report to the console.
///
/// Prints the summary of the report including package info, ELF statistics,
/// dependency statistics, any missing dependencies, and any validation errors.
pub fn summarize_report(report: &Report<'_>) {
    println!("Package: {}", report.package);
    println!("Total files: {}\n", report.totals.files);

    let elfs = &report.totals.elfs;
    println!(
        "{}\n",
        counts_table(
            ("ELF Type", "Count"),
            &[
                ("Binaries", elfs.binaries),
                ("Shared libraries", elfs.shared_libraries),
                ("Relocatable", elfs.relocatable),
                ("Core", elfs.core),
                ("None", elfs.none),
            ],
            elfs.total,
        )
    );

    let deps = &report.totals.dependencies;
    println!(
        "{}\n",
        counts_table(
            ("Dependency Type", "Count"),
            &[
                ("System", deps.system),
                ("Package", deps.package),
                ("Unknown", deps.unknown),
            ],
            deps.total,
        )
    );
    println!(
        "{}\n",
        counts_table(
            ("Dependency Status", "Count"),
            &[
                ("Missing", deps.missing),
                ("Found", deps.found),
                ("Error", deps.error),
            ],
            deps.total,
        )
    );

    for &(headers, label, extract) in FINDING_SECTIONS {
        let rows = sorted_by_path(report.findings.iter().filter_map(|f| extract(f)));
        print_section(&rows, |rows| path_keyed_table(rows, headers), label);
    }

    // System dependencies are keyed by dependency name rather than a path, so
    // they get a bespoke table (see `system_dependency_errors_table`).
    let mut sys_errors: Vec<(&str, &[&Path])> = report
        .findings
        .iter()
        .filter_map(|e| match e {
            Finding::SystemDependencyFoundInPackage { dependency, paths } => {
                Some((*dependency, paths.as_slice()))
            }
            _ => None,
        })
        .collect();
    sys_errors.sort_by_key(|(dep, _)| *dep);
    print_section(
        &sys_errors,
        system_dependency_errors_table,
        "system dependency/dependencies found in package",
    );
}

/// Sort an iterator of `(&Path, _)` tuples by path, collecting into a Vec.
fn sorted_by_path<'a, T>(iter: impl Iterator<Item = (&'a Path, T)>) -> Vec<(&'a Path, T)> {
    let mut rows: Vec<(&'a Path, T)> = iter.collect();
    rows.sort_by_key(|(path, _)| *path);
    rows
}

/// Print a section: the rendered table followed by a "Total: N <label>" line.
/// No output if `rows` is empty.
fn print_section<T>(rows: &[T], render: impl FnOnce(&[T]) -> Table, label: &str) {
    if rows.is_empty() {
        return;
    }
    println!("{}\n", render(rows));
    println!("Total: {} {}\n", rows.len(), label);
}

/// Create a table with the default preset styling.
///
/// Uses Unicode box-drawing characters when stdout is a TTY (e.g. `bazel run`
/// or direct invocation), and plain ASCII otherwise (e.g. `bazel test`, CI).
fn default_table_preset() -> Table {
    let mut table = Table::new();
    if std::io::stdout().is_terminal() {
        table
            .load_preset(comfy_table::presets::UTF8_FULL_CONDENSED)
            .apply_modifier(comfy_table::modifiers::UTF8_ROUND_CORNERS);
    } else {
        table.load_preset(comfy_table::presets::ASCII_FULL_CONDENSED);
    }
    table.set_content_arrangement(comfy_table::ContentArrangement::Dynamic);
    table
}

fn bold_header(headers: (&str, &str)) -> Vec<Cell> {
    vec![
        Cell::new(headers.0).add_attribute(comfy_table::Attribute::Bold),
        Cell::new(headers.1).add_attribute(comfy_table::Attribute::Bold),
    ]
}

/// Build a 2-column "label / count" table with a trailing bold **Total** row.
fn counts_table(headers: (&str, &str), rows: &[(&str, usize)], total: usize) -> Table {
    let mut table = default_table_preset();
    table.set_header(bold_header(headers));
    for (label, count) in rows {
        table.add_row(vec![Cell::new(*label), Cell::new(count)]);
    }
    table.add_row(vec![
        Cell::new("Total").add_attribute(comfy_table::Attribute::Bold),
        Cell::new(total).add_attribute(comfy_table::Attribute::Bold),
    ]);
    table
}

/// Build a 2-column table whose left column is a path (with the common prefix
/// stripped for readability) and whose right column is a pre-rendered value.
fn path_keyed_table(rows: &[(&Path, String)], headers: (&str, &str)) -> Table {
    let paths: Vec<&Path> = rows.iter().map(|(p, _)| *p).collect();
    let common_prefix = find_common_prefix(&paths);

    let mut table = default_table_preset();
    table.set_header(bold_header(headers));
    for (path, value) in rows {
        let display_path = common_prefix
            .as_deref()
            .and_then(|prefix| path.strip_prefix(prefix).ok())
            .unwrap_or(path);
        table.add_row(vec![
            Cell::new(display_path.to_string_lossy().as_ref()),
            Cell::new(value),
        ]);
    }
    table
}

/// Create a table showing system dependencies found bundled inside the package.
/// The key is the dependency name, not a path, so this can't use `path_keyed_table`.
fn system_dependency_errors_table(rows: &[(&str, &[&Path])]) -> Table {
    let mut table = default_table_preset();
    table.set_header(bold_header(("Dependency", "Found at Path(s)")));
    for (dependency, paths) in rows {
        let paths_str = paths
            .iter()
            .map(|p| p.to_string_lossy())
            .collect::<Vec<_>>()
            .join(", ");
        table.add_row(vec![Cell::new(*dependency), Cell::new(paths_str)]);
    }
    table
}
