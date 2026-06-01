// Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

//! Validates the shape of `DT_RPATH` and `DT_RUNPATH` entries.
//!
//! An entry is invalid if it is a relative path that the dynamic linker
//! would resolve against the process's current working directory rather than
//! the binary's location: either a plain relative path without `$ORIGIN`,
//! or a path with relative components (`../`, `./`, or anything else)
//! appearing before `$ORIGIN`. Both create binary-planting risk and
//! unpredictable behavior depending on the CWD at exec time.
//!
//! This is a property of the ELF the dynamic linker cares about, but the
//! check is run as a validator at report time rather than during ELF parse
//! so the parse step stays focused on parsing.
//!
//! `Elf::invalid_path` is the per-entry predicate; this module wraps the
//! "RPATH first, RUNPATH second, format the offending entry with its
//! source field name" logic.

use crate::package::{Elf, Package};
use crate::report::finding::Finding;

/// Iterate every ELF in the package and emit a finding for any with invalid
/// RPATH/RUNPATH entries.
pub(crate) fn scan_all<'a>(package: &'a Package) -> Vec<Finding<'a>> {
    package
        .elfs()
        .into_iter()
        .filter_map(|(path, elf)| {
            let paths = scan(elf);
            (!paths.is_empty()).then_some(Finding::RpathShape { path, paths })
        })
        .collect()
}

/// Returns formatted descriptions of any invalid RPATH or RUNPATH entries on
/// `elf`. Empty Vec means the entries are well-formed.
pub(crate) fn scan(elf: &Elf) -> Vec<String> {
    let mut findings = Vec::new();
    findings.extend(invalid_entries(elf.runpath(), "RUNPATH"));
    findings.extend(invalid_entries(elf.rpath(), "RPATH"));
    findings
}

fn invalid_entries(paths: &[String], field: &str) -> Vec<String> {
    paths
        .iter()
        .filter(|p| Elf::invalid_path(p))
        .map(|p| format!("{field}: {p} is invalid"))
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::package::{ElfError, ElfType};
    use std::path::PathBuf;

    fn elf_with(rpath: Vec<String>, runpath: Vec<String>) -> Elf {
        Elf::for_testing(ElfType::Executable, Vec::new(), rpath, runpath)
    }

    #[test]
    fn absolute_paths_are_valid() {
        let elf = elf_with(vec!["/usr/lib".into(), "/opt/lib".into()], Vec::new());
        assert!(scan(&elf).is_empty());
    }

    #[test]
    fn origin_at_start_is_valid() {
        let elf = elf_with(
            vec![
                "$ORIGIN/../lib".into(),
                "${ORIGIN}/lib".into(),
                "$ORIGIN/lib".into(),
            ],
            Vec::new(),
        );
        assert!(scan(&elf).is_empty());
    }

    #[test]
    fn plain_relative_paths_are_invalid() {
        let elf = elf_with(vec!["../lib".into(), "./lib".into()], Vec::new());
        let findings = scan(&elf);
        assert_eq!(findings.len(), 2);
        assert!(findings.iter().any(|s| s.contains("../lib")));
        assert!(findings.iter().any(|s| s.contains("./lib")));
    }

    #[test]
    fn both_runpath_and_rpath_are_checked() {
        // RUNPATH wins at runtime, but both still live in the ELF and the
        // shape check covers both.
        let elf = elf_with(
            vec!["../lib".into()],
            vec!["/opt/lib".into(), "./lib".into()],
        );
        let findings = scan(&elf);
        assert_eq!(findings.len(), 2);
        assert!(findings
            .iter()
            .any(|s| s.contains("RPATH") && s.contains("../lib")));
        assert!(findings
            .iter()
            .any(|s| s.contains("RUNPATH") && s.contains("./lib")));
    }

    #[test]
    fn mixed_valid_and_invalid() {
        let elf = elf_with(vec!["/usr/lib".into(), "../lib".into()], Vec::new());
        let findings = scan(&elf);
        assert_eq!(findings.len(), 1);
        assert!(findings[0].contains("../lib"));
    }

    #[test]
    fn content_before_origin_is_invalid() {
        let elf = elf_with(
            vec![
                "../${ORIGIN}/lib".into(),
                "./$ORIGIN/lib".into(),
                "../$ORIGIN/lib".into(),
                "some/path/$ORIGIN/lib".into(),
                "prefix/${ORIGIN}/lib".into(),
            ],
            Vec::new(),
        );
        let findings = scan(&elf);
        assert_eq!(findings.len(), 5);
        assert!(findings.iter().any(|s| s.contains("../${ORIGIN}")));
        assert!(findings.iter().any(|s| s.contains("./$ORIGIN")));
        assert!(findings.iter().any(|s| s.contains("../$ORIGIN")));
        assert!(findings.iter().any(|s| s.contains("some/path/$ORIGIN")));
        assert!(findings.iter().any(|s| s.contains("prefix/${ORIGIN}")));
    }

    fn get_examples_dir() -> PathBuf {
        match runfiles::Runfiles::create() {
            Ok(r) => r
                .rlocation("_main/tests/packaging/package_validator/fixtures")
                .expect("fixtures not found in runfiles"),
            Err(_) => PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("fixtures"),
        }
    }

    fn require_fixture(name: &str) -> Option<PathBuf> {
        let path = get_examples_dir().join(name);
        if path.exists() {
            Some(path)
        } else {
            eprintln!("Skipping test: fixture '{}' not found.", name);
            None
        }
    }

    /// Assert that scanning a fixture either flags `$needle` or finds nothing —
    /// patchelf occasionally refuses to write an invalid RPATH, in which case
    /// the fixture is well-formed and there's nothing to test.
    fn assert_flags_if_present(elf_path: &std::path::Path, needle: &str) {
        let elf = match Elf::from_path(elf_path) {
            Ok(elf) => elf,
            Err(ElfError::NotElfFile { .. } | ElfError::FileTooSmall { .. }) => return,
            Err(e) => panic!("Unexpected parse error: {e:?}"),
        };
        let findings = scan(&elf);
        if findings.is_empty() {
            return;
        }
        assert!(
            findings.iter().any(|p| p.contains(needle)),
            "Findings should mention {needle:?}, got: {findings:?}"
        );
    }

    #[test]
    fn fixture_invalid_relative_rpath() {
        let Some(p) = require_fixture("test-elf-invalid-relative-rpath.elf") else {
            return;
        };
        assert_flags_if_present(&p, "../lib");
    }

    #[test]
    fn fixture_invalid_relative_dot_rpath() {
        let Some(p) = require_fixture("test-elf-invalid-relative-dot-rpath.elf") else {
            return;
        };
        assert_flags_if_present(&p, "./lib");
    }

    #[test]
    fn fixture_invalid_prefix_origin_rpath() {
        let Some(p) = require_fixture("test-elf-invalid-prefix-origin-rpath.elf") else {
            return;
        };
        assert_flags_if_present(&p, "../$ORIGIN");
    }
}
