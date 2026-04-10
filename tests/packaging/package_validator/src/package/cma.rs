// Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

//! Implements CMA package extraction using `tar`.

use std::path::Path;
use tempfile::TempDir;

use super::extractor::{
    wait_with_timeout, PackageError, PackageExtractor, PackageResult, DEFAULT_EXTRACTION_TIMEOUT,
};
use super::PackageFiles;

pub(crate) struct CmaExtractor;

impl PackageExtractor for CmaExtractor {
    const EXTENSION: &'static str = "cma";

    /// Extract a CMA package into a temporary directory.
    ///
    /// CMA packages are gzip-compressed tarballs (`.tar.gz`) with a `.cma` extension.
    ///
    /// # Errors
    /// Returns an error if the package cannot be extracted.
    ///
    /// # Timeout
    /// This function enforces a timeout of 3 minutes for the `tar` subprocess.
    /// If extraction takes longer, the process will be killed and a `CommandTimeout`
    /// error will be returned.
    fn extract(package: &Path, dest: &TempDir) -> PackageResult<PackageFiles> {
        let mut child = match std::process::Command::new("tar")
            .arg("-xzf")
            .arg(package)
            .arg("-C")
            .arg(dest.path())
            .spawn()
        {
            Ok(child) => child,
            Err(e) => {
                if e.kind() == std::io::ErrorKind::NotFound {
                    return Err(PackageError::CommandNotFound {
                        command: "tar".to_string(),
                        path: package.to_path_buf(),
                    });
                }
                return Err(PackageError::CommandFailed {
                    command: "tar".to_string(),
                    path: package.to_path_buf(),
                    source: e,
                });
            }
        };

        let exit_status =
            wait_with_timeout(&mut child, DEFAULT_EXTRACTION_TIMEOUT, "tar", package)?;

        if exit_status.success() {
            Self::process(dest, package)
        } else {
            Err(PackageError::ExtractionFailed {
                path: package.to_path_buf(),
                reason: format!(
                    "tar exited with non-zero status: {}",
                    exit_status.code().unwrap_or(-1)
                ),
            })
        }
    }
}

#[cfg(test)]
mod tests {
    use crate::package::{Package, PackageFile};
    use std::path::PathBuf;

    fn get_examples_dir() -> PathBuf {
        match runfiles::Runfiles::create() {
            Ok(r) => r
                .rlocation("_main/tests/packaging/package_validator/fixtures")
                .expect("fixtures not found in runfiles"),
            Err(_) => PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("fixtures"),
        }
    }

    #[test]
    fn test_cma_package_extract() {
        let cma_path = get_examples_dir().join("test.cma");
        if !cma_path.exists() {
            eprintln!(
                "Skipping test: CMA test file not found at {}.",
                cma_path.display()
            );
            return;
        }

        let package = Package::new(cma_path).expect("Should extract CMA package");
        let files = package.files();
        assert!(
            !files.is_empty(),
            "Package should contain files after extraction"
        );

        // Verify specific expected structure
        let bin_files: Vec<_> = files
            .iter()
            .filter(|(path, _)| path.to_string_lossy().contains("/bin/"))
            .collect();
        let lib_files: Vec<_> = files
            .iter()
            .filter(|(path, _)| path.to_string_lossy().contains("/lib/"))
            .collect();

        assert!(
            !bin_files.is_empty() || !lib_files.is_empty(),
            "Package should contain bin or lib directories"
        );

        // Verify we found ELF files
        let elf_count = files
            .values()
            .filter(|f| matches!(f, PackageFile::Elf(_)))
            .count();
        assert!(
            elf_count > 0,
            "Package should contain at least one ELF file"
        );
    }
}
