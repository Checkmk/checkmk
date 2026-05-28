// Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

//! Derives the program's pass/fail outcome from a `Report`.
//!
//! Everything that should fail the run is collected into `report.findings` by
//! the validators — including missing and erroring dependencies — so the
//! decision is a single emptiness check.

use super::Report;
use anyhow::Result;

/// Returns `Ok(())` if the report contains no findings, or an `Err` describing
/// the count otherwise. All finding details are surfaced via the console
/// tables and JSON report; this function is purely the pass/fail signal.
pub fn validate_report(report: &Report<'_>) -> Result<()> {
    if report.findings.is_empty() {
        return Ok(());
    }
    Err(anyhow::anyhow!(
        "Validation failed: {} finding(s)",
        report.findings.len()
    ))
}
