// Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.
use rayon::prelude::*;
use serde::Serialize;
use std::ops::Add;

use crate::package::{ElfType, PackageElfs};

#[derive(Default, Debug, Clone, PartialEq, Eq, Serialize)]
pub(crate) struct Totals {
    pub(crate) none: usize,
    pub(crate) binaries: usize,
    pub(crate) shared_libraries: usize,
    pub(crate) relocatable: usize,
    pub(crate) core: usize,
    pub(crate) total: usize,
}

impl Totals {
    pub(crate) fn calculate(elfs: &PackageElfs) -> Self {
        elfs.par_iter()
            .fold(Totals::default, |mut totals, (_, e)| {
                match e.kind() {
                    ElfType::None => totals.none += 1,
                    ElfType::Executable => totals.binaries += 1,
                    ElfType::SharedObject => totals.shared_libraries += 1,
                    ElfType::Relocatable => totals.relocatable += 1,
                    ElfType::Core => totals.core += 1,
                }
                totals
            })
            .reduce(Totals::default, |a, b| a + b)
    }
}

impl Add for Totals {
    type Output = Self;

    fn add(self, other: Self) -> Self {
        let none = self.none + other.none;
        let binaries = self.binaries + other.binaries;
        let shared_libraries = self.shared_libraries + other.shared_libraries;
        let relocatable = self.relocatable + other.relocatable;
        let core = self.core + other.core;
        let total = none + binaries + shared_libraries + relocatable + core;
        Self {
            none,
            binaries,
            shared_libraries,
            relocatable,
            core,
            total,
        }
    }
}
