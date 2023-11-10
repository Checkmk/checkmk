// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use bytes::Bytes;
use http::HeaderMap;
use httpdate::parse_http_date;
use reqwest::{Error as ReqwestError, StatusCode, Version};
use std::fmt::{Display, Formatter, Result as FormatResult};
use std::time::{Duration, SystemTime};

use crate::connection::OnRedirect;
use crate::http::ProcessedResponse;

// check_http allows specification of
// * no levels/bounds
// * warn/lower
// * warn/lower and crit/upper
// So we're modelling exactly this.

pub struct UpperLevels<T> {
    warn: T,
    crit: Option<T>,
}

impl<T> UpperLevels<T>
where
    T: Ord + PartialOrd,
{
    pub fn warn(warn: T) -> Self {
        Self { warn, crit: None }
    }

    pub fn warn_crit(warn: T, crit: T) -> Self {
        Self {
            warn,
            crit: Some(crit),
        }
    }

    pub fn evaluate(&self, value: &T) -> Option<State> {
        match self {
            Self {
                warn: _,
                crit: Some(crit),
            } if value >= crit => Some(State::Crit),
            Self { warn, crit: _ } if value >= warn => Some(State::Warn),
            _ => None,
        }
    }
}

pub struct Bounds<T> {
    lower: T,
    upper: Option<T>,
}

impl<T> Bounds<T>
where
    T: Ord + PartialOrd,
{
    pub fn lower(lower: T) -> Self {
        Self { lower, upper: None }
    }

    pub fn lower_upper(lower: T, upper: T) -> Self {
        Self {
            lower,
            upper: Some(upper),
        }
    }

    pub fn evaluate(&self, value: &T, severity: State) -> Option<State> {
        match self {
            Self {
                lower: _,
                upper: Some(upper),
            } if value > upper => Some(severity),
            Self { lower, upper: _ } if value < lower => Some(severity),
            _ => None,
        }
    }
}

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

pub struct CheckParameters {
    pub onredirect: OnRedirect,
    pub page_size: Option<Bounds<usize>>,
    pub response_time_levels: Option<UpperLevels<Duration>>,
    pub document_age_levels: Option<UpperLevels<Duration>>,
}

pub fn collect_response_checks(
    response: ProcessedResponse,
    response_time: Duration,
    params: CheckParameters,
) -> Vec<CheckResult> {
    vec![
        check_status(response.status, response.version, params.onredirect),
        check_body(response.body, params.page_size),
        check_response_time(response_time, params.response_time_levels),
        check_document_age(&response.headers, params.document_age_levels),
    ]
    .into_iter()
    .flatten()
    .collect()
}

fn check_status(
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

fn check_body(
    body: Option<Result<Bytes, ReqwestError>>,
    page_size_limits: Option<Bounds<usize>>,
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

fn check_page_size(page_size: usize, page_size_limits: Option<Bounds<usize>>) -> CheckResult {
    let state = page_size_limits
        .and_then(|bounds| bounds.evaluate(&page_size, State::Warn))
        .unwrap_or(State::Ok);

    CheckResult {
        state,
        summary: format!("Page size: {} bytes", page_size),
    }
}

fn check_response_time(
    response_time: Duration,
    response_time_levels: Option<UpperLevels<Duration>>,
) -> Option<CheckResult> {
    let state = response_time_levels
        .and_then(|levels| levels.evaluate(&response_time))
        .unwrap_or(State::Ok);

    Some(CheckResult {
        state,
        summary: format!(
            "Response time: {}.{}s",
            response_time.as_secs(),
            response_time.subsec_millis()
        ),
    })
}

fn check_document_age(
    headers: &HeaderMap,
    document_age_levels: Option<UpperLevels<Duration>>,
) -> Option<CheckResult> {
    let document_age_levels = document_age_levels?;

    let now = SystemTime::now();

    let cr_no_document_age = Some(CheckResult {
        state: State::Crit,
        summary: "Can't determine document age".to_string(),
    });
    let cr_document_age_error = Some(CheckResult {
        state: State::Crit,
        summary: "Can't decode document age".to_string(),
    });

    let age_header = headers.get("last-modified").or(headers.get("date"));
    let Some(age) = age_header else {
        return cr_no_document_age;
    };
    let Ok(age) = age.to_str() else {
        return cr_document_age_error;
    };
    let Ok(age) = parse_http_date(age) else {
        return cr_document_age_error;
    };
    let Ok(age) = now.duration_since(age) else {
        return cr_document_age_error;
    };

    let state = document_age_levels.evaluate(&age)?;

    //TODO(au): Specify "too old" in Output
    Some(CheckResult {
        state,
        summary: "Document age too old".to_string(),
    })
}

#[cfg(test)]
mod test_check_page_size {
    use crate::checking::check_page_size;
    use crate::checking::Bounds;
    use crate::checking::State;

    #[test]
    fn test_without_bounds() {
        assert_eq!(check_page_size(42, None).state, State::Ok);
    }

    #[test]
    fn test_lower_within_bounds() {
        assert_eq!(
            check_page_size(42, Some(Bounds::lower(12))).state,
            State::Ok
        );
    }

    #[test]
    fn test_lower_out_of_bounds() {
        assert_eq!(
            check_page_size(42, Some(Bounds::lower(56))).state,
            State::Warn
        );
    }

    #[test]
    fn test_lower_and_higher_within_bounds() {
        assert_eq!(
            check_page_size(56, Some(Bounds::lower_upper(42, 100))).state,
            State::Ok
        );
    }

    #[test]
    fn test_lower_and_higher_too_low() {
        assert_eq!(
            check_page_size(42, Some(Bounds::lower_upper(56, 100))).state,
            State::Warn
        );
    }

    #[test]
    fn test_lower_and_higher_too_high() {
        assert_eq!(
            check_page_size(142, Some(Bounds::lower_upper(56, 100))).state,
            State::Warn
        );
    }
}

#[cfg(test)]
mod test_check_response_time {
    use crate::checking::check_response_time;
    use crate::checking::{State, UpperLevels};
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
                Some(UpperLevels::warn(Duration::new(6, 0)))
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
                Some(UpperLevels::warn(Duration::new(4, 0)))
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
                Some(UpperLevels::warn_crit(
                    Duration::new(6, 0),
                    Duration::new(7, 0)
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
                Some(UpperLevels::warn_crit(
                    Duration::new(4, 0),
                    Duration::new(6, 0)
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
                Some(UpperLevels::warn_crit(
                    Duration::new(2, 0),
                    Duration::new(3, 0)
                ))
            )
            .unwrap()
            .state,
            State::Crit
        );
    }
}
