// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use http::{HeaderMap, HeaderValue};
use httpdate::parse_http_date;
use reqwest::{StatusCode, Version};
use std::fmt::{Display, Formatter, Result as FormatResult};
use std::time::{Duration, SystemTime};

use crate::http::{Body, OnRedirect, ProcessedResponse};

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
    pub body_string: Option<String>,
    pub header_strings: Vec<(String, String)>,
}

pub fn collect_response_checks(
    response: Result<(ProcessedResponse, Duration), reqwest::Error>,
    params: CheckParameters,
) -> Vec<CheckResult> {
    let (response, response_time) = match response {
        Ok(resp) => resp,
        Err(err) => return check_reqwest_error(err),
    };

    check_status(response.status, response.version, params.onredirect)
        .into_iter()
        .chain(check_headers(&response.headers, params.header_strings))
        .chain(check_body(
            response.body,
            params.page_size,
            params.body_string,
        ))
        .chain(check_response_time(
            response_time,
            params.response_time_levels,
            params.timeout,
        ))
        .chain(check_document_age(
            SystemTime::now(),
            response
                .headers
                .get("last-modified")
                .or(response.headers.get("date")),
            params.document_age_levels,
        ))
        .flatten()
        .collect()
}

fn check_reqwest_error(err: reqwest::Error) -> Vec<CheckResult> {
    if err.is_builder() {
        notice(State::Unknown, "Error building the request")
    } else if err.is_request() {
        notice(State::Unknown, "Error while sending request")
    } else if err.is_timeout() {
        notice(State::Crit, "timeout")
    } else if err.is_connect() {
        notice(State::Crit, "Failed to connect")
    } else if err.is_redirect() {
        // Hit one of max_redirs, sticky, stickyport
        notice(State::Crit, &err.to_string())
    } else {
        notice(State::Unknown, "Unknown error")
    }
    .into_iter()
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

fn check_headers(
    headers: &HeaderMap,
    search_strings: Vec<(String, String)>,
) -> Vec<Option<CheckResult>> {
    if search_strings.is_empty() {
        return vec![];
    };

    if contains_search_strings(headers, &search_strings) {
        vec![]
    } else {
        notice(
            State::Crit,
            "Specified strings not found in response headers",
        )
    }
}

fn contains_search_strings(headers: &HeaderMap, search_strings: &[(String, String)]) -> bool {
    let headers_as_strings: Vec<(&str, String)> = headers
        .iter()
        // The header name (coming from reqwest) is guaranteed to be ASCII, so we can have it as string.
        // The header value is only bytes in general. However, RFC 9110, section 5.5 tells us that it
        // should be ASCII and is allowed to be ISO-8859-1 (latin-1), so we decode it with latin-1.
        .map(|(hk, hv)| (hk.as_str(), latin1_to_string(hv.as_bytes())))
        .collect();

    search_strings.iter().all(|(search_key, search_value)| {
        headers_as_strings.iter().any(|(header_key, header_value)| {
            header_key.contains(search_key) && header_value.contains(search_value)
        })
    })
}

fn latin1_to_string(bytes: &[u8]) -> String {
    // latin-1 basically consists of the first two unicode blocks,
    // so it's straighyforward to interpret the u8 values as unicode values.
    bytes.iter().map(|&b| b as char).collect()
}

fn check_body<T: std::error::Error>(
    body: Option<Result<Body, T>>,
    page_size_limits: Option<Bounds<usize>>,
    body_string: Option<String>,
) -> Vec<Option<CheckResult>> {
    let Some(body) = body else {
        // We assume that a None-Body means that we didn't fetch it at all
        // and we don't want to perform checks on it.
        return vec![];
    };

    let Ok(body) = body else {
        return notice(State::Crit, "Error fetching the response body");
    };
    let mut ret = check_page_size(body.length, page_size_limits);

    if body_string.map_or(false, |string| !body.text.contains(&string)) {
        ret.append(&mut notice(
            State::Warn,
            "Specified string not found in response body",
        ));
    };
    ret
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
    now: SystemTime,
    age_header: Option<&HeaderValue>,
    document_age_levels: Option<UpperLevels<u64>>,
) -> Vec<Option<CheckResult>> {
    if document_age_levels.is_none() {
        return vec![];
    };

    let Some(age) = age_header else {
        return notice(State::Crit, "Can't determine document age");
    };
    let document_age_error = "Can't decode document age";
    let Ok(age) = age.to_str() else {
        return notice(State::Crit, document_age_error);
    };
    let Ok(age) = parse_http_date(age) else {
        return notice(State::Crit, document_age_error);
    };
    let Ok(age) = now.duration_since(age) else {
        return notice(State::Crit, document_age_error);
    };

    check_levels(
        "Document age",
        age.as_secs(),
        Some(" seconds"),
        &document_age_levels,
    )
}

#[cfg(test)]
mod test_check_headers {
    use http::HeaderName;

    use super::*;
    use std::collections::HashMap;
    use std::str::FromStr;

    #[test]
    fn test_no_search_strings() {
        assert!(
            check_headers(
                &(&HashMap::from([
                    ("key1".to_string(), "value1".to_string()),
                    ("key2".to_string(), "value2".to_string()),
                ]))
                    .try_into()
                    .unwrap(),
                vec![]
            ) == vec![]
        )
    }

    #[test]
    fn test_strings_found() {
        assert!(
            check_headers(
                &(&HashMap::from([
                    ("some_key1".to_string(), "some_value1".to_string()),
                    ("some_key2".to_string(), "some_value2".to_string()),
                    ("some_key3".to_string(), "some_value3".to_string()),
                ]))
                    .try_into()
                    .unwrap(),
                vec![
                    (("some_key1".to_string()), "value1".to_string()),
                    (String::new(), "value".to_string()),
                    ("some_key3".to_string(), String::new()),
                ]
            ) == vec![]
        )
    }

    #[test]
    fn test_strings_not_found() {
        assert!(
            check_headers(
                &(&HashMap::from([
                    ("some_key1".to_string(), "some_value1".to_string()),
                    ("some_key2".to_string(), "some_value2".to_string()),
                    ("some_key3".to_string(), "some_value3".to_string()),
                ]))
                    .try_into()
                    .unwrap(),
                vec![("key1".to_string(), "value2".to_string()),]
            ) == vec![
                CheckResult::summary(
                    State::Crit,
                    "Specified strings not found in response headers"
                ),
                CheckResult::details(
                    State::Crit,
                    "Specified strings not found in response headers"
                ),
            ]
        )
    }

    #[test]
    fn test_impossible_non_latin1() {
        assert!(
            check_headers(
                &(&HashMap::from([("some_key1".to_string(), "ßome_value1".to_string()),]))
                    .try_into()
                    .unwrap(),
                vec![("some_key1".to_string(), "ßome_value1".to_string()),]
            ) == vec![
                CheckResult::summary(
                    State::Crit,
                    "Specified strings not found in response headers"
                ),
                CheckResult::details(
                    State::Crit,
                    "Specified strings not found in response headers"
                ),
            ]
        )
    }

    #[test]
    fn test_decode_latin1() {
        let mut header_map = HeaderMap::new();
        header_map.append(
            HeaderName::from_str("some_key").unwrap(),
            HeaderValue::from_bytes(b"\xF6\xE4\xFC").unwrap(),
        );
        assert!(
            check_headers(
                &header_map,
                vec![("some_key".to_string(), "öäü".to_string()),]
            ) == vec![]
        )
    }
}
#[cfg(test)]
mod test_check_body {
    use super::*;
    use std::error::Error;
    use std::fmt::{Display, Formatter, Result};

    #[derive(Debug)]
    struct DummyError;

    impl Error for DummyError {}

    impl Display for DummyError {
        fn fmt(&self, f: &mut Formatter) -> Result {
            write!(f, "Error")
        }
    }

    #[test]
    fn test_no_body() {
        assert!(check_body::<DummyError>(None, None, None,) == vec![])
    }

    #[test]
    fn test_error_body() {
        assert!(
            check_body(Some(Err(DummyError {})), None, None)
                == vec![
                    CheckResult::summary(State::Crit, "Error fetching the response body"),
                    CheckResult::details(State::Crit, "Error fetching the response body"),
                ]
        );
    }

    #[test]
    fn test_all_ok() {
        assert!(
            check_body::<DummyError>(
                Some(Ok(Body {
                    text: "foobär".to_string(),
                    length: 7
                })),
                Some(Bounds::lower_upper(3, 10)),
                Some("foo".to_string()),
            ) == vec![
                CheckResult::details(State::Ok, "Page size: 7 Bytes"),
                CheckResult::metric("size", 7., Some('B'), None, Some(0.), None)
            ]
        );
    }

    #[test]
    fn test_string_not_found() {
        assert!(
            check_body::<DummyError>(
                Some(Ok(Body {
                    text: "foobär".to_string(),
                    length: 7
                })),
                Some(Bounds::lower_upper(3, 10)),
                Some("foobar".to_string()),
            ) == vec![
                CheckResult::details(State::Ok, "Page size: 7 Bytes"),
                CheckResult::metric("size", 7., Some('B'), None, Some(0.), None),
                CheckResult::summary(State::Warn, "Specified string not found in response body"),
                CheckResult::details(State::Warn, "Specified string not found in response body"),
            ]
        );
    }

    #[test]
    fn test_size_lower_out_of_bounds() {
        assert!(
            check_body::<DummyError>(
                Some(Ok(Body {
                    text: "don't care".to_string(),
                    length: 42
                })),
                Some(Bounds::lower(56)),
                None,
            ) == vec![
                CheckResult::summary(State::Warn, "Page size: 42 Bytes (warn below 56 Bytes)"),
                CheckResult::details(State::Warn, "Page size: 42 Bytes (warn below 56 Bytes)"),
                CheckResult::metric("size", 42., Some('B'), None, Some(0.), None)
            ]
        );
    }

    #[test]
    fn test_size_lower_and_higher_too_low() {
        assert!(
            check_body::<DummyError>(
                Some(Ok(Body {
                    text: "don't care".to_string(),
                    length: 42,
                })),
                Some(Bounds::lower_upper(56, 100)),
                None,
            ) == vec![
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
    fn test_size_lower_and_higher_too_high() {
        assert!(
            check_body::<DummyError>(
                Some(Ok(Body {
                    text: "don't care".to_string(),
                    length: 142,
                })),
                Some(Bounds::lower_upper(56, 100)),
                None,
            ) == vec![
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
mod test_check_document_age {
    use super::*;

    // All fixed timestamps at 00:00 UTC/GMT
    const UNIX_TIME_2023_11_16: u64 = 1700092800;
    const DATE_2023_11_15: &str = "Wed, 15 Nov 2023 00:00:00 GMT";
    const DATE_2023_11_17: &str = "Fri, 17 Nov 2023 00:00:00 GMT";
    const TWELVE_HOURS: u64 = 12 * 60 * 60;
    const THIRTYSIX_HOURS: u64 = 36 * 60 * 60;

    fn system_time(unix_timestamp: u64) -> SystemTime {
        SystemTime::UNIX_EPOCH + Duration::from_secs(unix_timestamp)
    }

    fn header_date(date: &str) -> HeaderValue {
        HeaderValue::from_str(date).unwrap()
    }

    #[test]
    fn test_no_levels() {
        assert!(
            check_document_age(
                system_time(UNIX_TIME_2023_11_16),
                Some(&header_date("We don't care")),
                None,
            ) == vec![]
        );
    }

    #[test]
    fn test_missing_header_value() {
        assert!(
            check_document_age(
                system_time(UNIX_TIME_2023_11_16),
                None,
                Some(UpperLevels::warn(THIRTYSIX_HOURS)),
            ) == vec![
                CheckResult::summary(State::Crit, "Can't determine document age"),
                CheckResult::details(State::Crit, "Can't determine document age")
            ]
        );
    }

    #[test]
    fn test_erroneous_date() {
        assert!(
            check_document_age(
                system_time(UNIX_TIME_2023_11_16),
                Some(&header_date("Something wrong")),
                Some(UpperLevels::warn(THIRTYSIX_HOURS)),
            ) == vec![
                CheckResult::summary(State::Crit, "Can't decode document age"),
                CheckResult::details(State::Crit, "Can't decode document age")
            ]
        );
    }

    #[test]
    fn test_date_in_future() {
        assert!(
            check_document_age(
                system_time(UNIX_TIME_2023_11_16),
                Some(&header_date(DATE_2023_11_17)),
                Some(UpperLevels::warn(THIRTYSIX_HOURS)),
            ) == vec![
                CheckResult::summary(State::Crit, "Can't decode document age"),
                CheckResult::details(State::Crit, "Can't decode document age")
            ]
        );
    }

    #[test]
    fn test_ok() {
        assert!(
            check_document_age(
                system_time(UNIX_TIME_2023_11_16),
                Some(&header_date(DATE_2023_11_15)),
                Some(UpperLevels::warn(THIRTYSIX_HOURS)),
            ) == vec![CheckResult::details(
                State::Ok,
                "Document age: 86400 seconds"
            )]
        );
    }

    #[test]
    fn test_warn() {
        assert!(
            check_document_age(
                system_time(UNIX_TIME_2023_11_16),
                Some(&header_date(DATE_2023_11_15)),
                Some(UpperLevels::warn(TWELVE_HOURS)),
            ) == vec![
                CheckResult::summary(
                    State::Warn,
                    "Document age: 86400 seconds (warn at 43200 seconds)"
                ),
                CheckResult::details(
                    State::Warn,
                    "Document age: 86400 seconds (warn at 43200 seconds)"
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
