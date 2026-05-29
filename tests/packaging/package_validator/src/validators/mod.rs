// Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

//! Validators: each module checks one property of a `Package` and emits
//! findings (`Finding`) for violations. `run_all` is the orchestrator
//! the report layer calls to assemble all findings.
//!
//! Each validator exposes `scan_all(...) -> Vec<Finding>` taking the
//! inputs it needs (always `&Package`, sometimes a symlink resolver or
//! system-deps handle). `dependency_resolution` is the exception: it both
//! produces a `ReportDependencies` map for the report and emits findings
//! from it via `scan_findings`.

pub(crate) mod bundled_system_deps;
pub(crate) mod dependency_resolution;
pub(crate) mod embedded_build_paths;
pub(crate) mod parse_errors;
pub(crate) mod rpath_shape;

use crate::inputs::system_dependencies::SystemDependencies;
use crate::package::Package;
use crate::report::finding::Finding;
use crate::resolution::symlinks::SymlinkResolver;

/// Run every validator that operates directly on the package (i.e. doesn't
/// need the resolved-dependency map). The caller layers
/// `dependency_resolution::scan_findings` on top once the map exists.
pub(crate) fn run_all<'a>(
    package: &'a Package,
    symlink_resolver: &SymlinkResolver<'a>,
    system_dependencies: &'a SystemDependencies,
) -> Vec<Finding<'a>> {
    let mut findings: Vec<Finding<'a>> = Vec::new();
    findings.extend(bundled_system_deps::scan_all(
        package,
        symlink_resolver,
        system_dependencies,
    ));
    findings.extend(parse_errors::scan_all(package));
    findings.extend(rpath_shape::scan_all(package));
    findings.extend(embedded_build_paths::scan_all(package));
    findings
}
