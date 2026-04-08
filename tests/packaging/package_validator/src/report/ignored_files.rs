// Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

//! Resolves ignored files using exact path matching from a configuration file.

use anyhow::{Context, Result};
use std::collections::HashSet;
use std::fs;
use std::path::{Path, PathBuf};

/// Files to skip during validation, matched by path suffix against the absolute package path.
#[derive(Default)]
pub struct IgnoredFiles {
    paths: HashSet<PathBuf>,
}

impl IgnoredFiles {
    /// Create an empty `IgnoredFiles` with no paths.
    #[must_use]
    pub fn empty() -> Self {
        Self::default()
    }

    /// Create a new `IgnoredFiles` from a file containing package path suffixes.
    ///
    /// Each line is matched as a path suffix against the absolute package path
    /// (e.g. `lib/python3/cmk/plugins/oracle/agents/mk-oracle` matches
    /// `/lib/python3/cmk/plugins/oracle/agents/mk-oracle`).
    /// Empty lines and lines starting with `#` are ignored.
    ///
    /// # Errors
    /// Returns an error if the file cannot be read.
    pub fn from_file<P: AsRef<Path>>(path: P) -> Result<Self> {
        let content = fs::read_to_string(path.as_ref()).with_context(|| {
            format!("Failed to read ignored files: {}", path.as_ref().display())
        })?;

        let paths: HashSet<PathBuf> = content
            .lines()
            .map(str::trim)
            .filter(|line| !line.is_empty() && !line.starts_with('#'))
            .map(PathBuf::from)
            .collect();

        Ok(Self { paths })
    }

    /// Check if a package path ends with any of the ignored file sub-paths.
    ///
    /// Uses component-wise suffix matching so `lib/python3/foo` matches
    /// `/lib/python3/foo` but not `/llib/python3/foo`.
    #[must_use]
    pub(crate) fn contains(&self, path: &Path) -> bool {
        self.paths.iter().any(|p| path.ends_with(p))
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::Write;
    use tempfile::NamedTempFile;

    #[test]
    fn test_empty() {
        let ignored = IgnoredFiles::empty();
        assert!(!ignored.contains(Path::new("/python3/cmk/plugins/oracle/agents/mk-oracle")));
    }

    #[test]
    fn test_single_entry() {
        let mut file = NamedTempFile::new().unwrap();
        writeln!(file, "lib/python3/cmk/plugins/oracle/agents/mk-oracle").unwrap();
        file.flush().unwrap();

        let ignored = IgnoredFiles::from_file(file.path()).unwrap();
        // Matches full absolute package path by suffix
        assert!(ignored.contains(Path::new(
            "/lib/python3/cmk/plugins/oracle/agents/mk-oracle"
        )));
        // Does not match a different file
        assert!(!ignored.contains(Path::new(
            "/lib/python3/cmk/plugins/oracle/agents/mk-oracle.solaris"
        )));
        assert!(!ignored.contains(Path::new("/usr/bin/myapp")));
    }

    #[test]
    fn test_multiple_entries() {
        let mut file = NamedTempFile::new().unwrap();
        writeln!(file, "lib/python3/cmk/plugins/oracle/agents/mk-oracle").unwrap();
        writeln!(
            file,
            "lib/python3/cmk/plugins/oracle/agents/mk-oracle.solaris"
        )
        .unwrap();
        file.flush().unwrap();

        let ignored = IgnoredFiles::from_file(file.path()).unwrap();
        assert!(ignored.contains(Path::new(
            "/lib/python3/cmk/plugins/oracle/agents/mk-oracle"
        )));
        assert!(ignored.contains(Path::new(
            "/lib/python3/cmk/plugins/oracle/agents/mk-oracle.solaris"
        )));
        assert!(!ignored.contains(Path::new("/usr/bin/myapp")));
    }

    #[test]
    fn test_ignore_comments_and_empty_lines() {
        let mut file = NamedTempFile::new().unwrap();
        writeln!(file, "# This is a comment").unwrap();
        writeln!(file, "").unwrap();
        writeln!(file, "lib/python3/cmk/plugins/oracle/agents/mk-oracle").unwrap();
        writeln!(file, "  # Another comment").unwrap();
        writeln!(
            file,
            "lib/python3/cmk/plugins/oracle/agents/mk-oracle.solaris"
        )
        .unwrap();
        file.flush().unwrap();

        let ignored = IgnoredFiles::from_file(file.path()).unwrap();
        assert!(ignored.contains(Path::new(
            "/lib/python3/cmk/plugins/oracle/agents/mk-oracle"
        )));
        assert!(ignored.contains(Path::new(
            "/lib/python3/cmk/plugins/oracle/agents/mk-oracle.solaris"
        )));
    }

    #[test]
    fn test_trimming() {
        let mut file = NamedTempFile::new().unwrap();
        writeln!(file, "  lib/python3/cmk/plugins/oracle/agents/mk-oracle  ").unwrap();
        file.flush().unwrap();

        let ignored = IgnoredFiles::from_file(file.path()).unwrap();
        assert!(ignored.contains(Path::new(
            "/lib/python3/cmk/plugins/oracle/agents/mk-oracle"
        )));
    }

    #[test]
    fn test_file_not_found() {
        let result = IgnoredFiles::from_file("/nonexistent/file.txt");
        assert!(result.is_err());
        assert!(result
            .err()
            .unwrap()
            .to_string()
            .contains("Failed to read ignored files"));
    }

    #[test]
    fn test_subpath_matching() {
        let mut file = NamedTempFile::new().unwrap();
        writeln!(file, "lib/python3/cmk/plugins/oracle/agents/mk-oracle").unwrap();
        file.flush().unwrap();

        let ignored = IgnoredFiles::from_file(file.path()).unwrap();
        // Full suffix match works
        assert!(ignored.contains(Path::new(
            "/lib/python3/cmk/plugins/oracle/agents/mk-oracle"
        )));
        // Partial suffix (just filename) also matches
        assert!(ignored.contains(Path::new(
            "/any/prefix/lib/python3/cmk/plugins/oracle/agents/mk-oracle"
        )));
        // Parent directory does not match
        assert!(!ignored.contains(Path::new("/lib/python3/cmk/plugins/oracle/agents")));
        // No partial component match — 'oracle' alone doesn't match 'mk-oracle'
        assert!(!ignored.contains(Path::new("/lib/python3/cmk/plugins/oracle")));
    }
}
