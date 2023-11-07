// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use crate::cli::{DocumentAgeLevels, PageSizeLimits, ResponseTimeLevels};
use bytes::Bytes;
use http::HeaderMap;
use httpdate::parse_http_date;
use reqwest::{Error as ReqwestError, StatusCode, Version};
use std::fmt::{Display, Formatter, Result as FormatResult};
use std::time::{Duration, SystemTime};

use crate::cli::OnRedirect;

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

pub struct CheckResult {
    pub state: State,
    pub summary: String,
}

pub fn check_status(
    status: StatusCode,
    version: Version,
    onredirect: OnRedirect,
) -> Option<CheckResult> {
    let state = if status.is_client_error() {
        State::Warn
    } else if status.is_server_error() {
        State::Crit
    } else if status.is_redirection() {
        match onredirect {
            OnRedirect::Warning => State::Warn,
            OnRedirect::Critical => State::Crit,
            _ => State::Ok, // If we reach this point, the redirect is ok
        }
    } else {
        State::Ok
    };

    Some(CheckResult {
        state,
        summary: format!("{:?} {}", version, status),
    })
}

pub fn check_body(
    body: Option<Result<Bytes, ReqwestError>>,
    page_size_limits: Option<PageSizeLimits>,
) -> Option<CheckResult> {
    let body = body?;

    match body {
        Ok(bd) => Some(check_page_size(bd.len(), page_size_limits)),
        Err(_) => Some(CheckResult {
            state: State::Crit,
            summary: "Error fetching the reponse body".to_string(),
        }),
    }
}

pub fn check_page_size(page_size: usize, page_size_limits: Option<PageSizeLimits>) -> CheckResult {
    let state = match page_size_limits {
        Some((lower, _)) if page_size < lower => State::Warn,
        Some((_, Some(upper))) if page_size > upper => State::Warn,
        _ => State::Ok,
    };

    CheckResult {
        state,
        summary: format!("Page size: {} bytes", page_size),
    }
}

pub fn check_response_time(
    response_time: Duration,
    response_time_levels: Option<ResponseTimeLevels>,
) -> Option<CheckResult> {
    let state = match response_time_levels {
        Some((_, Some(crit))) if response_time.as_secs_f64() >= crit => State::Crit,
        Some((warn, _)) if response_time.as_secs_f64() >= warn => State::Warn,
        _ => State::Ok,
    };

    Some(CheckResult {
        state,
        summary: format!(
            "Response time: {}.{}s",
            response_time.as_secs(),
            response_time.subsec_millis()
        ),
    })
}

pub fn check_document_age(
    headers: &HeaderMap,
    document_age_levels: Option<DocumentAgeLevels>,
) -> Option<CheckResult> {
    let document_age_levels = document_age_levels?;

    let now = SystemTime::now();

    let age_header = headers.get("last-modified").or(headers.get("date"));
    let Some(document_age) = age_header else {
        return Some(CheckResult {
            state: State::Crit,
            summary: "Can't determine document age".to_string(),
        });
    };
    let Ok(Ok(age)) = document_age.to_str().map(parse_http_date) else {
        return Some(CheckResult {
            state: State::Crit,
            summary: "Can't decode document age".to_string(),
        });
    };

    //TODO(au): Specify "too old" in Output
    match document_age_levels {
        (_, Some(crit)) if now - Duration::from_secs(crit) > age => Some(CheckResult {
            state: State::Crit,
            summary: "Document age too old".to_string(),
        }),
        (warn, _) if now - Duration::from_secs(warn) > age => Some(CheckResult {
            state: State::Warn,
            summary: "Document age too old".to_string(),
        }),
        _ => None,
    }
}

#[cfg(test)]
mod test_check_page_size {
    use crate::checking::check_page_size;
    use crate::checking::State;

    #[test]
    fn test_without_limits() {
        assert_eq!(check_page_size(42, None).state, State::Ok);
    }

    #[test]
    fn test_lower_within_bounds() {
        assert_eq!(check_page_size(42, Some((12, None))).state, State::Ok);
    }

    #[test]
    fn test_lower_out_of_bounds() {
        assert_eq!(check_page_size(42, Some((56, None))).state, State::Warn);
    }

    #[test]
    fn test_lower_and_higher_within_bounds() {
        assert_eq!(check_page_size(56, Some((42, Some(100)))).state, State::Ok);
    }

    #[test]
    fn test_lower_and_higher_too_low() {
        assert_eq!(
            check_page_size(42, Some((56, Some(100)))).state,
            State::Warn
        );
    }

    #[test]
    fn test_lower_and_higher_too_high() {
        assert_eq!(
            check_page_size(142, Some((56, Some(100)))).state,
            State::Warn
        );
    }
}

#[cfg(test)]
mod test_check_response_time {
    use crate::checking::check_response_time;
    use crate::checking::State;
    use std::time::Duration;

    #[test]
    fn test_unbounded() {
        assert_eq!(
            check_response_time(Duration::new(5, 0), None)
                .unwrap()
                .state,
            State::Ok
        );
    }

    #[test]
    fn test_warn_within_bounds() {
        assert_eq!(
            check_response_time(
                Duration::new(5, 0),
                Some((Duration::new(6, 0).as_secs_f64(), None))
            )
            .unwrap()
            .state,
            State::Ok
        );
    }

    #[test]
    fn test_warn_is_warn() {
        assert_eq!(
            check_response_time(
                Duration::new(5, 0),
                Some((Duration::new(4, 0).as_secs_f64(), None))
            )
            .unwrap()
            .state,
            State::Warn
        );
    }

    #[test]
    fn test_warncrit_within_bounds() {
        assert_eq!(
            check_response_time(
                Duration::new(5, 0),
                Some((
                    Duration::new(6, 0).as_secs_f64(),
                    Some(Duration::new(7, 0).as_secs_f64())
                ))
            )
            .unwrap()
            .state,
            State::Ok
        );
    }

    #[test]
    fn test_warncrit_is_warn() {
        assert_eq!(
            check_response_time(
                Duration::new(5, 0),
                Some((
                    Duration::new(4, 0).as_secs_f64(),
                    Some(Duration::new(6, 0).as_secs_f64())
                ))
            )
            .unwrap()
            .state,
            State::Warn
        );
    }

    #[test]
    fn test_warncrit_is_crit() {
        assert_eq!(
            check_response_time(
                Duration::new(5, 0),
                Some((
                    Duration::new(2, 0).as_secs_f64(),
                    Some(Duration::new(3, 0).as_secs_f64())
                ))
            )
            .unwrap()
            .state,
            State::Crit
        );
    }
}
