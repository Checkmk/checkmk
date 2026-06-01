// Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

//! Configuration loaded from disk: lists of system dependencies and files
//! to ignore during validation. Owned by the caller (typically `main`) and
//! passed by reference into the report layer.

pub mod ignored_files;
pub mod system_dependencies;

pub use ignored_files::IgnoredFiles;
pub use system_dependencies::SystemDependencies;
