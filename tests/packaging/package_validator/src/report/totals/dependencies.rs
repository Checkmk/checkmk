// Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.
use dashmap::DashSet;
use rayon::prelude::*;
use serde::Serialize;
use std::ops::Add;

use crate::report::dependency_resolver::{DependencyKind, DependencyStatus};
use crate::report::ReportDependencies;

#[derive(Default, Debug, Clone, PartialEq, Eq, Serialize)]
pub(crate) struct Totals {
    pub(crate) missing: usize,
    pub(crate) missing_unique: usize,
    pub(crate) found: usize,
    pub(crate) found_unique: usize,
    pub(crate) error: usize,
    pub(crate) system: usize,
    pub(crate) package: usize,
    pub(crate) unknown: usize,
    pub(crate) total: usize,
    pub(crate) total_unique: usize,
}

impl Totals {
    pub(crate) fn calculate(dependencies: &ReportDependencies) -> Self {
        let found_unique = DashSet::new();
        let missing_unique = DashSet::new();
        let total_unique = DashSet::new();
        let mut totals = dependencies
            .par_iter()
            .fold(Totals::default, |mut totals, (_, deps)| {
                for (dependency, result) in deps {
                    total_unique.insert(*dependency);
                    match result.status {
                        DependencyStatus::Missing => {
                            totals.missing += 1;
                            missing_unique.insert(*dependency);
                        }
                        DependencyStatus::Found => {
                            totals.found += 1;
                            found_unique.insert(*dependency);
                        }
                        DependencyStatus::Error(_) => totals.error += 1,
                    }
                    match result.kind {
                        DependencyKind::System => totals.system += 1,
                        DependencyKind::Package => totals.package += 1,
                        DependencyKind::Unknown => totals.unknown += 1,
                    }
                }
                totals
            })
            .reduce(Totals::default, |a, b| a + b);
        totals.total_unique = total_unique.len();
        totals.missing_unique = missing_unique.len();
        totals.found_unique = found_unique.len();
        totals
    }
}

impl Add for Totals {
    type Output = Self;

    fn add(self, other: Self) -> Self {
        let missing = self.missing + other.missing;
        let found = self.found + other.found;
        let error = self.error + other.error;
        let package = self.package + other.package;
        let system = self.system + other.system;
        let unknown = self.unknown + other.unknown;
        let total = missing + found + error;
        Self {
            missing,
            found,
            error,
            system,
            package,
            unknown,
            total,
            total_unique: 0,   // Handled by the calculate function.
            missing_unique: 0, // Handled by the calculate function.
            found_unique: 0,   // Handled by the calculate function.
        }
    }
}
