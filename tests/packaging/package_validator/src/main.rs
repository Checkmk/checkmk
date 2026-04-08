// Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.
mod args;

use anyhow::{Context, Result};
use clap::Parser;
use std::fs::File;
use std::path::Path;

use args::Args;
use package_validator::package::Package;
use package_validator::report::{summarize_report, validate_report, Report, SystemDependencies};
use std::path::PathBuf;

fn main() -> Result<()> {
    let args = Args::parse();
    let package = extract_package(&args.package)?;
    let system_dependencies = create_system_dependencies(args.system_dependencies.as_ref())?;
    let report = Report::new(&package, &system_dependencies)?;
    write_report_to_file(&report, &args.report)?;
    summarize_report(&report);
    validate_report(&report)
}

/// Get the package from a filepath.
///
/// # Errors
/// Returns an error if the package type cannot be determined or is unsupported.
fn extract_package(path: &Path) -> Result<Package> {
    eprintln!("Extracting package: package={}", path.display());

    let package = Package::new(path.to_path_buf())
        .with_context(|| format!("Failed to extract package: {}", path.display()))?;

    eprintln!(
        "Extraction completed: package={}, files={}",
        path.display(),
        package.files().len()
    );
    Ok(package)
}

fn create_system_dependencies(path: Option<&PathBuf>) -> Result<SystemDependencies> {
    if let Some(system_dependencies) = path {
        Ok(SystemDependencies::from_file(system_dependencies)
            .with_context(|| "Failed to read system dependencies file")?)
    } else {
        Ok(SystemDependencies::empty())
    }
}

/// Write the report to a file.
///
/// # Errors
/// Returns an error if the report cannot be serialized to JSON or if the file cannot be created.
fn write_report_to_file(report: &Report<'_>, dest: &Path) -> Result<()> {
    eprintln!("Writing report to file: file={}", dest.display());
    let file = File::create(dest)
        .with_context(|| format!("Failed to create JSON output file: {}", dest.display()))?;
    serde_json::to_writer_pretty(file, report)
        .with_context(|| format!("Failed to serialize report to JSON: {}", dest.display()))?;
    Ok(())
}
