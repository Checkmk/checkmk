// Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

//! Report struct and public API for generating validation results.

mod console;
mod dependency_resolver;
mod errors;
mod symlink_resolver;
mod system_dependencies;
mod totals;
mod utils;
mod validate;

pub use console::summarize_report;
pub(crate) use dependency_resolver::DependencyStatus;
pub use system_dependencies::SystemDependencies;
pub use validate::validate_report;

use anyhow::Result;
use serde::Serialize;
use std::collections::{BTreeMap, HashMap};
use std::path::Path;

use crate::package::{Elf, Package};
use dependency_resolver::{DependencyResolver, DependencyResolverResult};
use errors::{scan_for_errors, SystemDependencyResolutionErrors};
use symlink_resolver::SymlinkResolver;
use totals::ReportTotals;

// Use BTreeMap to ensure alphabetical order of files when serializing to JSON.
type ReportDependencies<'a> = BTreeMap<&'a Path, HashMap<&'a str, DependencyResolverResult>>;
type ReportFiles<'a> = BTreeMap<&'a Path, &'a Elf>;

#[derive(Debug, Serialize)]
pub struct Report<'a> {
    package: String,
    totals: ReportTotals,
    errors: SystemDependencyResolutionErrors<'a>,
    dependencies: ReportDependencies<'a>,
    files: ReportFiles<'a>,
}

impl<'a> Report<'a> {
    /// Create a new report.
    ///
    /// # Errors
    /// Returns an error if the system dependencies file cannot be read.
    pub fn new(package: &'a Package, system_dependencies: &'a SystemDependencies) -> Result<Self> {
        // Compute dependencies using resolvers that only need to live during computation
        let symlink_resolver = SymlinkResolver::new(package);
        let dependencies = {
            let resolver = DependencyResolver::new(package, &symlink_resolver, system_dependencies);
            // dependencies() returns references tied to package, not the resolvers
            resolver.dependencies()
        };
        let totals = ReportTotals::new(package.files(), &package.elfs(), &dependencies);

        Ok(Self {
            package: package
                .path()
                .canonicalize()
                .unwrap_or_else(|_| package.path().to_path_buf())
                .to_string_lossy()
                .to_string(),
            totals,
            errors: scan_for_errors(package, &symlink_resolver, system_dependencies),
            dependencies,
            // Only interested in the ELF files for the report.
            // Using sequential iteration here since parallel collection into BTreeMap
            // provides minimal benefit and adds overhead.
            files: package.elfs().into_iter().collect(),
        })
    }
}
