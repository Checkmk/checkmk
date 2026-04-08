// Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

//! Formats and prints report summaries to the console.

use comfy_table::{Cell, Table};
use std::path::Path;

use super::utils::find_common_prefix;
use super::{DependencyStatus, Report};

/// Summarize the report to the console.
///
/// Prints the summary of the report including package info, ELF statistics,
/// dependency statistics, and any missing dependencies.
pub fn summarize_report(report: &Report<'_>) {
    // Print summary section
    println!("Package: {}", report.package);
    println!("Total files: {}\n", report.totals.files);

    println!("{}\n", elf_table(report));
    println!("{}\n", dependency_type_table(report));
    println!("{}\n", dependency_status_table(report));

    // Collect ELF files with missing dependencies
    let missing_deps = missing_dependencies(report);

    // Display table of missing dependencies
    if !missing_deps.is_empty() {
        let table = missing_dependencies_table(&missing_deps);
        println!("{table}");
        println!(
            "\nTotal: {} ELF file(s) with missing dependencies",
            missing_deps.len()
        );
    }
}

/// Create a table with the default preset styling.
fn default_table_preset() -> Table {
    let mut table = Table::new();
    table
        .load_preset(comfy_table::presets::UTF8_FULL_CONDENSED)
        .apply_modifier(comfy_table::modifiers::UTF8_ROUND_CORNERS)
        .set_content_arrangement(comfy_table::ContentArrangement::Dynamic);
    table
}

/// Create a table showing ELF file type statistics.
fn elf_table(report: &Report) -> Table {
    let mut table = default_table_preset();
    table
        .set_header(vec![
            Cell::new("ELF Type").add_attribute(comfy_table::Attribute::Bold),
            Cell::new("Count").add_attribute(comfy_table::Attribute::Bold),
        ])
        .add_row(vec![
            Cell::new("Binaries"),
            Cell::new(report.totals.elfs.binaries),
        ])
        .add_row(vec![
            Cell::new("Shared libraries"),
            Cell::new(report.totals.elfs.shared_libraries),
        ])
        .add_row(vec![
            Cell::new("Relocatable"),
            Cell::new(report.totals.elfs.relocatable),
        ])
        .add_row(vec![Cell::new("Core"), Cell::new(report.totals.elfs.core)])
        .add_row(vec![Cell::new("None"), Cell::new(report.totals.elfs.none)])
        .add_row(vec![
            Cell::new("Total").add_attribute(comfy_table::Attribute::Bold),
            Cell::new(report.totals.elfs.total).add_attribute(comfy_table::Attribute::Bold),
        ]);
    table
}

/// Create a table showing dependency type statistics.
fn dependency_type_table(report: &Report) -> Table {
    let mut table = default_table_preset();
    table
        .set_header(vec![
            Cell::new("Dependency Type").add_attribute(comfy_table::Attribute::Bold),
            Cell::new("Count").add_attribute(comfy_table::Attribute::Bold),
        ])
        .add_row(vec![
            Cell::new("System"),
            Cell::new(report.totals.dependencies.system),
        ])
        .add_row(vec![
            Cell::new("Package"),
            Cell::new(report.totals.dependencies.package),
        ])
        .add_row(vec![
            Cell::new("Unknown"),
            Cell::new(report.totals.dependencies.unknown),
        ])
        .add_row(vec![
            Cell::new("Total").add_attribute(comfy_table::Attribute::Bold),
            Cell::new(report.totals.dependencies.total).add_attribute(comfy_table::Attribute::Bold),
        ]);
    table
}

/// Create a table showing dependency status statistics.
fn dependency_status_table(report: &Report) -> Table {
    let mut table = default_table_preset();
    table
        .set_header(vec![
            Cell::new("Dependency Status").add_attribute(comfy_table::Attribute::Bold),
            Cell::new("Count").add_attribute(comfy_table::Attribute::Bold),
        ])
        .add_row(vec![
            Cell::new("Missing"),
            Cell::new(report.totals.dependencies.missing),
        ])
        .add_row(vec![
            Cell::new("Found"),
            Cell::new(report.totals.dependencies.found),
        ])
        .add_row(vec![
            Cell::new("Error"),
            Cell::new(report.totals.dependencies.error),
        ])
        .add_row(vec![
            Cell::new("Total").add_attribute(comfy_table::Attribute::Bold),
            Cell::new(report.totals.dependencies.total).add_attribute(comfy_table::Attribute::Bold),
        ]);
    table
}

/// Collect ELF files with missing dependencies from the report.
fn missing_dependencies<'a>(report: &Report<'a>) -> Vec<(&'a Path, Vec<&'a str>)> {
    let mut result: Vec<(&'a Path, Vec<&'a str>)> = report
        .dependencies
        .iter()
        .filter_map(|(elf_path, deps_map)| {
            let missing: Vec<&str> = deps_map
                .iter()
                .filter(|(_, result)| matches!(result.status, DependencyStatus::Missing))
                .map(|(dep_name, _)| *dep_name)
                .collect();

            (!missing.is_empty()).then_some((*elf_path, missing))
        })
        .collect();
    result.sort_by_key(|(path, _)| *path);
    result
}

/// Create a table showing missing dependencies for each ELF file.
fn missing_dependencies_table(missing_dependencies: &[(&Path, Vec<&str>)]) -> Table {
    // Find common prefix to strip for cleaner display
    let paths: Vec<&Path> = missing_dependencies.iter().map(|(p, _)| *p).collect();
    let common_prefix = find_common_prefix(&paths);

    let mut table = default_table_preset();
    table.set_header(vec![
        Cell::new("ELF File").add_attribute(comfy_table::Attribute::Bold),
        Cell::new("Missing Dependencies").add_attribute(comfy_table::Attribute::Bold),
    ]);

    // Add rows
    for (path, deps) in missing_dependencies {
        let display_path = if let Some(prefix) = &common_prefix {
            path.strip_prefix(prefix).unwrap_or(path)
        } else {
            path
        };
        let path_str = display_path.to_string_lossy();
        let deps_str = deps.join(", ");
        table.add_row(vec![Cell::new(path_str.as_ref()), Cell::new(deps_str)]);
    }
    table
}
