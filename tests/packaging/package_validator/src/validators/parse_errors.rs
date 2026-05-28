// Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

//! Emits findings for files the classifier flagged as `UnreadableElf` —
//! files that looked like ELFs but couldn't be parsed (I/O error, goblin
//! parse error, unknown e_type).

use crate::package::{Package, PackageFile};
use crate::report::finding::Finding;

pub(crate) fn scan_all<'a>(package: &'a Package) -> Vec<Finding<'a>> {
    package
        .files()
        .iter()
        .filter_map(|(path, file)| match file {
            PackageFile::UnreadableElf(message) => Some(Finding::UnreadableElf {
                path: path.as_path(),
                message: message.as_str(),
            }),
            _ => None,
        })
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::package::{PackageFile, PackageFiles};
    use std::path::{Path, PathBuf};

    fn make_package(files: Vec<(&str, PackageFile)>) -> Package {
        let pf: PackageFiles = files
            .into_iter()
            .map(|(path, file)| (PathBuf::from(path), file))
            .collect();
        Package::new_for_testing(PathBuf::from("/test/package.deb"), pf)
    }

    #[test]
    fn unreadable_elf_produces_finding() {
        let package = make_package(vec![
            ("/usr/bin/myapp", PackageFile::File),
            (
                "/usr/bin/broken",
                PackageFile::UnreadableElf("parse error".to_string()),
            ),
        ]);
        let errors = scan_all(&package);
        assert_eq!(errors.len(), 1);
        match &errors[0] {
            Finding::UnreadableElf { path, message } => {
                assert_eq!(*path, Path::new("/usr/bin/broken"));
                assert_eq!(*message, "parse error");
            }
            other => panic!("Expected UnreadableElf, got {:?}", other),
        }
    }

    #[test]
    fn package_with_no_unreadable_elfs_emits_nothing() {
        let package = make_package(vec![
            ("/usr/bin/myapp", PackageFile::File),
            (
                "/usr/lib/libfoo.so",
                PackageFile::Symlink(PathBuf::from("/usr/lib/libfoo.so.1")),
            ),
        ]);
        assert!(scan_all(&package).is_empty());
    }
}
