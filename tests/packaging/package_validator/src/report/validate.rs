// Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

//! Validates reports and returns errors for missing or unresolved dependencies.

use super::{DependencyStatus, Report};
use anyhow::Result;

/// Validate the report.
///
/// # Errors
/// Returns an error if missing/error dependencies are present, or if system
/// dependencies were found bundled inside the package.
pub fn validate_report(report: &Report<'_>) -> Result<()> {
    if !report.errors.is_empty() {
        for error in &report.errors {
            eprintln!("ERROR: {error}");
        }
        return Err(anyhow::anyhow!(
            "System dependencies found in package: {} error(s)",
            report.errors.len()
        ));
    }
    if !report.dlopen_runpath_errors.is_empty() {
        for error in &report.dlopen_runpath_errors {
            eprintln!("ERROR: {error}");
        }
        return Err(anyhow::anyhow!(
            "ELF files with DT_RUNPATH and dlopen/libltdl: {} error(s)",
            report.dlopen_runpath_errors.len()
        ));
    }
    if report.totals.dependencies.error > 0 {
        for (path, dependencies) in &report.dependencies {
            for (dependency, result) in dependencies {
                if let DependencyStatus::Error(error) = &result.status {
                    eprintln!("ERROR: {}: {}: {}", path.display(), dependency, error);
                }
            }
        }
        return Err(anyhow::anyhow!(
            "Error dependencies found in the report: {} error dependencies",
            report.totals.dependencies.error
        ));
    }
    if report.totals.dependencies.missing > 0 {
        return Err(anyhow::anyhow!(
            "Missing dependencies found in the report: {} missing dependencies",
            report.totals.dependencies.missing
        ));
    }
    Ok(())
}
