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

pub fn check_validity(url: &str, x: &Asn1TimeRef, warn: &Asn1Time, crit: &Asn1Time) -> CheckResult {
    std::assert!(warn >= crit);

    if crit >= x {
        CheckResult {
            state: State::Crit,
            summary: format!(
                "Certificate '{}' expires in {} day(s) ({})",
                url,
                diff_to_now(x),
                x
            ),
        }
    } else if warn >= x {
        CheckResult {
            state: State::Warn,
            summary: format!(
                "Certificate '{}' expires in {} day(s) ({})",
                url,
                diff_to_now(x),
                x
            ),
        }
    } else {
        CheckResult {
            state: State::Ok,
            summary: format!("Certificate '{}' will expire on {}", url, x),
        }
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
                "example.com",
                days_from_now(30).as_ref(),
                &days_from_now(0),
                &days_from_now(0),
            )
            .state
                == State::Ok
        );
        assert!(
            check_validity(
                "example.com",
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
                "example.com",
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
                "example.com",
                days_from_now(3).as_ref(),
                &days_from_now(15),
                &days_from_now(7),
            )
            .state
                == State::Crit
        );
        assert!(
            check_validity(
                "example.com",
                days_from_now(3).as_ref(),
                &days_from_now(15),
                &days_from_now(15),
            )
            .state
                == State::Crit
        );
    }
}
