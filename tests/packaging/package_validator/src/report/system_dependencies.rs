// Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

//! Resolves system dependencies using exact name matching from a configuration file.

use anyhow::{Context, Result};
use std::collections::HashSet;
use std::fs;
use std::path::Path;

/// Resolves system dependencies by matching exact dependency names.
#[derive(Default)]
pub struct SystemDependencies {
    dependencies: HashSet<String>,
}

impl SystemDependencies {
    /// Create an empty `SystemDependencyResolver` with no dependencies.
    ///
    /// This is useful for testing or when no system dependency patterns are needed.
    #[must_use]
    pub fn empty() -> Self {
        Self::default()
    }

    /// Create a new `SystemDependencyResolver` from a file containing exact dependency names.
    ///
    /// Each line in the file is treated as an exact dependency name. Empty lines and lines
    /// starting with `#` are ignored.
    ///
    /// # Errors
    /// Returns an error if the file cannot be read.
    pub fn from_file<P: AsRef<Path>>(path: P) -> Result<Self> {
        let content = fs::read_to_string(path.as_ref()).with_context(|| {
            format!(
                "Failed to read system deps file: {}",
                path.as_ref().display()
            )
        })?;

        let dependencies: HashSet<String> = content
            .lines()
            .map(str::trim)
            .filter(|line| !line.is_empty() && !line.starts_with('#'))
            .map(std::string::ToString::to_string)
            .collect();

        Ok(Self { dependencies })
    }

    /// Get the system dependencies.
    #[must_use]
    pub(crate) fn dependencies(&self) -> &HashSet<String> {
        &self.dependencies
    }

    /// Check if a dependency name exactly matches any of the system dependencies.
    #[must_use]
    pub(crate) fn contains(&self, dependency: &str) -> bool {
        self.dependencies.contains(dependency)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::Write;
    use tempfile::NamedTempFile;

    #[test]
    fn test_empty_resolver() {
        let dependencies = SystemDependencies::empty();
        assert!(!dependencies.contains("libm.so"));
    }

    #[test]
    fn test_simple_pattern() {
        let mut file = NamedTempFile::new().unwrap();
        writeln!(file, "libm.so.6").unwrap();
        file.flush().unwrap();

        let dependencies = SystemDependencies::from_file(file.path()).unwrap();
        assert!(dependencies.contains("libm.so.6"));
        assert!(!dependencies.contains("libm.so"));
        assert!(!dependencies.contains("libc.so.6"));
    }

    #[test]
    fn test_multiple_patterns() {
        let mut file = NamedTempFile::new().unwrap();
        writeln!(file, "libm.so.6").unwrap();
        writeln!(file, "libc.so.6").unwrap();
        writeln!(file, "libpthread.so.0").unwrap();
        file.flush().unwrap();

        let dependencies = SystemDependencies::from_file(file.path()).unwrap();
        assert!(dependencies.contains("libm.so.6"));
        assert!(dependencies.contains("libc.so.6"));
        assert!(dependencies.contains("libpthread.so.0"));
        assert!(!dependencies.contains("libssl.so"));
    }

    #[test]
    fn test_ignore_comments_and_empty_lines() {
        let mut file = NamedTempFile::new().unwrap();
        writeln!(file, "# This is a comment").unwrap();
        writeln!(file, "").unwrap();
        writeln!(file, "libm.so.6").unwrap();
        writeln!(file, "  # Another comment").unwrap();
        writeln!(file, "libc.so.6").unwrap();
        file.flush().unwrap();

        let dependencies = SystemDependencies::from_file(file.path()).unwrap();
        assert!(dependencies.contains("libm.so.6"));
        assert!(dependencies.contains("libc.so.6"));
    }

    #[test]
    fn test_file_not_found() {
        let result = SystemDependencies::from_file("/nonexistent/file.txt");
        assert!(result.is_err());
        assert!(result.err().unwrap().to_string().contains("Failed to read"));
    }

    #[test]
    fn test_trimming() {
        let mut file = NamedTempFile::new().unwrap();
        writeln!(file, "  libm.so.6  ").unwrap();
        writeln!(file, "libc.so.6").unwrap();
        writeln!(file, "\tlibpthread.so.0\t").unwrap();
        file.flush().unwrap();

        let dependencies = SystemDependencies::from_file(file.path()).unwrap();
        // Lines are trimmed when reading, so exact matches work
        assert!(dependencies.contains("libm.so.6"));
        assert!(!dependencies.contains("  libm.so.6  "));
        assert!(dependencies.contains("libc.so.6"));
        assert!(dependencies.contains("libpthread.so.0"));
    }
}
