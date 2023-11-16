// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use crate::checker::{CheckResult, State};
use std::fmt::{Display, Formatter, Result as FormatResult};

pub struct Output {
    pub state: State,
    summary: String,
}

impl Display for Output {
    fn fmt(&self, f: &mut Formatter) -> FormatResult {
        if self.summary.is_empty() {
            write!(f, "{}", self.state)?;
        } else {
            write!(f, "{} - {}", self.state, self.summary)?;
        }
        Ok(())
    }
}

impl From<Vec<CheckResult>> for Output {
    fn from(check_results: Vec<CheckResult>) -> Self {
        Self {
            state: match check_results.iter().map(|cr| &cr.state).max() {
                Some(state) => state.clone(),
                None => State::Ok,
            },
            summary: check_results
                .iter()
                .filter(|cr| !cr.summary.is_empty())
                .map(|cr| cr.to_string())
                .collect::<Vec<_>>()
                .join(", "),
        }
    }
}

#[cfg(test)]
mod test_output_format {
    use super::{CheckResult, Output};

    fn s(s: &str) -> String {
        String::from(s)
    }

    #[test]
    fn test_no_check_results_is_ok() {
        assert_eq!(format!("{}", Output::from(vec![])), "OK");
    }

    #[test]
    fn test_merge_check_results_with_state_only() {
        let cr1 = CheckResult::default();
        let cr2 = CheckResult::default();
        let cr3 = CheckResult::default();
        assert_eq!(format!("{}", Output::from(vec![cr1, cr2, cr3])), "OK");
    }

    #[test]
    fn test_merge_check_results_ok() {
        let cr1 = CheckResult::ok(s("summary 1"));
        let cr2 = CheckResult::ok(s("summary 2"));
        let cr3 = CheckResult::ok(s("summary 3"));
        assert_eq!(
            format!("{}", Output::from(vec![cr1, cr2, cr3])),
            "OK - summary 1, summary 2, summary 3"
        );
    }

    #[test]
    fn test_merge_check_results_warn() {
        let cr1 = CheckResult::ok(s("summary 1"));
        let cr2 = CheckResult::warn(s("summary 2"));
        let cr3 = CheckResult::ok(s("summary 3"));
        assert_eq!(
            format!("{}", Output::from(vec![cr1, cr2, cr3])),
            "WARNING - summary 1, summary 2 (!), summary 3"
        );
    }

    #[test]
    fn test_merge_check_results_crit() {
        let cr1 = CheckResult::ok(s("summary 1"));
        let cr2 = CheckResult::warn(s("summary 2"));
        let cr3 = CheckResult::crit(s("summary 3"));
        assert_eq!(
            format!("{}", Output::from(vec![cr1, cr2, cr3])),
            "CRITICAL - summary 1, summary 2 (!), summary 3 (!!)"
        );
    }

    #[test]
    fn test_merge_check_results_unknown() {
        let cr1 = CheckResult::ok(s("summary 1"));
        let cr2 = CheckResult::warn(s("summary 2"));
        let cr3 = CheckResult::crit(s("summary 3"));
        let cr4 = CheckResult::unknown(s("summary 4"));
        assert_eq!(
            format!("{}", Output::from(vec![cr1, cr2, cr3, cr4])),
            "UNKNOWN - summary 1, summary 2 (!), summary 3 (!!), summary 4 (?)"
        );
    }
}
