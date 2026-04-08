// Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

//! Defines the `PackageExtractor` trait for extracting different package formats.

use std::os::unix::process::ExitStatusExt;
use std::path::{Path, PathBuf};
use std::process::Child;
use std::time::Duration;
use tempfile::TempDir;
use thiserror::Error;
use wait_timeout::ChildExt;
use walkdir::WalkDir;

use super::elf::ElfError;
use super::files::PackageFile;
use super::PackageFiles;

/// Default timeout for package extraction commands (30 seconds).
pub(crate) const DEFAULT_EXTRACTION_TIMEOUT: Duration = Duration::from_secs(30);

/// Result type for package operations.
pub type PackageResult<T> = std::result::Result<T, PackageError>;

/// Errors that can occur during package operations.
#[derive(Debug, Error)]
pub enum PackageError {
    #[error("Failed to create/delete temporary directory")]
    TempDirFailed {
        #[source]
        source: std::io::Error,
    },
    #[error("Command not found: {command} (package: {path:?})")]
    CommandNotFound { command: String, path: PathBuf },
    #[error("Command failed: {command} (package: {path:?})")]
    CommandFailed {
        command: String,
        path: PathBuf,
        #[source]
        source: std::io::Error,
    },
    #[error("Command timed out after {timeout:?}: {command} (package: {path:?})")]
    CommandTimeout {
        command: String,
        path: PathBuf,
        timeout: Duration,
    },
    #[error("Extraction failed for package {path:?}: {reason}")]
    ExtractionFailed { path: PathBuf, reason: String },
    #[error("Failed to walk extracted directory: {path:?}")]
    WalkDirFailed {
        path: PathBuf,
        #[source]
        source: walkdir::Error,
    },
    #[error("Unsupported package type: {extension}")]
    UnsupportedPackageType { extension: String },
    #[error("Failed to read symlink: {path:?}")]
    ReadSymlinkFailed {
        path: PathBuf,
        #[source]
        source: std::io::Error,
    },
    #[error("Elf error: {0}")]
    ElfError(#[from] ElfError),
}

/// Wait for a child process to complete with a timeout.
///
/// Uses platform-specific APIs (SIGCHLD on Unix, `WaitForSingleObject` on Windows)
/// to wait for the process without polling. If the timeout is reached, the process is killed.
///
/// # Returns
/// - `Ok(ExitStatus)` if the process completed within the timeout
/// - `Err(PackageError::CommandTimeout)` if the process timed out
/// - `Err(PackageError::CommandFailed)` if there was an error waiting for the process
pub(crate) fn wait_with_timeout(
    child: &mut Child,
    timeout: Duration,
    command: &str,
    package_path: &Path,
) -> PackageResult<std::process::ExitStatus> {
    // Returns status if the process completed within the timeout, none otherwise.
    // In the case of an error it propagates the error.
    if let Some(status) = child
        .wait_timeout(timeout)
        .map_err(|e| PackageError::CommandFailed {
            command: command.to_string(),
            path: package_path.to_path_buf(),
            source: e,
        })?
    {
        // Check if the process completed successfully or was terminated by a signal.
        if status.code().is_some() {
            Ok(status)
        } else if let Some(signal) = status.signal() {
            Err(PackageError::CommandFailed {
                command: command.to_string(),
                path: package_path.to_path_buf(),
                source: std::io::Error::other(format!("Process terminated by signal: {signal}")),
            })
        } else {
            Err(PackageError::CommandFailed {
                command: command.to_string(),
                path: package_path.to_path_buf(),
                source: std::io::Error::other("Unknown process termination"),
            })
        }
    } else {
        // Timeout has been reached - kill the process
        let _ = child.kill();
        let _ = child.wait();
        Err(PackageError::CommandTimeout {
            command: command.to_string(),
            path: package_path.to_path_buf(),
            timeout,
        })
    }
}

/// Represents a file extracted from the package.
pub(crate) struct ExtractedFile<'a> {
    extraction_directory: &'a TempDir, // The directory where the package was extracted (paths within the package are relative to this directory).
    extracted_path: &'a Path,          // The path to the file within the extraction directory.
}

impl<'a> ExtractedFile<'a> {
    pub(crate) fn new(extraction_directory: &'a TempDir, extracted_path: &'a Path) -> Self {
        Self {
            extraction_directory,
            extracted_path,
        }
    }

    /// Get the path of the file within the extraction directory.
    ///
    /// # Returns
    /// The path of the file within the extraction directory.
    pub(crate) fn path(&self) -> &Path {
        self.extracted_path
    }

    /// Get the absolute path of the file within the package.
    ///
    /// # Panics
    /// Panics if the path cannot be stripped. This should never happen as all files in the package will be sub-paths of the extraction directory.
    pub(crate) fn package_path(&self) -> PathBuf {
        // We're ok with panicking here because we know the path is valid as all files in the package will be sub-paths of the extraction directory.
        let stripped = self
            .extracted_path
            .strip_prefix(self.extraction_directory.path())
            .unwrap();
        // Prepend '/' to make paths absolute (package files are absolute paths)
        Path::new("/").join(stripped)
    }
}

/// Trait for package extractors that perform the actual extraction logic.
pub(crate) trait PackageExtractor {
    const EXTENSION: &'static str; // Packages are identified by their extension.

    /// Extract package contents to a destination directory.
    ///
    /// # Errors
    /// Returns an error if extraction fails.
    fn extract(package: &Path, dest: &TempDir) -> PackageResult<PackageFiles>;

    /// Walk the extracted directory and collect files.
    ///
    /// # Errors
    /// Returns an error if walking the directory fails or no files are found.
    fn process(dest: &TempDir, package: &Path) -> PackageResult<PackageFiles> {
        let mut files = PackageFiles::new();
        for entry in WalkDir::new(dest.path()) {
            let e = entry.map_err(|e| PackageError::WalkDirFailed {
                path: package.to_path_buf(),
                source: e,
            })?;
            if e.file_type().is_file() || e.file_type().is_symlink() {
                let extracted_file = ExtractedFile::new(dest, e.path());
                let file = PackageFile::new(&extracted_file)?;
                files.insert(extracted_file.package_path(), file);
            }
        }

        if files.is_empty() {
            Err(PackageError::ExtractionFailed {
                path: package.to_path_buf(),
                reason: "Extraction completed but no files were found".to_string(),
            })
        } else {
            Ok(files)
        }
    }
}
