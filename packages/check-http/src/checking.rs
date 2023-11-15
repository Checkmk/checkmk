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

pub struct Metric {
    pub name: String,
    pub value: f64,
    pub unit: Option<&'static str>,
    pub levels: Option<(f64, Option<f64>)>,
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
            Some((warn, opt_crit)) => (Some(warn), opt_crit),
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
}

pub fn notice(state: State, text: &str) -> Vec<Option<CheckResult>> {
    let details = CheckResult::details(state.clone(), text);
    match state {
        State::Ok => vec![details],
        _ => vec![CheckResult::summary(state.clone(), text), details],
    }
}

pub struct CheckParameters {
    pub onredirect: OnRedirect,
    pub page_size: Option<Bounds<usize>>,
    pub response_time_levels: Option<UpperLevels<f64>>,
    pub document_age_levels: Option<UpperLevels<u64>>,
}

pub fn collect_response_checks(
    response: ProcessedResponse,
    response_time: Duration,
    params: CheckParameters,
) -> Vec<CheckResult> {
    check_status(response.status, response.version, params.onredirect)
        .into_iter()
        .chain(check_body(response.body, params.page_size))
        .chain(vec![
            check_response_time(response_time, params.response_time_levels),
            check_document_age(&response.headers, params.document_age_levels),
        ])
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
        .and_then(|bounds| bounds.evaluate(&page_size, State::Warn))
        .unwrap_or(State::Ok);

    notice(state, &format!("Page size: {} bytes", page_size))
}

fn check_response_time(
    response_time: Duration,
    response_time_levels: Option<UpperLevels<f64>>,
) -> Option<CheckResult> {
    let state = response_time_levels
        .and_then(|levels| levels.evaluate(&response_time.as_secs_f64()))
        .unwrap_or(State::Ok);

    CheckResult::summary(
        state,
        &format!(
            "Response time: {}.{}s",
            response_time.as_secs(),
            response_time.subsec_millis()
        ),
    )
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
mod test_helper {
    use super::CheckResult;
    use crate::checking::State;

    pub fn has_state(crs: Vec<Option<CheckResult>>, state: State) -> bool {
        crs.iter().any(|cr| is_state(cr, &state))
    }

    pub fn is_state(cr: &Option<CheckResult>, state: &State) -> bool {
        let Some(cr) = cr else { return false };
        match cr {
            CheckResult::Details(ci) | CheckResult::Summary(ci) => &ci.state == state,
            _ => false,
        }
    }
}

#[cfg(test)]
mod test_check_page_size {
    use super::test_helper::has_state;
    use crate::checking::check_page_size;
    use crate::checking::Bounds;
    use crate::checking::State;

    #[test]
    fn test_without_bounds() {
        assert!(has_state(check_page_size(42, None), State::Ok));
    }

    #[test]
    fn test_lower_within_bounds() {
        assert!(has_state(
            check_page_size(42, Some(Bounds::lower(12))),
            State::Ok
        ));
    }

    #[test]
    fn test_lower_out_of_bounds() {
        assert!(has_state(
            check_page_size(42, Some(Bounds::lower(56))),
            State::Warn
        ));
    }

    #[test]
    fn test_lower_and_higher_within_bounds() {
        assert!(has_state(
            check_page_size(56, Some(Bounds::lower_upper(42, 100))),
            State::Ok
        ));
    }

    #[test]
    fn test_lower_and_higher_too_low() {
        assert!(has_state(
            check_page_size(42, Some(Bounds::lower_upper(56, 100))),
            State::Warn
        ));
    }

    #[test]
    fn test_lower_and_higher_too_high() {
        assert!(has_state(
            check_page_size(142, Some(Bounds::lower_upper(56, 100))),
            State::Warn
        ));
    }
}

#[cfg(test)]
mod test_check_response_time {
    use super::test_helper::is_state;
    use crate::checking::check_response_time;
    use crate::checking::{State, UpperLevels};
    use std::time::Duration;

    #[test]
    fn test_unbounded() {
        assert!(is_state(
            &check_response_time(Duration::new(5, 0), None),
            &State::Ok
        ),);
    }

    #[test]
    fn test_warn_within_bounds() {
        assert!(is_state(
            &check_response_time(Duration::new(5, 0), Some(UpperLevels::warn(6.))),
            &State::Ok
        ));
    }

    #[test]
    fn test_warn_is_warn() {
        assert!(is_state(
            &check_response_time(Duration::new(5, 0), Some(UpperLevels::warn(4.))),
            &State::Warn
        ));
    }

    #[test]
    fn test_warncrit_within_bounds() {
        assert!(is_state(
            &check_response_time(Duration::new(5, 0), Some(UpperLevels::warn_crit(6., 7.))),
            &State::Ok
        ));
    }

    #[test]
    fn test_warncrit_is_warn() {
        assert!(is_state(
            &check_response_time(Duration::new(5, 0), Some(UpperLevels::warn_crit(4., 6.))),
            &State::Warn
        ));
    }

    #[test]
    fn test_warncrit_is_crit() {
        assert!(is_state(
            &check_response_time(Duration::new(5, 0), Some(UpperLevels::warn_crit(2., 3.))),
            &State::Crit
        ));
    }
}
