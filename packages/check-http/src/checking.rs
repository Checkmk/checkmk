// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use std::fmt::{Display, Formatter, Result as FormatResult};

#[derive(Clone, PartialEq, Eq, PartialOrd, Ord, Debug)]
pub enum State {
    Ok,
    Warn,
    Crit,
    Unknown,
}

impl Display for State {
    fn fmt(&self, f: &mut Formatter) -> FormatResult {
        match self {
            Self::Ok => write!(f, "OK"),
            Self::Warn => write!(f, "WARNING"),
            Self::Crit => write!(f, "CRITICAL"),
            Self::Unknown => write!(f, "UNKNOWN"),
        }
    }
}

impl From<State> for i32 {
    fn from(value: State) -> Self {
        match value {
            State::Ok => 0,
            State::Warn => 1,
            State::Crit => 2,
            State::Unknown => 3,
        }
    }
}

impl State {
    fn as_marker(&self) -> &'static str {
        match self {
            State::Ok => "",
            State::Warn => " (!)",
            State::Crit => " (!!)",
            State::Unknown => " (?)",
        }
    }
}

pub struct CheckResult {
    pub state: State,
    pub summary: String,
}

pub struct Output {
    pub worst_state: State,
    check_results: Vec<CheckResult>,
}

impl Display for Output {
    fn fmt(&self, f: &mut Formatter) -> FormatResult {
        write!(f, "HTTP {}", self.worst_state)?;
        let mut crs_iter = self
            .check_results
            .iter()
            .filter(|cr| !cr.summary.is_empty());
        if let Some(item) = crs_iter.next() {
            write!(f, " - {}{}", item.summary, item.state.as_marker())?;
        }
        for item in crs_iter {
            write!(f, ", {}{}", item.summary, item.state.as_marker())?;
        }
        Ok(())
    }
}

impl Output {
    pub fn from_check_results(check_results: Vec<CheckResult>) -> Self {
        let state = check_results
            .iter()
            .map(|output| output.state.clone())
            .max()
            .unwrap();

        Self {
            worst_state: state,
            check_results,
        }
    }
}

#[cfg(test)]
mod test_output_format {
    use super::*;

    fn s(s: &str) -> String {
        String::from(s)
    }

    #[test]
    fn test_merge_check_results_with_state_only() {
        let cr1 = CheckResult {
            state: State::Ok,
            summary: s(""),
        };
        let cr2 = CheckResult {
            state: State::Ok,
            summary: s(""),
        };
        let cr3 = CheckResult {
            state: State::Ok,
            summary: s(""),
        };
        assert_eq!(
            format!("{}", Output::from_check_results(vec![cr1, cr2, cr3])),
            "HTTP OK"
        );
    }

    #[test]
    fn test_merge_check_results_ok() {
        let cr1 = CheckResult {
            state: State::Ok,
            summary: s("summary 1"),
        };
        let cr2 = CheckResult {
            state: State::Ok,
            summary: s("summary 2"),
        };
        let cr3 = CheckResult {
            state: State::Ok,
            summary: s("summary 3"),
        };
        assert_eq!(
            format!("{}", Output::from_check_results(vec![cr1, cr2, cr3])),
            "HTTP OK - summary 1, summary 2, summary 3"
        );
    }

    #[test]
    fn test_merge_check_results_crit() {
        let cr1 = CheckResult {
            state: State::Ok,
            summary: s("summary 1"),
        };
        let cr2 = CheckResult {
            state: State::Warn,
            summary: s("summary 2"),
        };
        let cr3 = CheckResult {
            state: State::Crit,
            summary: s("summary 3"),
        };
        assert_eq!(
            format!("{}", Output::from_check_results(vec![cr1, cr2, cr3])),
            "HTTP CRITICAL - summary 1, summary 2 (!), summary 3 (!!)"
        );
    }
}
