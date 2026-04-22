// Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

//! Resolves symlinks within packages, handling cycles and external targets.

use std::collections::{HashMap, HashSet};
use std::path::{Path, PathBuf};

use crate::package::{Package, PackageFiles, PackageSymlinks};

pub(crate) type SymlinkResolutionResults<'a> = HashMap<&'a Path, SymlinkResolutionResult<'a>>;

pub(crate) enum SymlinkResolutionResult<'a> {
    NotFound(PathBuf), // The symlink was not found in the package, likely a system dependency.
    Found(&'a Path),   // The symlink was found in the package.
    CycleDetected(),   // The symlink points to itself or a cycle was detected.
}

pub(crate) struct SymlinkResolver<'a> {
    symlinks: SymlinkResolutionResults<'a>,
}

impl<'a> SymlinkResolver<'a> {
    pub(crate) fn new(package: &'a Package) -> Self {
        let files = package.files();
        let symlinks = package.symlinks();
        Self {
            symlinks: Self::resolve_symlinks(files, &symlinks),
        }
    }

    pub(crate) fn resolve(&'a self, path: &Path) -> Option<&'a SymlinkResolutionResult<'a>> {
        self.symlinks.get(path)
    }

    fn resolve_symlinks(
        files: &'a PackageFiles,
        symlinks: &PackageSymlinks<'a>,
    ) -> SymlinkResolutionResults<'a> {
        symlinks
            .iter()
            .map(|(symlink_path, target_path)| {
                let mut visited = HashSet::<&'a Path>::new();
                let result = Self::resolve_single_symlink(
                    symlink_path,
                    target_path,
                    files,
                    symlinks,
                    &mut visited,
                );
                (*symlink_path, result)
            })
            .collect()
    }

    fn resolve_single_symlink(
        current_path: &'a Path,
        target_path: &'a Path,
        files: &'a PackageFiles,
        symlinks: &PackageSymlinks<'a>,
        visited: &mut HashSet<&'a Path>,
    ) -> SymlinkResolutionResult<'a> {
        if visited.contains(current_path) {
            return SymlinkResolutionResult::CycleDetected();
        }
        visited.insert(current_path);

        if !files.contains_key(target_path) {
            // Target not found in package, likely a system dependency
            SymlinkResolutionResult::NotFound(target_path.to_path_buf())
        } else if let Some(next_target) = symlinks.get(target_path) {
            // Target is a symlink, recursively resolve
            Self::resolve_single_symlink(target_path, next_target, files, symlinks, visited)
        } else {
            // Target is not a symlink, we've found the final target
            SymlinkResolutionResult::Found(target_path)
        }
    }

    #[cfg(test)]
    fn symlinks(&self) -> &SymlinkResolutionResults<'a> {
        &self.symlinks
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::package::{Package, PackageFile};
    use std::collections::HashMap;
    use std::path::PathBuf;

    fn create_test_package(files: HashMap<PathBuf, PackageFile>) -> Package {
        Package::new_for_testing(PathBuf::from("/test/package.deb"), files)
    }

    #[test]
    fn test_simple_symlink_resolution() {
        // A -> /usr/bin/file
        let mut files = HashMap::new();
        let file_path = PathBuf::from("/usr/bin/file");
        let symlink_path = PathBuf::from("/usr/bin/A");
        files.insert(file_path.clone(), PackageFile::File);
        files.insert(
            symlink_path.clone(),
            PackageFile::Symlink(file_path.clone()),
        );

        let package = create_test_package(files);
        let resolver = SymlinkResolver::new(&package);
        let results = resolver.symlinks();

        assert_eq!(results.len(), 1);
        match results.get(symlink_path.as_path()) {
            Some(SymlinkResolutionResult::Found(target)) => {
                assert_eq!(*target, file_path.as_path());
            }
            _ => panic!("Expected Found result"),
        }
    }

    #[test]
    fn test_chained_symlinks() {
        // A -> B -> file
        let mut files = HashMap::new();
        let file_path = PathBuf::from("/usr/bin/file");
        let symlink_b_path = PathBuf::from("/usr/bin/B");
        let symlink_a_path = PathBuf::from("/usr/bin/A");

        files.insert(file_path.clone(), PackageFile::File);
        files.insert(
            symlink_b_path.clone(),
            PackageFile::Symlink(file_path.clone()),
        );
        files.insert(
            symlink_a_path.clone(),
            PackageFile::Symlink(symlink_b_path.clone()),
        );

        let package = create_test_package(files);
        let resolver = SymlinkResolver::new(&package);
        let results = resolver.symlinks();

        assert_eq!(results.len(), 2);
        // Check that A resolves to file
        match results.get(symlink_a_path.as_path()) {
            Some(SymlinkResolutionResult::Found(target)) => {
                assert_eq!(*target, file_path.as_path());
            }
            _ => panic!("Expected Found result for A"),
        }
        // Check that B resolves to file
        match results.get(symlink_b_path.as_path()) {
            Some(SymlinkResolutionResult::Found(target)) => {
                assert_eq!(*target, file_path.as_path());
            }
            _ => panic!("Expected Found result for B"),
        }
    }

    #[test]
    fn test_cycle_detection_self_reference() {
        // A -> A (self-reference)
        let mut files = HashMap::new();
        let symlink_path = PathBuf::from("/usr/bin/A");
        files.insert(
            symlink_path.clone(),
            PackageFile::Symlink(symlink_path.clone()),
        );

        let package = create_test_package(files);
        let resolver = SymlinkResolver::new(&package);
        let results = resolver.symlinks();

        assert_eq!(results.len(), 1);
        match results.get(symlink_path.as_path()) {
            Some(SymlinkResolutionResult::CycleDetected()) => {}
            _ => panic!("Expected CycleDetected result"),
        }
    }

    #[test]
    fn test_cycle_detection_multi_symlink() {
        // A -> B -> A (cycle)
        let mut files = HashMap::new();
        let symlink_a_path = PathBuf::from("/usr/bin/A");
        let symlink_b_path = PathBuf::from("/usr/bin/B");

        files.insert(
            symlink_a_path.clone(),
            PackageFile::Symlink(symlink_b_path.clone()),
        );
        files.insert(
            symlink_b_path.clone(),
            PackageFile::Symlink(symlink_a_path.clone()),
        );

        let package = create_test_package(files);
        let resolver = SymlinkResolver::new(&package);
        let results = resolver.symlinks();

        assert_eq!(results.len(), 2);
        // Both should detect cycles
        match results.get(symlink_a_path.as_path()) {
            Some(SymlinkResolutionResult::CycleDetected()) => {}
            _ => panic!("Expected CycleDetected result for A"),
        }
        match results.get(symlink_b_path.as_path()) {
            Some(SymlinkResolutionResult::CycleDetected()) => {}
            _ => panic!("Expected CycleDetected result for B"),
        }
    }

    #[test]
    fn test_not_found() {
        // Symlink pointing to /usr/lib/missing.so (not in package)
        let mut files = HashMap::new();
        let symlink_path = PathBuf::from("/usr/bin/A");
        let missing_target = PathBuf::from("/usr/lib/missing.so");

        files.insert(
            symlink_path.clone(),
            PackageFile::Symlink(missing_target.clone()),
        );

        let package = create_test_package(files);
        let resolver = SymlinkResolver::new(&package);
        let results = resolver.symlinks();

        assert_eq!(results.len(), 1);
        match results.get(symlink_path.as_path()) {
            Some(SymlinkResolutionResult::NotFound(target)) => {
                assert_eq!(target, &missing_target);
            }
            _ => panic!("Expected NotFound result"),
        }
    }

    #[test]
    fn test_multiple_symlinks() {
        // Multiple independent symlinks
        let mut files = HashMap::new();
        let file1_path = PathBuf::from("/usr/bin/file1");
        let file2_path = PathBuf::from("/usr/bin/file2");
        let symlink1_path = PathBuf::from("/usr/bin/symlink1");
        let symlink2_path = PathBuf::from("/usr/bin/symlink2");
        let missing_target = PathBuf::from("/usr/lib/missing.so");

        files.insert(file1_path.clone(), PackageFile::File);
        files.insert(file2_path.clone(), PackageFile::File);
        files.insert(
            symlink1_path.clone(),
            PackageFile::Symlink(file1_path.clone()),
        );
        files.insert(
            symlink2_path.clone(),
            PackageFile::Symlink(missing_target.clone()),
        );

        let package = create_test_package(files);
        let resolver = SymlinkResolver::new(&package);
        let results = resolver.symlinks();

        assert_eq!(results.len(), 2);
        // Check symlink1 resolves to file1
        match results.get(symlink1_path.as_path()) {
            Some(SymlinkResolutionResult::Found(target)) => {
                assert_eq!(*target, file1_path.as_path());
            }
            _ => panic!("Expected Found result for symlink1"),
        }
        // Check symlink2 is not found
        match results.get(symlink2_path.as_path()) {
            Some(SymlinkResolutionResult::NotFound(target)) => {
                assert_eq!(target, &missing_target);
            }
            _ => panic!("Expected NotFound result for symlink2"),
        }
    }

    #[test]
    fn test_edge_case_empty_package() {
        // Empty package (no files, no symlinks)
        let files = HashMap::new();
        let package = create_test_package(files);
        let resolver = SymlinkResolver::new(&package);
        let results = resolver.symlinks();

        assert_eq!(results.len(), 0);
    }

    #[test]
    fn test_edge_case_no_symlinks() {
        // Package with files but no symlinks
        let mut files = HashMap::new();
        files.insert(PathBuf::from("/usr/bin/file1"), PackageFile::File);
        files.insert(PathBuf::from("/usr/bin/file2"), PackageFile::File);

        let package = create_test_package(files);
        let resolver = SymlinkResolver::new(&package);
        let results = resolver.symlinks();

        assert_eq!(results.len(), 0);
    }

    #[test]
    fn test_edge_case_symlink_to_missing_symlink() {
        // Symlink A -> Symlink B -> missing file
        let mut files = HashMap::new();
        let symlink_a_path = PathBuf::from("/usr/bin/A");
        let symlink_b_path = PathBuf::from("/usr/bin/B");
        let missing_target = PathBuf::from("/usr/lib/missing.so");

        files.insert(
            symlink_a_path.clone(),
            PackageFile::Symlink(symlink_b_path.clone()),
        );
        files.insert(
            symlink_b_path.clone(),
            PackageFile::Symlink(missing_target.clone()),
        );

        let package = create_test_package(files);
        let resolver = SymlinkResolver::new(&package);
        let results = resolver.symlinks();

        assert_eq!(results.len(), 2);
        // Both should result in NotFound since the chain ends in a missing file
        match results.get(symlink_a_path.as_path()) {
            Some(SymlinkResolutionResult::NotFound(target)) => {
                assert_eq!(target, &missing_target);
            }
            _ => panic!("Expected NotFound result for A"),
        }
        match results.get(symlink_b_path.as_path()) {
            Some(SymlinkResolutionResult::NotFound(target)) => {
                assert_eq!(target, &missing_target);
            }
            _ => panic!("Expected NotFound result for B"),
        }
    }
}
