// Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

//! Validates `RPATH`/`RUNPATH` settings by checking if dependencies can be resolved. Handles `$ORIGIN` substitution and path normalization.

use rayon::iter::IntoParallelRefIterator;
use rayon::prelude::*;
use serde::{Deserialize, Serialize, Serializer};
use std::collections::HashMap;
use std::path::{Path, PathBuf};

use crate::package::{Elf, Package};
use crate::report::symlink_resolver::{SymlinkResolutionResult, SymlinkResolver};
use crate::report::system_dependencies::SystemDependencies;
use crate::report::ReportDependencies;

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize, Default)]
pub(crate) enum DependencyStatus {
    Found, // The dependency was found in the package or system and was resolved to a path.
    #[default]
    Missing, // The dependency was not found in the package or the system.
    Error(String), // An error occurred while resolving the dependency.
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize, Default)]
pub(crate) enum DependencyKind {
    System,
    Package,
    #[default]
    Unknown,
}

#[derive(Debug, Clone, PartialEq, Eq, Deserialize)]
pub(crate) struct DependencyResolverResult {
    pub(crate) status: DependencyStatus,
    pub(crate) kind: DependencyKind,
    pub(crate) path: Option<PathBuf>,
    pub(crate) searched_paths: Vec<PathBuf>,
}

impl Serialize for DependencyResolverResult {
    fn serialize<S>(&self, serializer: S) -> Result<S::Ok, S::Error>
    where
        S: Serializer,
    {
        use serde::ser::SerializeStruct;
        let mut state = serializer.serialize_struct("DependencyResolverResult", 3)?;
        state.serialize_field("status", &self.status)?;
        state.serialize_field("type", &self.kind)?;

        // Only serialize path if it's Some
        if let Some(ref path) = self.path {
            state.serialize_field("path", path)?;
        }

        // Only serialize searched_paths if path is None
        if self.path.is_none() {
            state.serialize_field("searched_paths", &self.searched_paths)?;
        }

        state.end()
    }
}

impl DependencyResolverResult {
    pub(crate) fn new(
        status: DependencyStatus,
        r#type: DependencyKind,
        searched_paths: Vec<PathBuf>,
        path: impl Into<Option<PathBuf>>,
    ) -> Self {
        Self {
            status,
            kind: r#type,
            path: path.into(),
            searched_paths,
        }
    }
}

pub(crate) struct DependencyResolver<'a, 'b, 'c> {
    package: &'a Package,
    symlink_resolver: &'b SymlinkResolver<'a>,
    system_dependencies: &'c SystemDependencies,
}

impl<'a, 'b, 'c> DependencyResolver<'a, 'b, 'c> {
    pub(crate) fn new(
        package: &'a Package,
        symlink_resolver: &'b SymlinkResolver<'a>,
        system_dependencies: &'c SystemDependencies,
    ) -> Self {
        Self {
            package,
            symlink_resolver,
            system_dependencies,
        }
    }

    pub(crate) fn dependencies(&self) -> ReportDependencies<'a> {
        self.package
            .elfs()
            .par_iter()
            .map(|(path, elf)| (*path, self.resolve(path, elf)))
            .collect()
    }

    fn resolve(&self, path: &Path, elf: &'a Elf) -> HashMap<&'a str, DependencyResolverResult> {
        elf.dependencies()
            .par_iter()
            .map(|dependency| {
                (
                    dependency.as_str(),
                    self.resolve_dependency(path, elf, dependency),
                )
            })
            .collect()
    }

    fn resolve_dependency(
        &self,
        path: &Path,
        elf: &'a Elf,
        dependency: &'a str,
    ) -> DependencyResolverResult {
        if self.system_dependencies.contains(dependency) {
            // Dependencies should *not* be defined as system dependencies and exist in the package.
            // Either the dependency was wrongly defined as a system dependency, or the package contains the dependency it shouldn't.
            // This logic is handled by the `SystemDependencyResolver::scan_for_errors` so we can ignore the case here.
            return DependencyResolverResult::new(
                DependencyStatus::Found,
                DependencyKind::System,
                Vec::new(),
                None,
            );
        }
        let search_paths = Self::determine_search_paths(path, elf);

        // Cannot be parallelized, as the order is important when searching for the dependency.
        // We want to search the paths in order of definition.
        for search_path in &search_paths {
            let dependency_path = search_path.join(dependency);
            let (status, kind, path) = self.find_dependency(&dependency_path);
            match status {
                DependencyStatus::Missing => {} // Continue to the next search path.
                DependencyStatus::Found => {
                    return DependencyResolverResult::new(status, kind, search_paths, path);
                }
                error @ DependencyStatus::Error(_) => {
                    // Stop searching and return the error.
                    return DependencyResolverResult::new(error, kind, search_paths, path);
                }
            }
        }
        // Not found in any search path, so it's missing.
        DependencyResolverResult::new(
            DependencyStatus::Missing,
            DependencyKind::Unknown,
            search_paths,
            None,
        )
    }

    /// Determine the search paths for resolving dependencies.
    ///
    /// The search order is:
    /// 1. RPATH/RUNPATH entries from the ELF file (with `$ORIGIN` substitution)
    /// 2. Common library paths from `/etc/ld.so.conf` conventions
    /// 3. Default system library paths
    ///
    /// We do not check common paths, or default system paths, but instead use
    /// `SystemDependencyResolver` to check if the dependency is a system dependency instead.
    /// It only checks the dependency name, not the path, so it's distro-agnostic.
    fn determine_search_paths(path: &Path, elf: &'a Elf) -> Vec<PathBuf> {
        let origin = path.parent().unwrap_or_else(|| Path::new("/"));
        elf.normalize_paths(origin)
    }

    // Assumes the calling function has checked that the path exists in the package.
    fn find_dependency(&self, path: &Path) -> (DependencyStatus, DependencyKind, Option<PathBuf>) {
        if let Some(symlink_result) = self.symlink_resolver.resolve(path) {
            // If the dependency is a symlink, we need to resolve it to the target path.
            match symlink_result {
                SymlinkResolutionResult::NotFound(target_path) => {
                    self.resolve_system_dependency(target_path)
                }
                SymlinkResolutionResult::Found(target_path) => {
                    self.resolve_package_dependency(target_path)
                }
                SymlinkResolutionResult::CycleDetected() => (
                    DependencyStatus::Error(format!("Symlink cycle detected: {}", path.display())),
                    DependencyKind::Unknown,
                    None,
                ),
            }
        } else {
            // Not a symlink, check if the dependency can be found in the package.
            self.resolve_package_dependency(path)
        }
    }

    fn resolve_package_dependency(
        &self,
        path: &Path,
    ) -> (DependencyStatus, DependencyKind, Option<PathBuf>) {
        if self.package.elfs().contains_key(path) {
            // Target exists and is an ELF file.
            (
                DependencyStatus::Found,
                DependencyKind::Package,
                Some(path.to_path_buf()),
            )
        } else if self.package.files().contains_key(path) {
            // Target exists, but is not an ELF file.
            (
                DependencyStatus::Error(format!(
                    "Found in package, but not an ELF file: {}",
                    path.display()
                )),
                DependencyKind::Package,
                Some(path.to_path_buf()),
            )
        } else {
            (DependencyStatus::Missing, DependencyKind::Unknown, None)
        }
    }

    fn resolve_system_dependency(
        &self,
        path: &Path,
    ) -> (DependencyStatus, DependencyKind, Option<PathBuf>) {
        let dependency_name = path
            .file_name()
            .and_then(|name| name.to_str())
            .unwrap_or("");
        if self.system_dependencies.contains(dependency_name) {
            (
                DependencyStatus::Found,
                DependencyKind::System,
                Some(path.to_path_buf()),
            )
        } else {
            (
                DependencyStatus::Missing,
                DependencyKind::Unknown,
                Some(path.to_path_buf()),
            )
        }
    }
}
