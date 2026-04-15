// Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

//! Report struct and public API for generating validation results.

mod console;
mod dependency_resolver;
mod errors;
mod ignored_files;
mod symlink_resolver;
mod system_dependencies;
mod totals;
mod utils;
mod validate;

pub use console::summarize_report;
pub(crate) use dependency_resolver::DependencyStatus;
pub use ignored_files::IgnoredFiles;
pub use system_dependencies::SystemDependencies;
pub use validate::validate_report;

use anyhow::Result;
use serde::Serialize;
use std::collections::{BTreeMap, HashMap};
use std::path::Path;

use crate::package::{Elf, Package, PackageElfs};
use dependency_resolver::{DependencyResolver, DependencyResolverResult};
use errors::{
    scan_for_errors, scan_for_runpath_dlopen_conflicts, DlopenRunpathErrors,
    SystemDependencyResolutionErrors,
};
use symlink_resolver::SymlinkResolver;
use totals::ReportTotals;

// Use BTreeMap to ensure alphabetical order of files when serializing to JSON.
type ReportDependencies<'a> = BTreeMap<&'a Path, HashMap<&'a str, DependencyResolverResult>>;
type ReportFiles<'a> = BTreeMap<&'a Path, &'a Elf>;

#[derive(Debug, Serialize)]
pub struct Report<'a> {
    package: String,
    totals: ReportTotals,
    pub(super) errors: SystemDependencyResolutionErrors<'a>,
    pub(super) dlopen_runpath_errors: DlopenRunpathErrors<'a>,
    dependencies: ReportDependencies<'a>,
    files: ReportFiles<'a>,
}

impl<'a> Report<'a> {
    /// Create a new report.
    ///
    /// # Errors
    /// Returns an error if the system dependencies file cannot be read.
    pub fn new(
        package: &'a Package,
        system_dependencies: &'a SystemDependencies,
        ignore_files: &IgnoredFiles,
    ) -> Result<Self> {
        // Compute dependencies using resolvers that only need to live during computation
        let symlink_resolver = SymlinkResolver::new(package);

        // Exclude files that won't execute on the Checkmk server (e.g. agent executables
        // deployed to monitored systems whose deps target the monitored host's environment).
        let active_elfs: PackageElfs = package
            .elfs()
            .into_iter()
            .filter(|(path, _)| !ignore_files.contains(path))
            .collect();

        let dependencies = {
            let resolver = DependencyResolver::new(package, &symlink_resolver, system_dependencies);
            // dependencies() returns references tied to package, not the resolvers
            resolver.dependencies(&active_elfs)
        };
        let totals = ReportTotals::new(package.files(), &active_elfs, &dependencies);

        Ok(Self {
            package: package
                .path()
                .canonicalize()
                .unwrap_or_else(|_| package.path().to_path_buf())
                .to_string_lossy()
                .to_string(),
            totals,
            errors: scan_for_errors(package, &symlink_resolver, system_dependencies),
            dlopen_runpath_errors: scan_for_runpath_dlopen_conflicts(&active_elfs, &dependencies),
            dependencies,
            // Only interested in the non-ignored ELF files for the report.
            // Using sequential iteration here since parallel collection into BTreeMap
            // provides minimal benefit and adds overhead.
            files: active_elfs.into_iter().collect(),
        })
    }
}
