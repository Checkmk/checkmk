// Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

//! Manages package lifecycle including extraction directory. Provides API for accessing package files, ELF files, and symlinks.

mod deb;
mod elf;
mod extractor;
mod files;
mod rpm;

use std::{
    collections::HashMap,
    path::{Path, PathBuf},
};
use tempfile::TempDir;

use deb::DebExtractor;
pub use elf::{Elf, ElfType};
use extractor::PackageExtractor;
use extractor::{PackageError, PackageResult};
pub use files::PackageFile;
use rpm::RpmExtractor;

/// Collection of files in a package, keyed by their path.
pub type PackageFiles = HashMap<PathBuf, PackageFile>;
pub(crate) type PackageSymlinks<'a> = HashMap<&'a Path, &'a Path>;
pub(crate) type PackageElfs<'a> = HashMap<&'a Path, &'a Elf>;

/// Package struct that manages package life-cycle including extraction directory.
pub struct Package {
    path: PathBuf,
    files: PackageFiles,
}

impl Package {
    /// Create a new package from a filepath.
    ///
    /// # Errors
    /// Returns an error if the package type cannot be determined or is unsupported.
    pub fn new(path: PathBuf) -> PackageResult<Self> {
        let files = Self::extract(&path)?;
        Ok(Self { path, files })
    }

    /// Get the path to the package.
    #[must_use]
    pub fn path(&self) -> &Path {
        &self.path
    }

    /// Get the files in the package.
    #[must_use]
    pub fn files(&self) -> &PackageFiles {
        &self.files
    }

    /// Get subset of ELF files.
    #[must_use]
    pub(crate) fn elfs(&self) -> PackageElfs<'_> {
        self.files
            .iter()
            .filter_map(|(path, file)| match file {
                PackageFile::Elf(elf) => Some((path.as_path(), elf)),
                _ => None,
            })
            .collect()
    }

    /// Get subset of symlinks.
    #[must_use]
    pub(crate) fn symlinks(&self) -> PackageSymlinks<'_> {
        self.files
            .iter()
            .filter_map(|(path, file)| match file {
                PackageFile::Symlink(symlink) => Some((path.as_path(), symlink.as_path())),
                _ => None,
            })
            .collect()
    }

    fn extract(path: &Path) -> PackageResult<PackageFiles> {
        let dest = TempDir::new().map_err(|e| PackageError::TempDirFailed { source: e })?;

        let extension = path
            .extension()
            .and_then(|ext| ext.to_str())
            .ok_or_else(|| PackageError::UnsupportedPackageType {
                extension: "unknown".to_string(),
            })?;

        let result = match extension {
            DebExtractor::EXTENSION => DebExtractor::extract(path, &dest),
            RpmExtractor::EXTENSION => RpmExtractor::extract(path, &dest),
            _ => {
                return Err(PackageError::UnsupportedPackageType {
                    extension: extension.to_string(),
                })
            }
        };
        // Explicitly close the temporary directory to prevent any errors from being hidden.
        dest.close()
            .map_err(|e| PackageError::TempDirFailed { source: e })?;
        result
    }

    #[cfg(test)]
    /// Create a test package with the given files.
    /// This is only available in test builds.
    pub(crate) fn new_for_testing(path: PathBuf, files: PackageFiles) -> Self {
        Self { path, files }
    }
}
