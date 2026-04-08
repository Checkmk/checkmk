// Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

//! Statistics calculation modules for ELF files and dependencies.

mod dependencies;
mod elf;

use serde::Serialize;

use crate::package::{PackageElfs, PackageFiles};
use crate::report::ReportDependencies;

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub(crate) struct ReportTotals {
    pub(crate) files: usize,
    pub(crate) elfs: elf::Totals,
    pub(crate) dependencies: dependencies::Totals,
}

impl ReportTotals {
    #[must_use]
    pub(crate) fn new(
        files: &PackageFiles,
        elfs: &PackageElfs,
        dependencies: &ReportDependencies,
    ) -> Self {
        Self {
            files: files.len(),
            elfs: elf::Totals::calculate(elfs),
            dependencies: dependencies::Totals::calculate(dependencies),
        }
    }
}
