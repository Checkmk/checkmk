// Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

//! Defines error types for report validation (e.g., system dependencies found in package).

use serde::Serialize;
use std::collections::HashMap;
use std::path::Path;
use thiserror::Error;

use super::system_dependencies::SystemDependencies;
use crate::package::Package;
use crate::report::symlink_resolver::{SymlinkResolutionResult, SymlinkResolver};

pub(crate) type SystemDependencyResolutionErrors<'a> = Vec<ReportError<'a>>;

#[derive(Debug, Error, Serialize)]
pub(crate) enum ReportError<'a> {
    // Dependencies should *not* be defined as system dependencies and exist in the package.
    // Either the dependency was wrongly defined as a system dependency, or the package
    // contains the dependency it shouldn't.
    #[error("System dependency {dependency}: Found in package at path(s): {paths:?}")]
    SystemDependencyFoundInPackage {
        dependency: &'a str,
        paths: Vec<&'a Path>,
    },
}

/// Scans a package for errors.
///
/// Returns a list of errors for any system dependencies found in the package.
/// Symlinks pointing outside the package are excluded from error detection.
pub(crate) fn scan_for_errors<'a>(
    package: &'a Package,
    symlink_resolver: &SymlinkResolver<'a>,
    system_dependencies: &'a SystemDependencies,
) -> SystemDependencyResolutionErrors<'a> {
    let system_dependencies = system_dependencies.dependencies();
    // Map file name to paths, and including only system dependencies.
    package
        .files()
        .iter()
        .filter_map(|(path, _)| {
            path.file_name()
                .and_then(|f| f.to_str())
                // Any system dependency included in the package is an error.
                .filter(|name| system_dependencies.contains(*name))
                // Except if it is a symlink to a file outside of the package.
                .filter(|_| {
                    symlink_resolver
                        .resolve(path.as_path())
                        .is_none_or(|result| {
                            !matches!(result, SymlinkResolutionResult::NotFound(_))
                        }) // Regular files (not symlinks) should be included
                })
                .map(|name| (name, path))
        })
        .fold(
            HashMap::<&str, Vec<&Path>>::new(),
            |mut acc, (name, path)| {
                acc.entry(name).or_default().push(path);
                acc
            },
        )
        .into_iter()
        .map(
            |(name, paths)| ReportError::SystemDependencyFoundInPackage {
                dependency: name,
                paths,
            },
        )
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::package::{Package, PackageFile, PackageFiles};
    use crate::report::symlink_resolver::SymlinkResolver;
    use std::io::Write;
    use std::path::{Path, PathBuf};
    use tempfile::NamedTempFile;

    fn create_system_dependencies(deps: &[&str]) -> SystemDependencies {
        let mut file = NamedTempFile::new().unwrap();
        for dep in deps {
            writeln!(file, "{}", dep).unwrap();
        }
        file.flush().unwrap();
        SystemDependencies::from_file(file.path()).unwrap()
    }

    fn create_test_package(files: Vec<(&str, PackageFile)>) -> Package {
        let package_files: PackageFiles = files
            .into_iter()
            .map(|(path, file)| (PathBuf::from(path), file))
            .collect();
        Package::new_for_testing(PathBuf::from("/test/package.deb"), package_files)
    }

    fn assert_error_matches(
        error: &ReportError,
        expected_dependency: &str,
        expected_paths: &[&str],
    ) {
        match error {
            ReportError::SystemDependencyFoundInPackage { dependency, paths } => {
                assert_eq!(*dependency, expected_dependency);
                assert_eq!(paths.len(), expected_paths.len());
                for expected_path in expected_paths {
                    assert!(
                        paths.contains(&Path::new(expected_path)),
                        "Expected path {} not found in {:?}",
                        expected_path,
                        paths
                    );
                }
            }
        }
    }

    fn get_error_dependencies<'a>(
        errors: &'a SystemDependencyResolutionErrors<'a>,
    ) -> Vec<&'a str> {
        errors
            .iter()
            .map(|e| match e {
                ReportError::SystemDependencyFoundInPackage { dependency, .. } => *dependency,
            })
            .collect()
    }

    #[test]
    fn test_no_errors_when_no_system_dependencies() {
        let package = create_test_package(vec![
            ("/usr/bin/myapp", PackageFile::File),
            ("/usr/lib/myapp.so", PackageFile::File),
        ]);
        let system_deps = create_system_dependencies(&["libm.so.6", "libc.so.6"]);
        let symlink_resolver = SymlinkResolver::new(&package);

        let errors = scan_for_errors(&package, &symlink_resolver, &system_deps);
        assert!(errors.is_empty());
    }

    #[test]
    fn test_error_detected_for_single_system_dependency() {
        let package = create_test_package(vec![
            ("/usr/bin/myapp", PackageFile::File),
            ("/usr/lib/libm.so.6", PackageFile::File),
        ]);
        let system_deps = create_system_dependencies(&["libm.so.6"]);
        let symlink_resolver = SymlinkResolver::new(&package);

        let errors = scan_for_errors(&package, &symlink_resolver, &system_deps);
        assert_eq!(errors.len(), 1);
        assert_error_matches(&errors[0], "libm.so.6", &["/usr/lib/libm.so.6"]);
    }

    #[test]
    fn test_multiple_paths_for_same_dependency() {
        let package = create_test_package(vec![
            ("/usr/lib/libm.so.6", PackageFile::File),
            ("/usr/lib/x86_64-linux-gnu/libm.so.6", PackageFile::File),
            ("/opt/lib/libm.so.6", PackageFile::File),
        ]);
        let system_deps = create_system_dependencies(&["libm.so.6"]);
        let symlink_resolver = SymlinkResolver::new(&package);

        let errors = scan_for_errors(&package, &symlink_resolver, &system_deps);
        assert_eq!(errors.len(), 1);
        assert_error_matches(
            &errors[0],
            "libm.so.6",
            &[
                "/usr/lib/libm.so.6",
                "/usr/lib/x86_64-linux-gnu/libm.so.6",
                "/opt/lib/libm.so.6",
            ],
        );
    }

    #[test]
    fn test_multiple_different_system_dependencies() {
        let package = create_test_package(vec![
            ("/usr/lib/libm.so.6", PackageFile::File),
            ("/usr/lib/libc.so.6", PackageFile::File),
            ("/usr/lib/libpthread.so.0", PackageFile::File),
            ("/usr/bin/myapp", PackageFile::File),
        ]);
        let system_deps =
            create_system_dependencies(&["libm.so.6", "libc.so.6", "libpthread.so.0"]);
        let symlink_resolver = SymlinkResolver::new(&package);

        let errors = scan_for_errors(&package, &symlink_resolver, &system_deps);
        assert_eq!(errors.len(), 3);

        let error_deps = get_error_dependencies(&errors);
        assert!(error_deps.contains(&"libm.so.6"));
        assert!(error_deps.contains(&"libc.so.6"));
        assert!(error_deps.contains(&"libpthread.so.0"));
    }

    #[test]
    fn test_filename_matching_exact_only() {
        let package = create_test_package(vec![
            ("/usr/lib/libm.so", PackageFile::File),
            ("/usr/lib/libm.so.6", PackageFile::File),
            ("/usr/lib/libm.so.6.0", PackageFile::File),
        ]);
        // Only libm.so.6 is a system dependency
        let system_deps = create_system_dependencies(&["libm.so.6"]);
        let symlink_resolver = SymlinkResolver::new(&package);

        let errors = scan_for_errors(&package, &symlink_resolver, &system_deps);
        assert_eq!(errors.len(), 1);
        assert_error_matches(&errors[0], "libm.so.6", &["/usr/lib/libm.so.6"]);
    }

    #[test]
    fn test_files_in_different_directories_same_filename() {
        let package = create_test_package(vec![
            ("/usr/lib/libm.so.6", PackageFile::File),
            ("/usr/lib/x86_64-linux-gnu/libm.so.6", PackageFile::File),
            ("/opt/custom/libm.so.6", PackageFile::File),
        ]);
        let system_deps = create_system_dependencies(&["libm.so.6"]);
        let symlink_resolver = SymlinkResolver::new(&package);

        let errors = scan_for_errors(&package, &symlink_resolver, &system_deps);
        assert_eq!(errors.len(), 1);
        assert_error_matches(
            &errors[0],
            "libm.so.6",
            &[
                "/usr/lib/libm.so.6",
                "/usr/lib/x86_64-linux-gnu/libm.so.6",
                "/opt/custom/libm.so.6",
            ],
        );
    }

    #[test]
    fn test_empty_system_dependencies() {
        let package = create_test_package(vec![
            ("/usr/lib/libm.so.6", PackageFile::File),
            ("/usr/lib/libc.so.6", PackageFile::File),
        ]);
        let system_deps = SystemDependencies::empty();
        let symlink_resolver = SymlinkResolver::new(&package);

        let errors = scan_for_errors(&package, &symlink_resolver, &system_deps);
        assert!(errors.is_empty());
    }

    #[test]
    fn test_error_message_formatting() {
        let package = create_test_package(vec![
            ("/usr/lib/libm.so.6", PackageFile::File),
            ("/opt/lib/libm.so.6", PackageFile::File),
        ]);
        let system_deps = create_system_dependencies(&["libm.so.6"]);
        let symlink_resolver = SymlinkResolver::new(&package);

        let errors = scan_for_errors(&package, &symlink_resolver, &system_deps);
        assert_eq!(errors.len(), 1);

        let error_msg = format!("{}", errors[0]);
        assert!(error_msg.contains("libm.so.6"));
        assert!(error_msg.contains("/usr/lib/libm.so.6"));
        assert!(error_msg.contains("/opt/lib/libm.so.6"));
        assert!(error_msg.contains("Found in package"));
    }

    #[test]
    fn test_only_filename_matters_not_path() {
        let package = create_test_package(vec![
            ("/usr/bin/libm.so.6", PackageFile::File),
            ("/etc/libm.so.6", PackageFile::File),
            ("/tmp/libm.so.6", PackageFile::File),
        ]);
        let system_deps = create_system_dependencies(&["libm.so.6"]);
        let symlink_resolver = SymlinkResolver::new(&package);

        let errors = scan_for_errors(&package, &symlink_resolver, &system_deps);
        assert_eq!(errors.len(), 1);
        assert_error_matches(
            &errors[0],
            "libm.so.6",
            &["/usr/bin/libm.so.6", "/etc/libm.so.6", "/tmp/libm.so.6"],
        );
    }

    #[test]
    fn test_symlink_pointing_outside_package_no_error() {
        // Symlink pointing to a path not in the package should NOT generate an error
        let package = create_test_package(vec![(
            "/usr/lib/libm.so.6",
            PackageFile::Symlink(PathBuf::from("/lib/x86_64-linux-gnu/libm.so.6")),
        )]);
        let system_deps = create_system_dependencies(&["libm.so.6"]);
        let symlink_resolver = SymlinkResolver::new(&package);

        let errors = scan_for_errors(&package, &symlink_resolver, &system_deps);
        // Should be empty because symlink points outside the package
        assert!(errors.is_empty());
    }

    #[test]
    fn test_symlink_pointing_inside_package_generates_error() {
        // Symlink pointing to a file inside the package SHOULD generate an error
        let package = create_test_package(vec![
            ("/usr/lib/libm.so.6.actual", PackageFile::File),
            (
                "/usr/lib/libm.so.6",
                PackageFile::Symlink(PathBuf::from("/usr/lib/libm.so.6.actual")),
            ),
        ]);
        let system_deps = create_system_dependencies(&["libm.so.6"]);
        let symlink_resolver = SymlinkResolver::new(&package);

        let errors = scan_for_errors(&package, &symlink_resolver, &system_deps);
        assert_eq!(errors.len(), 1);
        assert_error_matches(&errors[0], "libm.so.6", &["/usr/lib/libm.so.6"]);
    }

    #[test]
    fn test_mixed_regular_file_and_symlink_outside() {
        // Regular file should generate error, symlink pointing outside should not
        let package = create_test_package(vec![
            ("/usr/lib/libm.so.6", PackageFile::File),
            (
                "/usr/lib/libc.so.6",
                PackageFile::Symlink(PathBuf::from("/lib/x86_64-linux-gnu/libc.so.6")),
            ),
        ]);
        let system_deps = create_system_dependencies(&["libm.so.6", "libc.so.6"]);
        let symlink_resolver = SymlinkResolver::new(&package);

        let errors = scan_for_errors(&package, &symlink_resolver, &system_deps);
        // Only libm.so.6 (regular file) should generate error
        assert_eq!(errors.len(), 1);
        assert_error_matches(&errors[0], "libm.so.6", &["/usr/lib/libm.so.6"]);
    }

    #[test]
    fn test_mixed_regular_file_and_symlink_inside() {
        // Both regular file and symlink pointing inside should generate errors
        let package = create_test_package(vec![
            ("/usr/lib/libm.so.6", PackageFile::File),
            ("/usr/lib/libc.so.6.actual", PackageFile::File),
            (
                "/usr/lib/libc.so.6",
                PackageFile::Symlink(PathBuf::from("/usr/lib/libc.so.6.actual")),
            ),
        ]);
        let system_deps = create_system_dependencies(&["libm.so.6", "libc.so.6"]);
        let symlink_resolver = SymlinkResolver::new(&package);

        let errors = scan_for_errors(&package, &symlink_resolver, &system_deps);
        assert_eq!(errors.len(), 2);

        let error_deps = get_error_dependencies(&errors);
        assert!(error_deps.contains(&"libm.so.6"));
        assert!(error_deps.contains(&"libc.so.6"));
    }

    #[test]
    fn test_symlink_chain_pointing_inside() {
        // Symlink chain A -> B -> file, where file is in package, should generate error
        let package = create_test_package(vec![
            ("/usr/lib/libm.so.6.actual", PackageFile::File),
            (
                "/usr/lib/libm.so.6.intermediate",
                PackageFile::Symlink(PathBuf::from("/usr/lib/libm.so.6.actual")),
            ),
            (
                "/usr/lib/libm.so.6",
                PackageFile::Symlink(PathBuf::from("/usr/lib/libm.so.6.intermediate")),
            ),
        ]);
        let system_deps = create_system_dependencies(&["libm.so.6"]);
        let symlink_resolver = SymlinkResolver::new(&package);

        let errors = scan_for_errors(&package, &symlink_resolver, &system_deps);
        // The symlink chain resolves to a file inside the package, so it should generate an error
        assert_eq!(errors.len(), 1);
        assert_error_matches(&errors[0], "libm.so.6", &["/usr/lib/libm.so.6"]);
    }

    #[test]
    fn test_symlink_chain_pointing_outside() {
        // Symlink chain A -> B -> file, where file is NOT in package, should NOT generate error
        let package = create_test_package(vec![
            (
                "/usr/lib/libm.so.6.intermediate",
                PackageFile::Symlink(PathBuf::from("/lib/x86_64-linux-gnu/libm.so.6")),
            ),
            (
                "/usr/lib/libm.so.6",
                PackageFile::Symlink(PathBuf::from("/usr/lib/libm.so.6.intermediate")),
            ),
        ]);
        let system_deps = create_system_dependencies(&["libm.so.6"]);
        let symlink_resolver = SymlinkResolver::new(&package);

        let errors = scan_for_errors(&package, &symlink_resolver, &system_deps);
        // The symlink chain resolves to a file outside the package, so it should NOT generate an error
        assert!(errors.is_empty());
    }
}
