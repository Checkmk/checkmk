// Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

//! Flags any file in the package whose name matches a declared system
//! dependency. The premise: if a name is on the system-deps list, the target
//! host is expected to provide it; bundling a copy in the package means either
//! the list is wrong or the package is shipping something it shouldn't.
//!
//! Symlinks pointing outside the package are excluded — they only *reference*
//! the system file rather than ship a copy.

use std::collections::HashMap;
use std::path::Path;

use crate::inputs::system_dependencies::SystemDependencies;
use crate::package::Package;
use crate::report::finding::Finding;
use crate::resolution::symlinks::{SymlinkResolutionResult, SymlinkResolver};

pub(crate) fn scan_all<'a>(
    package: &'a Package,
    symlink_resolver: &SymlinkResolver<'a>,
    system_dependencies: &'a SystemDependencies,
) -> Vec<Finding<'a>> {
    package
        .files()
        .iter()
        .filter_map(|(path, _)| {
            path.file_name()
                .and_then(|f| f.to_str())
                .filter(|name| system_dependencies.contains(name))
                .filter(|_| {
                    symlink_resolver
                        .resolve(path.as_path())
                        .is_none_or(|result| {
                            !matches!(result, SymlinkResolutionResult::NotFound(_))
                        })
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
        .map(|(name, paths)| Finding::SystemDependencyFoundInPackage {
            dependency: name,
            paths,
        })
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::package::{Package, PackageFile, PackageFiles};
    use std::io::Write;
    use std::path::PathBuf;
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

    fn assert_error_matches(error: &Finding, expected_dependency: &str, expected_paths: &[&str]) {
        match error {
            Finding::SystemDependencyFoundInPackage { dependency, paths } => {
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
            other => panic!("Expected SystemDependencyFoundInPackage, got {:?}", other),
        }
    }

    fn dependency_names<'a>(errors: &'a [Finding<'a>]) -> Vec<&'a str> {
        errors
            .iter()
            .filter_map(|e| match e {
                Finding::SystemDependencyFoundInPackage { dependency, .. } => Some(*dependency),
                _ => None,
            })
            .collect()
    }

    fn scan<'a>(package: &'a Package, system_deps: &'a SystemDependencies) -> Vec<Finding<'a>> {
        let symlink_resolver = SymlinkResolver::new(package);
        scan_all(package, &symlink_resolver, system_deps)
    }

    #[test]
    fn no_errors_when_no_system_dependencies_match() {
        let package = create_test_package(vec![
            ("/usr/bin/myapp", PackageFile::File),
            ("/usr/lib/myapp.so", PackageFile::File),
        ]);
        let deps = create_system_dependencies(&["libm.so", "libc.so"]);
        assert!(scan(&package, &deps).is_empty());
    }

    #[test]
    fn error_detected_for_single_system_dependency() {
        let package = create_test_package(vec![
            ("/usr/bin/myapp", PackageFile::File),
            ("/usr/lib/libm.so.6", PackageFile::File),
        ]);
        let deps = create_system_dependencies(&["libm.so"]);
        let errors = scan(&package, &deps);
        assert_eq!(errors.len(), 1);
        assert_error_matches(&errors[0], "libm.so.6", &["/usr/lib/libm.so.6"]);
    }

    #[test]
    fn multiple_paths_for_same_dependency() {
        let package = create_test_package(vec![
            ("/usr/lib/libm.so.6", PackageFile::File),
            ("/usr/lib/x86_64-linux-gnu/libm.so.6", PackageFile::File),
            ("/opt/lib/libm.so.6", PackageFile::File),
        ]);
        let deps = create_system_dependencies(&["libm.so"]);
        let errors = scan(&package, &deps);
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
    fn multiple_different_system_dependencies() {
        let package = create_test_package(vec![
            ("/usr/lib/libm.so.6", PackageFile::File),
            ("/usr/lib/libc.so.6", PackageFile::File),
            ("/usr/lib/libpthread.so.0", PackageFile::File),
            ("/usr/bin/myapp", PackageFile::File),
        ]);
        let deps = create_system_dependencies(&["libm.so", "libc.so", "libpthread.so"]);
        let errors = scan(&package, &deps);
        assert_eq!(errors.len(), 3);
        let names = dependency_names(&errors);
        assert!(names.contains(&"libm.so.6"));
        assert!(names.contains(&"libc.so.6"));
        assert!(names.contains(&"libpthread.so.0"));
    }

    #[test]
    fn versioned_so_names_match_base() {
        let package = create_test_package(vec![
            ("/usr/lib/libm.so", PackageFile::File),
            ("/usr/lib/libm.so.6", PackageFile::File),
            ("/usr/lib/libm.so.6.0", PackageFile::File),
        ]);
        let deps = create_system_dependencies(&["libm.so"]);
        let errors = scan(&package, &deps);
        assert_eq!(errors.len(), 3);
        let names = dependency_names(&errors);
        assert!(names.contains(&"libm.so"));
        assert!(names.contains(&"libm.so.6"));
        assert!(names.contains(&"libm.so.6.0"));
    }

    #[test]
    fn empty_system_dependency_list_produces_no_errors() {
        let package = create_test_package(vec![
            ("/usr/lib/libm.so.6", PackageFile::File),
            ("/usr/lib/libc.so.6", PackageFile::File),
        ]);
        assert!(scan(&package, &SystemDependencies::empty()).is_empty());
    }

    #[test]
    fn finding_lists_all_paths() {
        let package = create_test_package(vec![
            ("/usr/lib/libm.so.6", PackageFile::File),
            ("/opt/lib/libm.so.6", PackageFile::File),
        ]);
        let deps = create_system_dependencies(&["libm.so"]);
        let errors = scan(&package, &deps);
        assert_eq!(errors.len(), 1);
        assert_error_matches(
            &errors[0],
            "libm.so.6",
            &["/usr/lib/libm.so.6", "/opt/lib/libm.so.6"],
        );
    }

    #[test]
    fn symlink_pointing_outside_package_is_not_flagged() {
        let package = create_test_package(vec![(
            "/usr/lib/libm.so.6",
            PackageFile::Symlink(PathBuf::from("/lib/x86_64-linux-gnu/libm.so.6")),
        )]);
        let deps = create_system_dependencies(&["libm.so"]);
        assert!(scan(&package, &deps).is_empty());
    }

    #[test]
    fn symlink_pointing_inside_package_is_flagged() {
        // Use a non-.so target name so it doesn't also match the system-dep list.
        let package = create_test_package(vec![
            ("/usr/lib/libm-actual", PackageFile::File),
            (
                "/usr/lib/libm.so.6",
                PackageFile::Symlink(PathBuf::from("/usr/lib/libm-actual")),
            ),
        ]);
        let deps = create_system_dependencies(&["libm.so"]);
        let errors = scan(&package, &deps);
        assert_eq!(errors.len(), 1);
        assert_error_matches(&errors[0], "libm.so.6", &["/usr/lib/libm.so.6"]);
    }

    #[test]
    fn symlink_chain_inside_package_is_flagged() {
        let package = create_test_package(vec![
            ("/usr/lib/libm-actual", PackageFile::File),
            (
                "/usr/lib/libm-intermediate",
                PackageFile::Symlink(PathBuf::from("/usr/lib/libm-actual")),
            ),
            (
                "/usr/lib/libm.so.6",
                PackageFile::Symlink(PathBuf::from("/usr/lib/libm-intermediate")),
            ),
        ]);
        let deps = create_system_dependencies(&["libm.so"]);
        let errors = scan(&package, &deps);
        assert_eq!(errors.len(), 1);
        assert_error_matches(&errors[0], "libm.so.6", &["/usr/lib/libm.so.6"]);
    }

    #[test]
    fn symlink_chain_outside_package_is_not_flagged() {
        let package = create_test_package(vec![
            (
                "/usr/lib/libm-intermediate",
                PackageFile::Symlink(PathBuf::from("/lib/x86_64-linux-gnu/libm.so.6")),
            ),
            (
                "/usr/lib/libm.so.6",
                PackageFile::Symlink(PathBuf::from("/usr/lib/libm-intermediate")),
            ),
        ]);
        let deps = create_system_dependencies(&["libm.so"]);
        assert!(scan(&package, &deps).is_empty());
    }
}
