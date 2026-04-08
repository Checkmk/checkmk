// Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

//! Defines types for different package file types (ELF, Symlink, Other).

use path_clean::PathClean;
use serde::Serialize;
use std::fs;
use std::path::{Path, PathBuf};

use super::elf::{Elf, ElfError};
use super::extractor::{ExtractedFile, PackageError, PackageResult};

/// Represents a file in a package.
#[derive(Debug, Clone, Serialize)]
pub enum PackageFile {
    File,
    Symlink(PathBuf), // Stores the normalized target path of the symlink.
    Elf(Elf),
}

impl PackageFile {
    /// Create a new package file from a path.
    ///
    /// # Errors
    /// Returns an error if the file is not a valid package file.
    pub(crate) fn new(extracted_file: &ExtractedFile) -> PackageResult<Self> {
        let path = extracted_file.path();
        if path.is_symlink() {
            let target = fs::read_link(path).map_err(|e| PackageError::ReadSymlinkFailed {
                path: path.to_path_buf(),
                source: e,
            })?;
            // Resolve relative targets relative to the symlink's parent directory
            let resolved_target = if target.is_absolute() {
                target
            } else {
                // The target path should be relative within the package not the extraction directory.
                extracted_file
                    .package_path()
                    .parent()
                    .unwrap_or_else(|| Path::new("/"))
                    .join(&target)
            };
            let normalized_target = resolved_target.clean();
            return Ok(Self::Symlink(normalized_target));
        }
        if !Elf::is_invalid_extension(path) {
            return match Elf::from_path(path) {
                Ok(elf) => Ok(Self::Elf(elf)),
                Err(ElfError::NotElfFile { .. } | ElfError::FileTooSmall { .. }) => Ok(Self::File),
                Err(e) => Err(PackageError::ElfError(e)),
            };
        }
        Ok(Self::File)
    }
}
