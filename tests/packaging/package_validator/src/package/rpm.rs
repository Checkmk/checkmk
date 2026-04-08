// Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

//! Implements RPM package extraction using `rpm2cpio` and `cpio`.

use std::path::Path;
use std::process::Stdio;
use std::time::Instant;
use tempfile::TempDir;

use super::extractor::{
    wait_with_timeout, PackageError, PackageExtractor, PackageResult, DEFAULT_EXTRACTION_TIMEOUT,
};
use super::PackageFiles;

pub(crate) struct RpmExtractor;

impl PackageExtractor for RpmExtractor {
    const EXTENSION: &'static str = "rpm";

    /// Extract an RPM package into a temporary directory.
    ///
    /// # Errors
    /// Returns an error if the package cannot be extracted.
    ///
    /// # Timeout
    /// This function enforces a total timeout of 30 seconds for the `rpm2cpio` and
    /// `cpio` pipeline. If extraction takes longer, the processes will be killed and
    /// a `CommandTimeout` error will be returned.
    fn extract(package: &Path, dest: &TempDir) -> PackageResult<PackageFiles> {
        let start = Instant::now();

        // Use system commands for maximum performance: rpm2cpio | cpio -id
        // This is much faster than parsing CPIO in Rust, especially for large RPMs
        // The system cpio command handles padding, alignment, and all edge cases efficiently
        let mut rpm2cpio_child = match std::process::Command::new("rpm2cpio")
            .arg(package)
            .stdout(Stdio::piped())
            .spawn()
        {
            Ok(child) => child,
            Err(e) => {
                if e.kind() == std::io::ErrorKind::NotFound {
                    return Err(PackageError::CommandNotFound {
                        command: "rpm2cpio".to_string(),
                        path: package.to_path_buf(),
                    });
                }
                return Err(PackageError::CommandFailed {
                    command: "rpm2cpio".to_string(),
                    path: package.to_path_buf(),
                    source: e,
                });
            }
        };

        let Some(rpm2cpio_stdout) = rpm2cpio_child.stdout.take() else {
            let _ = rpm2cpio_child.kill();
            let _ = rpm2cpio_child.wait();
            return Err(PackageError::ExtractionFailed {
                path: package.to_path_buf(),
                reason: "Failed to get stdout from rpm2cpio".to_string(),
            });
        };

        let mut cpio_child = match std::process::Command::new("cpio")
            .arg("-id")
            .arg("--quiet")
            .current_dir(dest.path())
            .stdin(rpm2cpio_stdout)
            .spawn()
        {
            Ok(child) => child,
            Err(e) => {
                let _ = rpm2cpio_child.kill();
                let _ = rpm2cpio_child.wait();
                if e.kind() == std::io::ErrorKind::NotFound {
                    return Err(PackageError::CommandNotFound {
                        command: "cpio".to_string(),
                        path: package.to_path_buf(),
                    });
                }
                return Err(PackageError::CommandFailed {
                    command: "cpio".to_string(),
                    path: package.to_path_buf(),
                    source: e,
                });
            }
        };

        // Wait for cpio with the remaining timeout (subtracting time already elapsed)
        let elapsed = start.elapsed();
        let remaining_timeout = DEFAULT_EXTRACTION_TIMEOUT.saturating_sub(elapsed);
        let cpio_status = wait_with_timeout(&mut cpio_child, remaining_timeout, "cpio", package)?;

        // Clean up rpm2cpio - it should have finished by now since cpio consumed all its output
        let _ = rpm2cpio_child.wait();

        if cpio_status.success() {
            Self::process(dest, package)
        } else {
            Err(PackageError::ExtractionFailed {
                path: package.to_path_buf(),
                reason: format!(
                    "cpio exited with non-zero status: {}",
                    cpio_status.code().unwrap_or(-1)
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
    fn test_rpm_package_extract() {
        let rpm_path = get_examples_dir().join("test.rpm");
        if !rpm_path.exists() {
            eprintln!(
                "Skipping test: RPM test file not found at {}.",
                rpm_path.display()
            );
            return;
        }

        let package = Package::new(rpm_path).expect("Should extract RPM package");
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
