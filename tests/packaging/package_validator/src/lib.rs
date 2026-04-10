// Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

//! A tool for validating RPATH/RUNPATH settings in DEB, RPM, and CMA packages.
//!
//! This crate provides functionality to:
//! - Extract and analyze DEB, RPM, and CMA packages
//! - Parse ELF binaries to extract dependency information
//! - Validate RPATH/RUNPATH settings for proper dependency resolution
//! - Generate reports on dependency status

pub mod package;
pub mod report;

// Re-export key types for convenience
pub use package::{Elf, ElfType, Package, PackageFile};
pub use report::{IgnoredFiles, Report, SystemDependencies};
