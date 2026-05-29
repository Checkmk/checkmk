// Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

//! `Finding`: the single failure type produced by all validators.
//! Each variant is emitted by a validator under `crate::validators::*`.
//!
//! A `Finding` is always carried in a `Vec<Finding>` and pattern-matched into a
//! console row (see `report::console`) — it is never used as a `std::error::Error`
//! or rendered through `Display`, so it deliberately implements neither.
//!
//! Every variant is keyed by one affected ELF (one finding per file, never per
//! dependency), so a console row count equals an affected-file count.

use serde::Serialize;
use std::path::Path;

#[derive(Debug, Serialize)]
pub(crate) enum Finding<'a> {
    SystemDependencyFoundInPackage {
        dependency: &'a str,
        paths: Vec<&'a Path>,
    },
    RpathShape {
        path: &'a Path,
        paths: Vec<String>,
    },
    UnreadableElf {
        path: &'a Path,
        message: &'a str,
    },
    /// Build-host paths (e.g. `/.cache/bazel/`) leaked in the ELF's `.rodata`.
    /// One finding per ELF.
    EmbeddedBuildPaths {
        path: &'a Path,
        strings: Vec<String>,
    },
    /// All dependencies of `path` that errored during resolution, as
    /// `(dependency, message)` pairs. One finding per ELF.
    DependencyResolutionError {
        path: &'a Path,
        errors: Vec<(&'a str, String)>,
    },
    /// All dependencies of `path` that could not be found. One finding per ELF.
    MissingDependency {
        path: &'a Path,
        dependencies: Vec<&'a str>,
    },
}
