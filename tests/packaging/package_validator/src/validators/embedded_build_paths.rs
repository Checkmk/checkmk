// Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

//! Flags ELF binaries that leak the build host's directory layout
//! (`/.cache/bazel/`, `/home/jenkins`) in their `.rodata`. This is a
//! build-hygiene check, not an ELF correctness check — the binary loads and
//! runs fine, it just exposes the build sandbox layout.
//!
//! Detection needs the raw `.rodata` bytes, so this validator reads the
//! extracted file from disk via `Package::extracted_path`. That works because
//! `Package` keeps the extraction directory alive for its whole lifetime.

use goblin::elf::Elf as GoblinElf;
use std::fs;
use std::path::Path;

use crate::package::Package;
use crate::report::finding::Finding;

const MARKERS: &[&[u8]] = &[b"/.cache/bazel/", b"/home/jenkins"];

/// Emit a finding for every ELF whose `.rodata` leaks build-host paths.
pub(crate) fn scan_all<'a>(package: &'a Package) -> Vec<Finding<'a>> {
    package
        .elfs()
        .into_iter()
        .filter_map(|(path, _elf)| {
            let on_disk = package.extracted_path(path)?;
            let strings = scan(&on_disk);
            (!strings.is_empty()).then_some(Finding::EmbeddedBuildPaths { path, strings })
        })
        .collect()
}

/// Scan the `.rodata` of the ELF at `path` for null-terminated strings
/// containing the build-host marker. Operates on raw bytes since `.rodata` is
/// arbitrary binary data, not guaranteed UTF-8, and the marker is ASCII and
/// cannot span a null byte.
///
/// The file is an already-extracted ELF, so a read/parse failure here is
/// unexpected; warn rather than silently returning nothing (a silent empty
/// return is exactly what hid an earlier regression).
fn scan(path: &Path) -> Vec<String> {
    let bytes = match fs::read(path) {
        Ok(bytes) => bytes,
        Err(e) => {
            eprintln!(
                "WARNING: could not read extracted ELF {} for build-path scan: {e}",
                path.display()
            );
            return Vec::new();
        }
    };
    let elf = match GoblinElf::parse(&bytes) {
        Ok(elf) => elf,
        Err(e) => {
            eprintln!(
                "WARNING: could not parse extracted ELF {} for build-path scan: {e}",
                path.display()
            );
            return Vec::new();
        }
    };
    elf.section_headers
        .iter()
        .filter_map(|section| {
            let name = elf.shdr_strtab.get_at(section.sh_name)?;
            let range = section.file_range()?;
            (name == ".rodata" && range.end <= bytes.len()).then_some(&bytes[range])
        })
        .flat_map(|section_bytes| {
            section_bytes
                .split(|&b| b == 0)
                .filter(|cstring| {
                    MARKERS
                        .iter()
                        .any(|m| cstring.windows(m.len()).any(|w| w == *m))
                })
                .map(|cstring| String::from_utf8_lossy(cstring).into_owned())
                .collect::<Vec<_>>()
        })
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::package::Package;
    use std::path::PathBuf;
    use std::process::Command;

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

    // Cheap unit coverage of the marker logic: read a fixture ELF directly.
    #[test]
    fn test_clean_elf_has_no_findings() {
        let Some(path) = require_fixture("test-elf-rodata-no-build-paths.elf") else {
            return;
        };
        assert!(
            scan(&path).is_empty(),
            "Clean ELF should produce no findings"
        );
    }

    #[test]
    fn test_tainted_elf_reports_paths() {
        let Some(path) = require_fixture("test-elf-rodata-bazel-paths.elf") else {
            return;
        };
        let findings = scan(&path);
        assert!(
            findings.iter().any(|s| s.contains("/.cache/bazel/")),
            "Tainted ELF should produce a finding referencing the Bazel cache, got: {findings:?}"
        );
    }

    /// End-to-end regression guard: a tainted binary, packaged and run through
    /// the real extract → report path, must still be flagged. This exercises the
    /// property that previously regressed — extracted files must remain readable
    /// after `Package::new` returns. A `.cma` is just a gzipped tar, so we build
    /// one hermetically around the tainted fixture.
    #[test]
    fn test_tainted_binary_flagged_end_to_end() {
        let Some(fixture) = require_fixture("test-elf-rodata-bazel-paths.elf") else {
            return;
        };

        // Stage the fixture as bin/tool inside a directory to be tarred.
        let staging = tempfile::tempdir().expect("create staging dir");
        let bin_dir = staging.path().join("bin");
        fs::create_dir_all(&bin_dir).expect("create bin dir");
        fs::copy(&fixture, bin_dir.join("tool")).expect("copy fixture");

        // Pack it into a .cma (gzipped tar) so the extension dispatches to the
        // CMA extractor. Skip gracefully if `tar` is unavailable.
        let cma = tempfile::Builder::new()
            .suffix(".cma")
            .tempfile()
            .expect("create .cma temp file");
        let status = Command::new("tar")
            .arg("-czf")
            .arg(cma.path())
            .arg("-C")
            .arg(staging.path())
            .arg(".")
            .status();
        match status {
            Ok(s) if s.success() => {}
            Ok(s) => panic!("tar failed: {s}"),
            Err(e) if e.kind() == std::io::ErrorKind::NotFound => {
                eprintln!("Skipping test: `tar` not available.");
                return;
            }
            Err(e) => panic!("failed to run tar: {e}"),
        }

        let package = Package::new(cma.path().to_path_buf()).expect("extract .cma package");
        let findings = scan_all(&package);

        assert!(
            findings.iter().any(|f| matches!(
                f,
                Finding::EmbeddedBuildPaths { strings, .. }
                    if strings.iter().any(|s| s.contains("/.cache/bazel/"))
            )),
            "Packaged tainted binary should be flagged, got: {findings:?}"
        );
    }
}
