// Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

//! Validates reports and returns errors for missing or unresolved dependencies.

use super::{DependencyStatus, Report};
use anyhow::Result;

/// Validate the report.
///
/// # Errors
/// Returns an error if missing/error dependencies are present.
pub fn validate_report(report: &Report<'_>) -> Result<()> {
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
