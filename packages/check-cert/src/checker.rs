// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use openssl::asn1::{Asn1Time, Asn1TimeRef};
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

pub struct CheckResult {
    pub state: State,
    pub summary: String,
}

impl CheckResult {
    pub fn new(state: State, summary: String) -> Self {
        Self { state, summary }
    }

    pub fn ok(summary: String) -> Self {
        Self {
            state: State::Ok,
            summary,
        }
    }

    pub fn warn(summary: String) -> Self {
        Self {
            state: State::Warn,
            summary,
        }
    }

    pub fn crit(summary: String) -> Self {
        Self {
            state: State::Crit,
            summary,
        }
    }

    pub fn unknown(summary: String) -> Self {
        Self {
            state: State::Unknown,
            summary,
        }
    }
}

impl Default for CheckResult {
    fn default() -> Self {
        Self {
            state: State::Ok,
            summary: String::from(""),
        }
    }
}

impl Display for CheckResult {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        write!(
            f,
            "{}{}",
            self.summary,
            match self.state {
                State::Ok => "",
                State::Warn => " (!)",
                State::Crit => " (!!)",
                State::Unknown => " (?)",
            }
        )
    }
}

fn diff_to_now(x: &Asn1TimeRef) -> i32 {
    let exp = Asn1Time::days_from_now(0).unwrap().diff(x).unwrap();
    exp.days
}

pub fn check_validity(x: &Asn1TimeRef, warn: &Asn1Time, crit: &Asn1Time) -> CheckResult {
    std::assert!(warn >= crit);

    if crit >= x {
        CheckResult::crit(format!(
            "Certificate expires in {} day(s) ({})",
            diff_to_now(x),
            x
        ))
    } else if warn >= x {
        CheckResult::warn(format!(
            "Certificate expires in {} day(s) ({})",
            diff_to_now(x),
            x
        ))
    } else {
        CheckResult::ok(format!("Certificate will expire on {}", x))
    }
}

#[cfg(test)]
mod test_diff_to_now {
    use super::diff_to_now;
    use openssl::asn1::Asn1Time;

    fn days_from_now(days: u32) -> Asn1Time {
        Asn1Time::days_from_now(days).unwrap()
    }

    #[test]
    fn test_diff_to_today() {
        assert!(diff_to_now(days_from_now(0).as_ref()) == 0);
    }

    #[test]
    fn test_diff_to_tomorrow() {
        assert!(diff_to_now(days_from_now(1).as_ref()) == 1);
    }
}

#[cfg(test)]
mod test_check_validity {
    use super::{check_validity, State};
    use openssl::asn1::Asn1Time;

    fn days_from_now(days: u32) -> Asn1Time {
        Asn1Time::days_from_now(days).unwrap()
    }

    #[test]
    fn test_check_validity_ok() {
        assert!(
            check_validity(
                days_from_now(30).as_ref(),
                &days_from_now(0),
                &days_from_now(0),
            )
            .state
                == State::Ok
        );
        assert!(
            check_validity(
                days_from_now(30).as_ref(),
                &days_from_now(15),
                &days_from_now(7),
            )
            .state
                == State::Ok
        );
    }

    #[test]
    fn test_check_validity_warn() {
        assert!(
            check_validity(
                days_from_now(10).as_ref(),
                &days_from_now(15),
                &days_from_now(7),
            )
            .state
                == State::Warn
        );
    }

    #[test]
    fn test_check_validity_crit() {
        assert!(
            check_validity(
                days_from_now(3).as_ref(),
                &days_from_now(15),
                &days_from_now(7),
            )
            .state
                == State::Crit
        );
        assert!(
            check_validity(
                days_from_now(3).as_ref(),
                &days_from_now(15),
                &days_from_now(15),
            )
            .state
                == State::Crit
        );
    }
}
