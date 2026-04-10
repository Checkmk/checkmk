// Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

//! Resolves system dependencies by matching the base `.so` name from a configuration file.

use anyhow::{Context, Result};
use std::collections::HashSet;
use std::fs;
use std::path::Path;

/// Resolves system dependencies by matching the base `.so` name (version suffix ignored).
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

    /// Create a new `SystemDependencyResolver` from a file containing base `.so` names.
    ///
    /// Each line in the file is treated as a base dependency name (e.g. `libcairo.so`).
    /// Empty lines and lines starting with `#` are ignored.
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

    /// Check if a dependency matches any system dependency by base `.so` name.
    ///
    /// The version suffix is stripped before matching, so `libcairo.so.2` matches
    /// a `libcairo.so` entry. Names with no version suffix match directly.
    #[must_use]
    pub(crate) fn contains(&self, dependency: &str) -> bool {
        self.dependencies.contains(so_base_name(dependency))
    }
}

/// Extract the base `.so` name by stripping any trailing version suffix.
///
/// For example: `"libcairo.so.2"` → `"libcairo.so"`, `"libm.so.6.0"` → `"libm.so"`.
/// Names already without a version suffix are returned unchanged.
fn so_base_name(name: &str) -> &str {
    name.split_once(".so")
        .filter(|(_, suffix)| suffix.is_empty() || suffix.starts_with('.'))
        .map_or(name, |(prefix, _)| &name[..prefix.len() + ".so".len()])
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
        writeln!(file, "libm.so").unwrap();
        file.flush().unwrap();

        let dependencies = SystemDependencies::from_file(file.path()).unwrap();
        // Versioned names on disk match the base .so entry
        assert!(dependencies.contains("libm.so.6"));
        assert!(dependencies.contains("libm.so"));
        assert!(!dependencies.contains("libc.so.6"));
    }

    #[test]
    fn test_multiple_patterns() {
        let mut file = NamedTempFile::new().unwrap();
        writeln!(file, "libm.so").unwrap();
        writeln!(file, "libc.so").unwrap();
        writeln!(file, "libpthread.so").unwrap();
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
        writeln!(file, "libm.so").unwrap();
        writeln!(file, "  # Another comment").unwrap();
        writeln!(file, "libc.so").unwrap();
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
        writeln!(file, "  libm.so  ").unwrap();
        writeln!(file, "libc.so").unwrap();
        writeln!(file, "\tlibpthread.so\t").unwrap();
        file.flush().unwrap();

        let dependencies = SystemDependencies::from_file(file.path()).unwrap();
        // Lines are trimmed when reading; versioned names on disk match base entries
        assert!(dependencies.contains("libm.so.6"));
        assert!(!dependencies.contains("  libm.so.6  "));
        assert!(dependencies.contains("libc.so.6"));
        assert!(dependencies.contains("libpthread.so.0"));
    }

    #[test]
    fn test_so_base_name_version_stripping() {
        assert_eq!(so_base_name("libcairo.so.2"), "libcairo.so");
        assert_eq!(so_base_name("libm.so.6"), "libm.so");
        assert_eq!(so_base_name("libbz2.so.1.0"), "libbz2.so");
        assert_eq!(so_base_name("libpcap.so.0.8"), "libpcap.so");
        // Names without a version suffix are unchanged
        assert_eq!(so_base_name("libperl.so"), "libperl.so");
        assert_eq!(so_base_name("libtcl8.6.so"), "libtcl8.6.so");
        assert_eq!(so_base_name("libnspr4.so"), "libnspr4.so");
    }
}
