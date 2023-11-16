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

#[cfg_attr(test, derive(PartialEq))]
pub struct UpperLevels<T> {
    pub warn: T,
    pub crit: Option<T>,
}

impl<T> UpperLevels<T>
where
    T: PartialOrd,
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

impl From<UpperLevels<u64>> for UpperLevels<f64> {
    fn from(value: UpperLevels<u64>) -> Self {
        Self {
            warn: value.warn as f64,
            crit: value.crit.map(|c| c as f64),
        }
    }
}

pub struct Bounds<T> {
    lower: T,
    upper: Option<T>,
}

impl<T> Bounds<T>
where
    T: PartialOrd,
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

#[derive(Clone, PartialEq, Eq, PartialOrd, Ord)]
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

#[cfg_attr(test, derive(PartialEq))]
pub struct Metric {
    pub name: String,
    pub value: f64,
    pub unit: Option<char>,
    pub levels: Option<UpperLevels<f64>>,
    pub lower: Option<f64>,
    pub upper: Option<f64>,
}

impl Display for Metric {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        fn write_optional<T: Display>(f: &mut Formatter, val: Option<T>) -> FormatResult {
            if let Some(val) = val {
                write!(f, "{}", val)?;
            };
            Ok(())
        }

        write!(f, "{}={}", self.name, self.value)?;
        write_optional(f, self.unit)?;
        let (warn, crit) = match self.levels {
            Some(UpperLevels { warn, crit }) => (Some(warn), crit),
            None => (None, None),
        };
        write!(f, ";")?;
        write_optional(f, warn)?;
        write!(f, ";")?;
        write_optional(f, crit)?;
        write!(f, ";")?;
        write_optional(f, self.lower)?;
        write!(f, ";")?;
        write_optional(f, self.upper)?;
        Ok(())
    }
}

#[cfg_attr(test, derive(Eq, PartialEq))]
pub struct CheckItem {
    pub state: State,
    text: String,
}

impl Display for CheckItem {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        write!(
            f,
            "{}{}",
            self.text,
            match self.state {
                State::Ok => "",
                State::Warn => " (!)",
                State::Crit => " (!!)",
                State::Unknown => " (?)",
            }
        )
    }
}

impl CheckItem {
    fn new(state: State, text: &str) -> Option<Self> {
        if text.is_empty() {
            return None;
        };

        Some(Self {
            state,
            text: text.to_string(),
        })
    }
}

#[cfg_attr(test, derive(PartialEq))]
pub enum CheckResult {
    Summary(CheckItem),
    Details(CheckItem),
    Metric(Metric),
}

impl CheckResult {
    pub fn summary(state: State, text: &str) -> Option<CheckResult> {
        CheckItem::new(state, text).map(Self::Summary)
    }

    pub fn details(state: State, text: &str) -> Option<CheckResult> {
        CheckItem::new(state, text).map(Self::Details)
    }

    pub fn metric(
        name: &str,
        value: f64,
        unit: Option<char>,
        levels: Option<UpperLevels<f64>>,
        lower: Option<f64>,
        upper: Option<f64>,
    ) -> Option<CheckResult> {
        Some(CheckResult::Metric(Metric {
            name: name.to_string(),
            value,
            unit,
            levels,
            lower,
            upper,
        }))
    }
}

pub fn notice(state: State, text: &str) -> Vec<Option<CheckResult>> {
    let details = CheckResult::details(state.clone(), text);
    match state {
        State::Ok => vec![details],
        _ => vec![CheckResult::summary(state.clone(), text), details],
    }
}

pub fn check_levels<T: Display + Copy + PartialOrd>(
    description: &str,
    value: T,
    unit: Option<&'static str>,
    upper_levels: &Option<UpperLevels<T>>,
) -> Vec<Option<CheckResult>> {
    let state = match &upper_levels {
        Some(ul) => ul.evaluate(&value).unwrap_or(State::Ok),
        None => State::Ok,
    };

    let opt_unit = unit.unwrap_or_default();
    let warn_crit_info = if let State::Warn | State::Crit = state {
        match &upper_levels {
            Some(UpperLevels { warn, crit: None }) => format!(" (warn at {}{})", warn, opt_unit),
            Some(UpperLevels {
                warn,
                crit: Some(crit),
            }) => format!(" (warn/crit at {}{}/{}{})", warn, opt_unit, crit, opt_unit),
            _ => "".to_string(),
        }
    } else {
        "".to_string()
    };

    notice(
        state,
        &format!("{}: {}{}{}", description, value, opt_unit, warn_crit_info),
    )
}

pub struct CheckParameters {
    pub onredirect: OnRedirect,
    pub page_size: Option<Bounds<usize>>,
    pub response_time_levels: Option<UpperLevels<f64>>,
    pub document_age_levels: Option<UpperLevels<u64>>,
    pub timeout: Duration,
}

pub fn collect_response_checks(
    response: ProcessedResponse,
    response_time: Duration,
    params: CheckParameters,
) -> Vec<CheckResult> {
    check_status(response.status, response.version, params.onredirect)
        .into_iter()
        .chain(check_body(response.body, params.page_size))
        .chain(check_response_time(
            response_time,
            params.response_time_levels,
            params.timeout,
        ))
        .chain(vec![check_document_age(
            &response.headers,
            params.document_age_levels,
        )])
        .flatten()
        .collect()
}

fn check_status(
    status: StatusCode,
    version: Version,
    onredirect: OnRedirect,
) -> Vec<Option<CheckResult>> {
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

    let text = format!("{:?} {}", version, status);
    vec![
        CheckResult::summary(state.clone(), &text),
        CheckResult::details(state, &text),
    ]
}

fn check_body(
    body: Option<Result<Bytes, ReqwestError>>,
    page_size_limits: Option<Bounds<usize>>,
) -> Vec<Option<CheckResult>> {
    let Some(body) = body else {
        return vec![];
    };

    match body {
        Ok(bd) => check_page_size(bd.len(), page_size_limits),
        Err(_) => notice(State::Crit, "Error fetching the reponse body"),
    }
}

fn check_page_size(
    page_size: usize,
    page_size_limits: Option<Bounds<usize>>,
) -> Vec<Option<CheckResult>> {
    let state = page_size_limits
        .as_ref()
        .and_then(|bounds| bounds.evaluate(&page_size, State::Warn))
        .unwrap_or(State::Ok);

    let bounds_info = if let State::Warn = state {
        match page_size_limits {
            Some(Bounds { lower, upper: None }) => format!(" (warn below {} Bytes)", lower),
            Some(Bounds {
                lower,
                upper: Some(upper),
            }) => format!(" (warn below/above {} Bytes/{} Bytes)", lower, upper),
            _ => "".to_string(),
        }
    } else {
        "".to_string()
    };

    let mut res = notice(
        state,
        &format!("Page size: {} Bytes{}", page_size, bounds_info),
    );
    res.push(CheckResult::metric(
        "size",
        page_size as f64,
        Some('B'),
        None,
        Some(0.),
        None,
    ));
    res
}

fn check_response_time(
    response_time: Duration,
    response_time_levels: Option<UpperLevels<f64>>,
    timeout: Duration,
) -> Vec<Option<CheckResult>> {
    let mut ret = check_levels(
        "Response time",
        response_time.as_secs_f64(),
        Some(" seconds"),
        &response_time_levels,
    );
    ret.push(CheckResult::metric(
        "time",
        response_time.as_secs_f64(),
        Some('s'),
        response_time_levels,
        Some(0.),
        Some(timeout.as_secs_f64()),
    ));
    ret
}

fn check_document_age(
    headers: &HeaderMap,
    document_age_levels: Option<UpperLevels<u64>>,
) -> Option<CheckResult> {
    let document_age_levels = document_age_levels?;

    let now = SystemTime::now();

    let cr_no_document_age = CheckResult::summary(State::Crit, "Can't determine document age");
    let cr_document_age_error = CheckResult::summary(State::Crit, "Can't decode document age");

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

    let state = document_age_levels.evaluate(&age.as_secs())?;

    //TODO(au): Specify "too old" in Output
    CheckResult::summary(state, "Document age too old")
}

#[cfg(test)]
mod test_check_page_size {
    use super::*;

    #[test]
    fn test_without_bounds() {
        assert!(
            check_page_size(42, None)
                == vec![
                    CheckResult::details(State::Ok, "Page size: 42 Bytes"),
                    CheckResult::metric("size", 42., Some('B'), None, Some(0.), None)
                ]
        )
    }

    #[test]
    fn test_lower_within_bounds() {
        assert!(
            check_page_size(42, Some(Bounds::lower(12)))
                == vec![
                    CheckResult::details(State::Ok, "Page size: 42 Bytes"),
                    CheckResult::metric("size", 42., Some('B'), None, Some(0.), None)
                ]
        );
    }

    #[test]
    fn test_lower_out_of_bounds() {
        assert!(
            check_page_size(42, Some(Bounds::lower(56)))
                == vec![
                    CheckResult::summary(State::Warn, "Page size: 42 Bytes (warn below 56 Bytes)"),
                    CheckResult::details(State::Warn, "Page size: 42 Bytes (warn below 56 Bytes)"),
                    CheckResult::metric("size", 42., Some('B'), None, Some(0.), None)
                ]
        );
    }

    #[test]
    fn test_lower_and_higher_too_low() {
        assert!(
            check_page_size(42, Some(Bounds::lower_upper(56, 100)))
                == vec![
                    CheckResult::summary(
                        State::Warn,
                        "Page size: 42 Bytes (warn below/above 56 Bytes/100 Bytes)"
                    ),
                    CheckResult::details(
                        State::Warn,
                        "Page size: 42 Bytes (warn below/above 56 Bytes/100 Bytes)"
                    ),
                    CheckResult::metric("size", 42., Some('B'), None, Some(0.), None)
                ]
        );
    }

    #[test]
    fn test_lower_and_higher_too_high() {
        assert!(
            check_page_size(142, Some(Bounds::lower_upper(56, 100)))
                == vec![
                    CheckResult::summary(
                        State::Warn,
                        "Page size: 142 Bytes (warn below/above 56 Bytes/100 Bytes)"
                    ),
                    CheckResult::details(
                        State::Warn,
                        "Page size: 142 Bytes (warn below/above 56 Bytes/100 Bytes)"
                    ),
                    CheckResult::metric("size", 142., Some('B'), None, Some(0.), None)
                ]
        );
    }
}

#[cfg(test)]
mod test_check_response_time {
    use super::*;
    use std::time::Duration;

    #[test]
    fn test_unbounded() {
        assert!(
            check_response_time(Duration::new(5, 0), None, Duration::from_secs(10))
                == vec![
                    CheckResult::details(State::Ok, "Response time: 5 seconds"),
                    CheckResult::metric("time", 5., Some('s'), None, Some(0.), Some(10.))
                ]
        );
    }

    #[test]
    fn test_warn_within_bounds() {
        assert!(
            check_response_time(
                Duration::new(5, 0),
                Some(UpperLevels::warn(6.)),
                Duration::from_secs(10)
            ) == vec![
                CheckResult::details(State::Ok, "Response time: 5 seconds"),
                CheckResult::metric(
                    "time",
                    5.,
                    Some('s'),
                    Some(UpperLevels::warn(6.)),
                    Some(0.),
                    Some(10.)
                )
            ]
        );
    }

    #[test]
    fn test_warn_is_warn() {
        assert!(
            check_response_time(
                Duration::new(5, 0),
                Some(UpperLevels::warn(4.)),
                Duration::from_secs(10)
            ) == vec![
                CheckResult::summary(State::Warn, "Response time: 5 seconds (warn at 4 seconds)"),
                CheckResult::details(State::Warn, "Response time: 5 seconds (warn at 4 seconds)"),
                CheckResult::metric(
                    "time",
                    5.,
                    Some('s'),
                    Some(UpperLevels::warn(4.)),
                    Some(0.),
                    Some(10.)
                )
            ]
        );
    }

    #[test]
    fn test_warncrit_within_bounds() {
        assert!(
            check_response_time(
                Duration::new(5, 0),
                Some(UpperLevels::warn_crit(6., 7.)),
                Duration::from_secs(10)
            ) == vec![
                CheckResult::details(State::Ok, "Response time: 5 seconds"),
                CheckResult::metric(
                    "time",
                    5.,
                    Some('s'),
                    Some(UpperLevels::warn_crit(6., 7.)),
                    Some(0.),
                    Some(10.)
                )
            ]
        );
    }

    #[test]
    fn test_warncrit_is_warn() {
        assert!(
            check_response_time(
                Duration::new(5, 0),
                Some(UpperLevels::warn_crit(4., 6.)),
                Duration::from_secs(10)
            ) == vec![
                CheckResult::summary(
                    State::Warn,
                    "Response time: 5 seconds (warn/crit at 4 seconds/6 seconds)"
                ),
                CheckResult::details(
                    State::Warn,
                    "Response time: 5 seconds (warn/crit at 4 seconds/6 seconds)"
                ),
                CheckResult::metric(
                    "time",
                    5.,
                    Some('s'),
                    Some(UpperLevels::warn_crit(4., 6.)),
                    Some(0.),
                    Some(10.)
                )
            ]
        );
    }

    #[test]
    fn test_warncrit_is_crit() {
        assert!(
            check_response_time(
                Duration::new(5, 0),
                Some(UpperLevels::warn_crit(2., 3.)),
                Duration::from_secs(10)
            ) == vec![
                CheckResult::summary(
                    State::Crit,
                    "Response time: 5 seconds (warn/crit at 2 seconds/3 seconds)"
                ),
                CheckResult::details(
                    State::Crit,
                    "Response time: 5 seconds (warn/crit at 2 seconds/3 seconds)"
                ),
                CheckResult::metric(
                    "time",
                    5.,
                    Some('s'),
                    Some(UpperLevels::warn_crit(2., 3.)),
                    Some(0.),
                    Some(10.)
                )
            ]
        );
    }
}

#[cfg(test)]
mod test_check_levels {
    use super::*;

    #[test]
    fn test_basic() {
        assert!(
            check_levels("test", 0, None, &None)
                == vec![CheckResult::details(State::Ok, "test: 0")]
        )
    }

    #[test]
    fn test_warn_level_inactive() {
        assert!(
            check_levels("test", 0, Some(" Bytes"), &Some(UpperLevels::warn(10)))
                == vec![CheckResult::details(State::Ok, "test: 0 Bytes")]
        )
    }

    #[test]
    fn test_warn_level_active() {
        assert!(
            check_levels("test", 20, Some("%"), &Some(UpperLevels::warn(10)))
                == vec![
                    CheckResult::summary(State::Warn, "test: 20% (warn at 10%)"),
                    CheckResult::details(State::Warn, "test: 20% (warn at 10%)")
                ]
        )
    }

    #[test]
    fn test_warn_crit_levels() {
        assert!(
            check_levels("test", 20, Some("%"), &Some(UpperLevels::warn_crit(10, 20)))
                == vec![
                    CheckResult::summary(State::Crit, "test: 20% (warn/crit at 10%/20%)"),
                    CheckResult::details(State::Crit, "test: 20% (warn/crit at 10%/20%)")
                ]
        )
    }
}
