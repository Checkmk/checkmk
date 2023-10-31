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
    pub summary: Option<String>,
    pub details: Option<String>,
}

impl Display for CheckResult {
    fn fmt(&self, f: &mut Formatter) -> FormatResult {
        write!(f, "HTTP {}", self.state)?;
        if let Some(summary) = self.summary.as_ref() {
            write!(f, " - {}", summary)?;
        }
        if let Some(details) = self.details.as_ref() {
            write!(f, "\n{}", details)?;
        }
        Ok(())
    }
}

impl CheckResult {
    pub fn from_summary(state: State, summary: &str) -> Self {
        let summary = format!("{}{}", summary, state.as_marker());
        Self {
            state,
            summary: Some(summary),
            details: None,
        }
    }

    pub fn from_state(state: State) -> Self {
        Self {
            state,
            summary: None,
            details: None,
        }
    }
}

#[cfg(test)]
mod test_output_format {
    use super::*;
    use crate::merge_check_results;

    fn s(s: &str) -> Option<String> {
        Some(String::from(s))
    }

    #[test]
    fn test_check_result_with_state_only() {
        assert_eq!(
            format!(
                "{}",
                CheckResult {
                    state: State::Ok,
                    summary: None,
                    details: None
                }
            ),
            "HTTP OK"
        );
    }

    #[test]
    fn test_check_result_with_empty_fields() {
        assert_eq!(
            format!(
                "{}",
                CheckResult {
                    state: State::Ok,
                    summary: s(""),
                    details: s("")
                }
            ),
            // Expected "HTTP OK"
            "HTTP OK - \n"
        );
    }

    #[test]
    fn test_check_result_with_summary() {
        assert_eq!(
            format!(
                "{}",
                CheckResult {
                    state: State::Ok,
                    summary: s("this is the summary"),
                    details: None
                }
            ),
            "HTTP OK - this is the summary"
        );
    }

    #[test]
    fn test_check_result_with_details() {
        assert_eq!(
            format!(
                "{}",
                CheckResult {
                    state: State::Ok,
                    summary: None,
                    details: s("these are the details")
                }
            ),
            "HTTP OK\nthese are the details"
        );
    }

    #[test]
    fn test_check_result_with_summary_and_details() {
        assert_eq!(
            format!(
                "{}",
                CheckResult {
                    state: State::Ok,
                    summary: s("this is the summary"),
                    details: s("these are the details")
                }
            ),
            "HTTP OK - this is the summary\nthese are the details"
        );
    }

    #[test]
    fn test_merge_check_results_with_state_only() {
        let cr1 = CheckResult {
            state: State::Ok,
            summary: None,
            details: None,
        };
        let cr2 = CheckResult {
            state: State::Ok,
            summary: None,
            details: None,
        };
        let cr3 = CheckResult {
            state: State::Ok,
            summary: None,
            details: None,
        };
        assert_eq!(
            format!("{}", merge_check_results(&[cr1, cr2, cr3])),
            "HTTP OK"
        );
    }

    #[test]
    fn test_merge_check_results_with_summary() {
        let cr1 = CheckResult {
            state: State::Ok,
            summary: s("summary 1"),
            details: None,
        };
        let cr2 = CheckResult {
            state: State::Ok,
            summary: s("summary 2"),
            details: None,
        };
        let cr3 = CheckResult {
            state: State::Ok,
            summary: s("summary 3"),
            details: None,
        };
        assert_eq!(
            format!("{}", merge_check_results(&[cr1, cr2, cr3])),
            "HTTP OK - summary 1, summary 2, summary 3"
        );
    }

    #[test]
    fn test_merge_check_results_with_details() {
        let cr1 = CheckResult {
            state: State::Ok,
            summary: None,
            details: s("details 1"),
        };
        let cr2 = CheckResult {
            state: State::Ok,
            summary: None,
            details: s("details 2"),
        };
        let cr3 = CheckResult {
            state: State::Ok,
            summary: None,
            details: s("details 3"),
        };
        assert_eq!(
            format!("{}", merge_check_results(&[cr1, cr2, cr3])),
            "HTTP OK\ndetails 1\ndetails 2\ndetails 3"
        );
    }

    #[test]
    fn test_merge_check_results_with_summary_and_details() {
        let cr1 = CheckResult {
            state: State::Ok,
            summary: s("summary 1"),
            details: s("details 1"),
        };
        let cr2 = CheckResult {
            state: State::Ok,
            summary: s("summary 2"),
            details: s("details 2"),
        };
        let cr3 = CheckResult {
            state: State::Ok,
            summary: s("summary 3"),
            details: s("details 3"),
        };
        assert_eq!(
            format!("{}", merge_check_results(&[cr1, cr2, cr3])),
            "HTTP OK - summary 1, summary 2, summary 3\ndetails 1\ndetails 2\ndetails 3"
        );
    }
}
