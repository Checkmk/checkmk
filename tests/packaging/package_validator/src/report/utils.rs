// Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

//! Utility functions for output formatting.

use std::path::{Path, PathBuf};

/// Find the common prefix path shared by all given paths.
///
/// Returns `None` if the paths slice is empty or if there is no common prefix.
///
/// # Examples
///
/// ```ignore
/// use std::path::{Path, PathBuf};
///
/// let paths = vec![
///     Path::new("/usr/lib/foo"),
///     Path::new("/usr/lib/bar"),
///     Path::new("/usr/lib/baz"),
/// ];
/// let refs: Vec<&Path> = paths.iter().map(|p| p.as_ref()).collect();
/// assert_eq!(find_common_prefix(&refs), Some(PathBuf::from("/usr/lib")));
/// ```
#[must_use]
pub(crate) fn find_common_prefix(paths: &[&Path]) -> Option<PathBuf> {
    if paths.is_empty() {
        return None;
    }

    if paths.len() == 1 {
        return paths[0].parent().map(PathBuf::from);
    }

    let mut common = paths[0].to_path_buf();
    for path in paths.iter().skip(1) {
        let mut new_common = PathBuf::new();
        for (c1, c2) in common.components().zip(path.components()) {
            if c1 == c2 {
                new_common.push(c1);
            } else {
                break;
            }
        }
        common = new_common;
    }

    if common.as_os_str().is_empty() {
        None
    } else {
        Some(common)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_find_common_prefix_empty() {
        let paths: Vec<&Path> = vec![];
        assert_eq!(find_common_prefix(&paths), None);
    }

    #[test]
    fn test_find_common_prefix_single() {
        let paths = vec![Path::new("/usr/lib/foo")];
        assert_eq!(find_common_prefix(&paths), Some(PathBuf::from("/usr/lib")));
    }

    #[test]
    fn test_find_common_prefix_multiple() {
        let paths = vec![
            Path::new("/usr/lib/foo"),
            Path::new("/usr/lib/bar"),
            Path::new("/usr/lib/baz"),
        ];
        assert_eq!(find_common_prefix(&paths), Some(PathBuf::from("/usr/lib")));
    }

    #[test]
    fn test_find_common_prefix_no_common() {
        let paths = vec![Path::new("/usr/lib/foo"), Path::new("/opt/lib/bar")];
        assert_eq!(find_common_prefix(&paths), Some(PathBuf::from("/")));
    }
}
