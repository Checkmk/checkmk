// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use httpdate::parse_http_date;
use regex::Regex;
use reqwest::{
    header::{HeaderMap, HeaderValue},
    tls::TlsInfo,
    Method, StatusCode, Url, Version,
};
use std::{
    error::Error,
    time::{Duration, SystemTime},
};
use x509_parser::{certificate::X509Certificate, prelude::FromDer};

use crate::checking_types::{
    check_lower_levels, check_upper_levels, notice, Bounds, CheckResult, LowerLevels, State,
    UpperLevels,
};
use crate::http::{Body, OnRedirect, ProcessedResponse};

pub struct RequestInformation {
    pub request_url: Url,
    pub method: Method,
    pub user_agent: String,
    pub onredirect: OnRedirect,
    pub timeout: Duration,
    pub server: Option<String>,
}

pub struct CheckParameters {
    pub status_code: Vec<StatusCode>,
    pub page_size: Option<Bounds<usize>>,
    pub response_time_levels: Option<UpperLevels<f64>>,
    pub document_age_levels: Option<UpperLevels<u64>>,
    pub body_matchers: Vec<TextMatcher>,
    pub header_matchers: Vec<(TextMatcher, TextMatcher)>,
    pub certificate_levels: Option<LowerLevels<u64>>,
    pub disable_certificate_verification: bool,
    pub content_search_fail_state: State,
}

pub enum TextMatcher {
    Exact(String),
    Contains(String),
    Regex { regex: Regex, expectation: bool },
}

impl TextMatcher {
    pub fn match_on(&self, text: &str) -> bool {
        match self {
            Self::Contains(string) => text.contains(string),
            Self::Exact(string) => text == string,
            Self::Regex { regex, expectation } => &regex.is_match(text) == expectation,
        }
    }
}

impl TextMatcher {
    pub fn from_regex(regex: Regex, expectation: bool) -> Self {
        Self::Regex { regex, expectation }
    }

    pub fn inner(&self) -> &str {
        match self {
            Self::Contains(string) | Self::Exact(string) => string.as_str(),
            Self::Regex {
                regex,
                expectation: _,
            } => regex.as_str(),
        }
    }
}

pub fn collect_response_checks(
    response: Result<ProcessedResponse, reqwest::Error>,
    request_information: RequestInformation,
    params: CheckParameters,
) -> Vec<CheckResult> {
    let response = match response {
        Ok(resp) => resp,
        Err(err) => return check_reqwest_error(err, request_information),
    };

    let (body, body_check_results) = check_body(response.body);

    check_urls(
        request_information.request_url,
        response.final_url,
        request_information.server,
    )
    .into_iter()
    .chain(check_redirect(
        response.status,
        request_information.onredirect,
        response.redirect_target,
    ))
    .chain(check_method(request_information.method))
    .chain(check_version(response.version))
    .chain(check_status(response.status, params.status_code))
    .chain(check_response_time(
        response.time_headers,
        response.time_body,
        params.response_time_levels,
        request_information.timeout,
    ))
    .chain(body_check_results)
    .chain(check_page_age(
        SystemTime::now(),
        response
            .headers
            .get("last-modified")
            .or(response.headers.get("date")),
        params.document_age_levels,
    ))
    .chain(check_page_size(body.as_ref(), params.page_size))
    .chain(check_certificate(
        response.tls_info,
        params.certificate_levels,
        params.disable_certificate_verification,
    ))
    .chain(check_user_agent(request_information.user_agent))
    .chain(check_headers(
        &response.headers,
        params.header_matchers,
        params.content_search_fail_state.clone(),
    ))
    .chain(check_body_matching(
        body.as_ref(),
        params.body_matchers,
        params.content_search_fail_state,
    ))
    .flatten()
    .collect()
}

fn check_urls(url: Url, final_url: Url, server: Option<String>) -> Vec<Option<CheckResult>> {
    let mut results = vec![
        CheckResult::summary(State::Ok, url.as_str()),
        CheckResult::details(State::Ok, &format!("URL to test: {}", url)),
    ];
    // If we end up with a different final_url, we obviously got redirected.
    // Since we didn't run into an error, the redirect must be OK.

    if let Some(server) = server {
        results.push(CheckResult::details(
            State::Ok,
            &format!("Connected to server: {}", server),
        ));
    }

    if url != final_url {
        results.push(CheckResult::details(
            State::Ok,
            &format!("Followed redirect to: {}", final_url),
        ));
    }
    results
}

fn check_reqwest_error(
    err: reqwest::Error,
    request_information: RequestInformation,
) -> Vec<CheckResult> {
    let mut source = err.source();
    let mut causes = Vec::new();
    while let Some(s) = source {
        causes.push(s.to_string());
        source = s.source();
    }
    let cause = match causes.is_empty() {
        true => String::new(),
        false => causes.join(": "),
    };

    if err.is_timeout() {
        notice(
            State::Crit,
            &format!(
                "Could not connect to {} within specified timeout: {}",
                request_information.request_url,
                render_seconds_with_ms(&request_information.timeout.as_secs_f64()),
            ),
        )
    } else if err.is_connect()
        // Hit one of max_redirs, sticky, stickyport
        | err.is_redirect()
    {
        notice(
            State::Crit,
            &(err.to_string() + ": " + &cause).replace('\n', " - "),
        )
    } else {
        // The errors coming from reqwest are usually short and don't contain
        // newlines, but we want to be safe.
        notice(
            State::Unknown,
            &(err.to_string() + ": " + &cause).replace('\n', " - "),
        )
    }
    .into_iter()
    .flatten()
    .collect()
}

fn check_method(method: Method) -> Vec<Option<CheckResult>> {
    vec![CheckResult::details(
        State::Ok,
        &format!("Method: {}", method),
    )]
}

fn check_version(version: Version) -> Vec<Option<CheckResult>> {
    vec![
        CheckResult::summary(State::Ok, &format!("Version: {:?}", version)),
        CheckResult::details(State::Ok, &format!("Version: {:?}", version)),
    ]
}

fn check_status(
    status: StatusCode,
    accepted_statuses: Vec<StatusCode>,
) -> Vec<Option<CheckResult>> {
    let (state, status_text) = if accepted_statuses.is_empty() {
        (
            if status.is_client_error() {
                State::Warn
            } else if status.is_server_error() {
                State::Crit
            } else {
                State::Ok
            },
            String::new(),
        )
    } else if accepted_statuses.contains(&status) {
        (State::Ok, String::new())
    } else {
        (
            State::Crit,
            if accepted_statuses.len() == 1 {
                format!(" (expected {})", accepted_statuses[0])
            } else {
                format!(
                    " (expected one of [{}])",
                    accepted_statuses
                        .iter()
                        .map(|st| st.as_u16().to_string())
                        .collect::<Vec<_>>()
                        .join(" ")
                )
            },
        )
    };

    let text = format!("Status: {}{}", status, status_text);
    vec![
        CheckResult::summary(state.clone(), &text),
        CheckResult::details(state, &text),
    ]
}

fn check_redirect(
    status: StatusCode,
    onredirect: OnRedirect,
    redirect_target: Option<Url>,
) -> Vec<Option<CheckResult>> {
    if !status.is_redirection() {
        return vec![];
    };
    let text = redirect_target
        .map(|url| format!("Stopped on redirect to: {}", url))
        .unwrap_or("Stopped on redirect".to_string());
    match onredirect {
        OnRedirect::Ok => vec![CheckResult::details(State::Ok, &text)],
        OnRedirect::Warning => notice(State::Warn, &text),
        OnRedirect::Critical => notice(State::Crit, &text),
        OnRedirect::Sticky => notice(State::Warn, &format!("{} (changed IP)", text)),
        OnRedirect::Stickyport => notice(State::Warn, &format!("{} (changed IP/port)", text)),
        // The only possibility for status.is_redirection() to become true is that
        // we configured one of the above policies. Otherwise, we would have
        // followed the redirect or ran into an error.
        // Hence, this will never match.
        OnRedirect::Follow => vec![],
    }
}

fn check_headers(
    headers: &HeaderMap,
    matchers: Vec<(TextMatcher, TextMatcher)>,
    fail_state: State,
) -> Vec<Option<CheckResult>> {
    if matchers.is_empty() {
        return vec![];
    };

    let headers_as_strings: Vec<(&str, String)> = headers
        .iter()
        // The header name (coming from reqwest) is guaranteed to be ASCII, so we can have it as string.
        // The header value is only bytes in general. However, RFC 9110, section 5.5 tells us that it
        // should be ASCII and is allowed to be ISO-8859-1 (latin-1), so we decode it with latin-1.
        .map(|(hk, hv)| (hk.as_str(), latin1_to_string(hv.as_bytes())))
        .collect();

    matchers
        .iter()
        .flat_map(|(name_matcher, value_matcher)| {
            let (match_text, positive_result_text, negative_result_text, expectation) =
                match name_matcher {
                    // We expect name and value matchers to be of the same variant,
                    // so we can match on name_matcher only.
                    TextMatcher::Regex {
                        regex: _,
                        expectation,
                    } => {
                        if *expectation {
                            (
                                "Expected regex in HTTP headers",
                                "match found",
                                "no match found",
                                *expectation,
                            )
                        } else {
                            (
                                "Not expected regex in HTTP headers",
                                "no match found",
                                "match found",
                                *expectation,
                            )
                        }
                    }
                    TextMatcher::Contains(_) | TextMatcher::Exact(_) => {
                        ("Expected HTTP header", "found", "not found", true)
                    }
                };

            let header_regex = format!("{}:{}", name_matcher.inner(), value_matcher.inner());

            if match_on_headers(
                &headers_as_strings,
                name_matcher,
                value_matcher,
                expectation,
            ) {
                vec![CheckResult::details(
                    State::Ok,
                    &format!(
                        "{}: {} ({})",
                        match_text, header_regex, positive_result_text
                    ),
                )]
            } else {
                notice(
                    fail_state.clone(),
                    &format!(
                        "{}: {} ({})",
                        match_text, header_regex, negative_result_text
                    ),
                )
            }
        })
        .collect::<Vec<_>>()
}

fn match_on_headers(
    string_headers: &[(&str, String)],
    name_matcher: &TextMatcher,
    value_matcher: &TextMatcher,
    first_match_ok: bool,
) -> bool {
    if first_match_ok {
        string_headers.iter().any(|(header_key, header_value)| {
            name_matcher.match_on(header_key) && value_matcher.match_on(header_value)
        })
    } else {
        string_headers.iter().all(|(header_key, header_value)| {
            name_matcher.match_on(header_key) && value_matcher.match_on(header_value)
        })
    }
}
fn latin1_to_string(bytes: &[u8]) -> String {
    // latin-1 basically consists of the first two unicode blocks,
    // so it's straighyforward to interpret the u8 values as unicode values.
    bytes.iter().map(|&b| b as char).collect()
}

fn check_body<T: std::error::Error>(
    body: Option<Result<Body, T>>,
) -> (Option<Body>, Vec<Option<CheckResult>>) {
    let Some(body) = body else {
        // We assume that a None-Body means that we didn't fetch it at all
        // and we don't want to perform checks on it.
        return (None, vec![]);
    };

    let Ok(body) = body else {
        return (
            None,
            notice(State::Crit, "Error fetching the response body"),
        );
    };

    (Some(body), vec![])
}

fn check_body_matching(
    body: Option<&Body>,
    matcher: Vec<TextMatcher>,
    fail_state: State,
) -> Vec<Option<CheckResult>> {
    let Some(body) = body else {
        return vec![];
    };

    matcher
        .iter()
        .flat_map(|m| {
            let (match_text, positive_result_text, negative_result_text) = match m {
                TextMatcher::Regex {
                    regex: _,
                    expectation,
                } => {
                    if *expectation {
                        ("Expected regex in body", "match found", "no match found")
                    } else {
                        (
                            "Not expected regex in body",
                            "no match found",
                            "match found",
                        )
                    }
                }
                TextMatcher::Contains(_) | TextMatcher::Exact(_) => {
                    ("Expected string in body", "found", "not found")
                }
            };

            if m.match_on(&body.text) {
                vec![CheckResult::details(
                    State::Ok,
                    &format!("{}: {} ({})", match_text, m.inner(), positive_result_text),
                )]
            } else {
                notice(
                    fail_state.clone(),
                    &format!("{}: {} ({})", match_text, m.inner(), negative_result_text),
                )
            }
        })
        .collect::<Vec<_>>()
}

fn check_page_size(
    body: Option<&Body>,
    page_size_limits: Option<Bounds<usize>>,
) -> Vec<Option<CheckResult>> {
    let Some(body) = body else {
        return vec![];
    };

    let state = page_size_limits
        .as_ref()
        .and_then(|bounds| bounds.evaluate(&body.length, State::Warn))
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
        &format!("Page size: {} Bytes{}", body.length, bounds_info),
    );
    res.push(CheckResult::metric(
        "response_size",
        body.length as f64,
        Some('B'),
        None,
        Some(0.),
        None,
    ));
    res
}

fn check_response_time(
    time_header: Duration,
    time_body: Option<Duration>,
    response_time_levels: Option<UpperLevels<f64>>,
    timeout: Duration,
) -> Vec<Option<CheckResult>> {
    let response_time = if let Some(time_body) = time_body {
        time_header + time_body
    } else {
        time_header
    };

    let mut ret = check_upper_levels(
        "Response time",
        response_time.as_secs_f64(),
        render_seconds_with_ms,
        &response_time_levels,
    );
    ret.push(CheckResult::metric(
        "response_time",
        response_time.as_secs_f64(),
        Some('s'),
        response_time_levels,
        Some(0.),
        Some(timeout.as_secs_f64()),
    ));
    ret.push(CheckResult::metric(
        "time_http_headers",
        time_header.as_secs_f64(),
        Some('s'),
        None,
        None,
        None,
    ));
    if let Some(time_body) = time_body {
        ret.push(CheckResult::metric(
            "time_http_body",
            time_body.as_secs_f64(),
            Some('s'),
            None,
            None,
            None,
        ))
    };
    ret
}

fn check_page_age(
    now: SystemTime,
    age_header: Option<&HeaderValue>,
    page_age_levels: Option<UpperLevels<u64>>,
) -> Vec<Option<CheckResult>> {
    if page_age_levels.is_none() {
        return vec![];
    };

    let Some(age) = age_header else {
        return notice(State::Crit, "Can't determine page age");
    };
    let page_age_error = "Can't decode page age";
    let Ok(age) = age.to_str() else {
        return notice(State::Crit, page_age_error);
    };
    let Ok(age) = parse_http_date(age) else {
        return notice(State::Crit, page_age_error);
    };
    let Ok(age) = now.duration_since(age) else {
        return notice(State::Crit, page_age_error);
    };

    check_upper_levels(
        "Page age",
        age.as_secs(),
        |secs| format!("{} seconds", secs),
        &page_age_levels,
    )
}

// TODO(au): Tests
fn check_certificate(
    tls_info: Option<TlsInfo>,
    certificate_levels: Option<LowerLevels<u64>>,
    disable_certificate_verification: bool,
) -> Vec<Option<CheckResult>> {
    if disable_certificate_verification {
        return vec![CheckResult::details(
            State::Ok,
            "Server certificate validity: ignored",
        )];
    }

    let Some(cert) = tls_info.as_ref().and_then(|t| t.peer_certificate()) else {
        // If the outer tlsinfo is None, we didn't fetch it -> OK
        // If the inner peer cert is None, there is no certificate and we're talking plain HTTP.
        // Otherwise the TLS handshake would already have failed.
        return vec![];
    };

    let Ok((_, cert)) = X509Certificate::from_der(cert) else {
        return notice(State::Unknown, "Unable to parse server certificate");
    };
    let Some(validity) = cert.validity().time_to_expiration() else {
        return notice(State::Crit, "Invalid server certificate");
    };

    check_lower_levels(
        "Server certificate validity",
        validity.whole_days().max(0).unsigned_abs(),
        |days| format!("{} days", days),
        &certificate_levels,
    )
}

fn check_user_agent(user_agent: String) -> Vec<Option<CheckResult>> {
    vec![CheckResult::details(
        State::Ok,
        &format!("User agent: {}", user_agent),
    )]
}

fn render_seconds_with_ms(val: &f64) -> String {
    // Format to three digits to get a sense of milliseconds,
    // but crop unnecessary trailing zeros/decimal point
    format!(
        "{} seconds",
        format!("{:.3}", val)
            .trim_end_matches('0')
            .trim_end_matches('.')
    )
}

#[cfg(test)]
mod test_check_urls {

    use super::*;
    use reqwest::Url;

    #[test]
    fn test_no_redirect() {
        assert_eq!(
            check_urls(
                Url::parse("https://foo.bar").unwrap(),
                Url::parse("https://foo.bar/").unwrap(),
                None,
            ),
            vec![
                CheckResult::summary(State::Ok, "https://foo.bar/"),
                CheckResult::details(State::Ok, "URL to test: https://foo.bar/"),
            ]
        )
    }

    #[test]
    fn test_redirect() {
        assert_eq!(
            check_urls(
                Url::parse("https://foo.bar").unwrap(),
                Url::parse("https://foo.bar/baz").unwrap(),
                None,
            ),
            vec![
                CheckResult::summary(State::Ok, "https://foo.bar/"),
                CheckResult::details(State::Ok, "URL to test: https://foo.bar/"),
                CheckResult::details(State::Ok, "Followed redirect to: https://foo.bar/baz"),
            ]
        )
    }
}

#[cfg(test)]
mod test_check_method {
    use std::vec;

    use super::*;
    use reqwest::Method;

    #[test]
    fn test_ok() {
        assert_eq!(
            check_method(Method::POST),
            vec![CheckResult::details(State::Ok, "Method: POST"),]
        )
    }
}

#[cfg(test)]
mod test_check_version {
    use std::vec;

    use super::*;
    use reqwest::Version;

    #[test]
    fn test_ok() {
        assert_eq!(
            check_version(Version::HTTP_11),
            vec![
                CheckResult::summary(State::Ok, "Version: HTTP/1.1"),
                CheckResult::details(State::Ok, "Version: HTTP/1.1"),
            ]
        )
    }
}

#[cfg(test)]
mod test_check_status {
    use std::vec;

    use super::*;
    use reqwest::StatusCode;

    #[test]
    fn test_success_unchecked() {
        assert_eq!(
            check_status(StatusCode::OK, vec![]),
            vec![
                CheckResult::summary(State::Ok, "Status: 200 OK"),
                CheckResult::details(State::Ok, "Status: 200 OK"),
            ]
        )
    }

    #[test]
    fn test_client_error_unchecked() {
        assert_eq!(
            check_status(StatusCode::EXPECTATION_FAILED, vec![]),
            vec![
                CheckResult::summary(State::Warn, "Status: 417 Expectation Failed"),
                CheckResult::details(State::Warn, "Status: 417 Expectation Failed"),
            ]
        )
    }

    #[test]
    fn test_server_error_unchecked() {
        assert_eq!(
            check_status(StatusCode::INTERNAL_SERVER_ERROR, vec![]),
            vec![
                CheckResult::summary(State::Crit, "Status: 500 Internal Server Error"),
                CheckResult::details(State::Crit, "Status: 500 Internal Server Error"),
            ]
        )
    }

    #[test]
    fn test_success_checked_ok() {
        assert_eq!(
            check_status(StatusCode::OK, vec![StatusCode::OK]),
            vec![
                CheckResult::summary(State::Ok, "Status: 200 OK"),
                CheckResult::details(State::Ok, "Status: 200 OK"),
            ]
        )
    }

    #[test]
    fn test_success_checked_not_ok() {
        assert_eq!(
            check_status(StatusCode::OK, vec![StatusCode::IM_USED]),
            vec![
                CheckResult::summary(State::Crit, "Status: 200 OK (expected 226 IM Used)"),
                CheckResult::details(State::Crit, "Status: 200 OK (expected 226 IM Used)"),
            ]
        )
    }

    #[test]
    fn test_success_checked_multiple_not_ok() {
        assert_eq!(
            check_status(
                StatusCode::OK,
                vec![StatusCode::ACCEPTED, StatusCode::IM_USED]
            ),
            vec![
                CheckResult::summary(State::Crit, "Status: 200 OK (expected one of [202 226])"),
                CheckResult::details(State::Crit, "Status: 200 OK (expected one of [202 226])"),
            ]
        )
    }

    #[test]
    fn test_client_error_checked_ok() {
        assert_eq!(
            check_status(StatusCode::IM_A_TEAPOT, vec![StatusCode::IM_A_TEAPOT]),
            vec![
                CheckResult::summary(State::Ok, "Status: 418 I'm a teapot"),
                CheckResult::details(State::Ok, "Status: 418 I'm a teapot"),
            ]
        )
    }
}

#[cfg(test)]
mod test_check_redirect {
    use super::*;
    use reqwest::StatusCode;

    #[test]
    fn test_no_redirect() {
        assert!(check_redirect(
            StatusCode::OK,
            OnRedirect::Critical,
            Some(Url::parse("https://foo.bar").unwrap())
        )
        .is_empty());
    }

    #[test]
    fn test_redirect_ok() {
        assert_eq!(
            check_redirect(
                StatusCode::MOVED_PERMANENTLY,
                OnRedirect::Ok,
                Some(Url::parse("https://foo.bar").unwrap())
            ),
            vec![CheckResult::details(
                State::Ok,
                "Stopped on redirect to: https://foo.bar/"
            )]
        );
    }

    #[test]
    fn test_redirect_warn() {
        assert_eq!(
            check_redirect(
                StatusCode::MOVED_PERMANENTLY,
                OnRedirect::Warning,
                Some(Url::parse("https://foo.bar").unwrap())
            ),
            vec![
                CheckResult::summary(State::Warn, "Stopped on redirect to: https://foo.bar/"),
                CheckResult::details(State::Warn, "Stopped on redirect to: https://foo.bar/"),
            ]
        );
    }

    #[test]
    fn test_redirect_crit() {
        assert_eq!(
            check_redirect(
                StatusCode::MOVED_PERMANENTLY,
                OnRedirect::Critical,
                Some(Url::parse("https://foo.bar").unwrap())
            ),
            vec![
                CheckResult::summary(State::Crit, "Stopped on redirect to: https://foo.bar/"),
                CheckResult::details(State::Crit, "Stopped on redirect to: https://foo.bar/"),
            ]
        );
    }

    #[test]
    fn test_redirect_sticky() {
        assert_eq!(
            check_redirect(
                StatusCode::MOVED_PERMANENTLY,
                OnRedirect::Sticky,
                Some(Url::parse("https://foo.bar").unwrap())
            ),
            vec![
                CheckResult::summary(
                    State::Warn,
                    "Stopped on redirect to: https://foo.bar/ (changed IP)"
                ),
                CheckResult::details(
                    State::Warn,
                    "Stopped on redirect to: https://foo.bar/ (changed IP)"
                ),
            ]
        );
    }

    #[test]
    fn test_redirect_stickyport() {
        assert_eq!(
            check_redirect(
                StatusCode::MOVED_PERMANENTLY,
                OnRedirect::Stickyport,
                Some(Url::parse("https://foo.bar").unwrap())
            ),
            vec![
                CheckResult::summary(
                    State::Warn,
                    "Stopped on redirect to: https://foo.bar/ (changed IP/port)"
                ),
                CheckResult::details(
                    State::Warn,
                    "Stopped on redirect to: https://foo.bar/ (changed IP/port)"
                ),
            ]
        );
    }

    #[test]
    fn test_redirect_not_handled() {
        // This can happen when hitting "max_redirs", but is handled by check_reqwest_error
        assert!(check_redirect(
            StatusCode::MOVED_PERMANENTLY,
            OnRedirect::Follow,
            Some(Url::parse("https://foo.bar").unwrap())
        )
        .is_empty());
    }
}

#[cfg(test)]
mod test_check_headers {
    use reqwest::header::HeaderName;

    use super::*;
    use std::collections::HashMap;
    use std::str::FromStr;

    #[test]
    fn test_strings_not_found() {
        assert_eq!(
            check_headers(
                &(&HashMap::from([
                    ("some_key1".to_string(), "some_value1".to_string()),
                    ("some_key2".to_string(), "some_value2".to_string()),
                    ("some_key3".to_string(), "some_value3".to_string()),
                ]))
                    .try_into()
                    .unwrap(),
                vec![
                    (
                        TextMatcher::Exact("some_key1".to_string()),
                        TextMatcher::Exact("value1".to_string())
                    ),
                    (
                        TextMatcher::Exact(String::new()),
                        TextMatcher::Exact("value".to_string())
                    ),
                    (
                        TextMatcher::Exact("some_key3".to_string()),
                        TextMatcher::Exact(String::new())
                    ),
                ],
                State::Crit,
            ),
            vec![
                CheckResult::summary(
                    State::Crit,
                    "Expected HTTP header: some_key1:value1 (not found)"
                ),
                CheckResult::details(
                    State::Crit,
                    "Expected HTTP header: some_key1:value1 (not found)"
                ),
                CheckResult::summary(State::Crit, "Expected HTTP header: :value (not found)"),
                CheckResult::details(State::Crit, "Expected HTTP header: :value (not found)"),
                CheckResult::summary(State::Crit, "Expected HTTP header: some_key3: (not found)"),
                CheckResult::details(State::Crit, "Expected HTTP header: some_key3: (not found)"),
            ]
        )
    }

    #[test]
    fn test_strings_not_all_found() {
        assert_eq!(
            check_headers(
                &(&HashMap::from([
                    ("some_key1".to_string(), "some_value1".to_string()),
                    ("some_key2".to_string(), "some_value2".to_string()),
                    ("some_key3".to_string(), "some_value3".to_string()),
                ]))
                    .try_into()
                    .unwrap(),
                vec![
                    (
                        TextMatcher::Exact("some_key1".to_string()),
                        TextMatcher::Exact("some_value1".to_string())
                    ),
                    (
                        TextMatcher::Exact(String::new()),
                        TextMatcher::Exact("value".to_string())
                    ),
                ],
                State::Crit,
            ),
            vec![
                CheckResult::details(
                    State::Ok,
                    "Expected HTTP header: some_key1:some_value1 (found)"
                ),
                CheckResult::summary(State::Crit, "Expected HTTP header: :value (not found)"),
                CheckResult::details(State::Crit, "Expected HTTP header: :value (not found)"),
            ]
        )
    }

    #[test]
    fn test_strings_all_found() {
        assert_eq!(
            check_headers(
                &(&HashMap::from([
                    ("some_key1".to_string(), "some_value1".to_string()),
                    ("some_key2".to_string(), "some_value2".to_string()),
                    ("some_key3".to_string(), "some_value3".to_string()),
                ]))
                    .try_into()
                    .unwrap(),
                vec![
                    (
                        TextMatcher::Exact("some_key1".to_string()),
                        TextMatcher::Exact("some_value1".to_string())
                    ),
                    (
                        TextMatcher::Exact("some_key3".to_string()),
                        TextMatcher::Exact("some_value3".to_string())
                    ),
                ],
                State::Crit,
            ),
            vec![
                CheckResult::details(
                    State::Ok,
                    "Expected HTTP header: some_key1:some_value1 (found)"
                ),
                CheckResult::details(
                    State::Ok,
                    "Expected HTTP header: some_key3:some_value3 (found)"
                ),
            ]
        )
    }

    #[test]
    fn test_strings_mixed_not_found() {
        assert_eq!(
            check_headers(
                &(&HashMap::from([
                    ("some_key1".to_string(), "some_value1".to_string()),
                    ("some_key2".to_string(), "some_value2".to_string()),
                    ("some_key3".to_string(), "some_value3".to_string()),
                ]))
                    .try_into()
                    .unwrap(),
                vec![(
                    TextMatcher::Exact("some_key1".to_string()),
                    TextMatcher::Exact("some_value2".to_string())
                ),],
                State::Crit,
            ),
            vec![
                CheckResult::summary(
                    State::Crit,
                    "Expected HTTP header: some_key1:some_value2 (not found)"
                ),
                CheckResult::details(
                    State::Crit,
                    "Expected HTTP header: some_key1:some_value2 (not found)"
                ),
            ]
        )
    }

    #[test]
    fn test_impossible_non_latin1() {
        assert_eq!(
            check_headers(
                &(&HashMap::from([("some_key1".to_string(), "ßome_value1".to_string()),]))
                    .try_into()
                    .unwrap(),
                vec![(
                    TextMatcher::Exact("some_key1".to_string()),
                    TextMatcher::Exact("ßome_value1".to_string())
                ),],
                State::Crit,
            ),
            vec![
                CheckResult::summary(
                    State::Crit,
                    "Expected HTTP header: some_key1:ßome_value1 (not found)"
                ),
                CheckResult::details(
                    State::Crit,
                    "Expected HTTP header: some_key1:ßome_value1 (not found)"
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
        assert_eq!(
            check_headers(
                &header_map,
                vec![(
                    TextMatcher::Exact("some_key".to_string()),
                    TextMatcher::Exact("öäü".to_string())
                ),],
                State::Crit,
            ),
            vec![CheckResult::details(
                State::Ok,
                "Expected HTTP header: some_key:öäü (found)"
            )]
        )
    }

    #[test]
    fn test_regex() {
        assert_eq!(
            check_headers(
                &(&HashMap::from([
                    ("some_key1".to_string(), "some_value1".to_string()),
                    ("some_key2".to_string(), "some_value2".to_string()),
                    ("some_key3".to_string(), "some_value3".to_string()),
                ]))
                    .try_into()
                    .unwrap(),
                vec![
                    (
                        TextMatcher::from_regex(Regex::new("s.*y[0-9]").unwrap(), true),
                        TextMatcher::from_regex(Regex::new("s[a-z]+_*value1").unwrap(), true)
                    ),
                    (
                        TextMatcher::from_regex(Regex::new("foobar").unwrap(), true),
                        TextMatcher::from_regex(Regex::new("baz").unwrap(), true)
                    ),
                ],
                State::Crit,
            ),
            vec![
                CheckResult::details(
                    State::Ok,
                    "Expected regex in HTTP headers: s.*y[0-9]:s[a-z]+_*value1 (match found)"
                ),
                CheckResult::summary(
                    State::Crit,
                    "Expected regex in HTTP headers: foobar:baz (no match found)"
                ),
                CheckResult::details(
                    State::Crit,
                    "Expected regex in HTTP headers: foobar:baz (no match found)"
                ),
            ]
        )
    }

    #[test]
    fn test_regex_invert() {
        assert_eq!(
            check_headers(
                &(&HashMap::from([("some_key1".to_string(), "some_value1".to_string()),]))
                    .try_into()
                    .unwrap(),
                vec![(
                    TextMatcher::from_regex(Regex::new("s.*y[0-9]").unwrap(), false),
                    TextMatcher::from_regex(Regex::new("s[a-z]+_*value1").unwrap(), false)
                ),],
                State::Crit,
            ),
            vec![
                CheckResult::summary(
                    State::Crit,
                    "Not expected regex in HTTP headers: s.*y[0-9]:s[a-z]+_*value1 (match found)"
                ),
                CheckResult::details(
                    State::Crit,
                    "Not expected regex in HTTP headers: s.*y[0-9]:s[a-z]+_*value1 (match found)"
                ),
            ]
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
        assert_eq!(check_body::<DummyError>(None), (None, vec![]));
    }

    #[test]
    fn test_error_body() {
        assert_eq!(
            check_body(Some(Err(DummyError {}))),
            (
                None,
                vec![
                    CheckResult::summary(State::Crit, "Error fetching the response body"),
                    CheckResult::details(State::Crit, "Error fetching the response body"),
                ]
            )
        );
    }

    #[test]
    fn test_all_ok() {
        assert_eq!(
            check_body::<DummyError>(Some(Ok(Body {
                text: "foobär".to_string(),
                length: 7
            }))),
            (
                Some(Body {
                    text: "foobär".to_string(),
                    length: 7
                }),
                vec![]
            )
        );
    }
}

#[cfg(test)]
mod test_check_page_size {
    use super::*;
    use crate::http::Body;

    #[test]
    fn test_size_lower_out_of_bounds() {
        assert_eq!(
            check_page_size(
                Some(&Body {
                    text: String::new(),
                    length: 42,
                }),
                Some(Bounds::lower(56)),
            ),
            vec![
                CheckResult::summary(State::Warn, "Page size: 42 Bytes (warn below 56 Bytes)"),
                CheckResult::details(State::Warn, "Page size: 42 Bytes (warn below 56 Bytes)"),
                CheckResult::metric("response_size", 42., Some('B'), None, Some(0.), None)
            ]
        );
    }

    #[test]
    fn test_size_lower_and_higher_too_low() {
        assert_eq!(
            check_page_size(
                Some(&Body {
                    text: String::new(),
                    length: 42,
                }),
                Some(Bounds::lower_upper(56, 100)),
            ),
            vec![
                CheckResult::summary(
                    State::Warn,
                    "Page size: 42 Bytes (warn below/above 56 Bytes/100 Bytes)"
                ),
                CheckResult::details(
                    State::Warn,
                    "Page size: 42 Bytes (warn below/above 56 Bytes/100 Bytes)"
                ),
                CheckResult::metric("response_size", 42., Some('B'), None, Some(0.), None)
            ]
        );
    }

    #[test]
    fn test_size_lower_and_higher_too_high() {
        assert_eq!(
            check_page_size(
                Some(&Body {
                    text: String::new(),
                    length: 142,
                }),
                Some(Bounds::lower_upper(56, 100)),
            ),
            vec![
                CheckResult::summary(
                    State::Warn,
                    "Page size: 142 Bytes (warn below/above 56 Bytes/100 Bytes)"
                ),
                CheckResult::details(
                    State::Warn,
                    "Page size: 142 Bytes (warn below/above 56 Bytes/100 Bytes)"
                ),
                CheckResult::metric("response_size", 142., Some('B'), None, Some(0.), None)
            ]
        );
    }
}

#[cfg(test)]
mod test_check_body_matching {
    use super::*;

    fn test_body(test_string: &str) -> Option<Body> {
        Some(Body {
            text: test_string.to_owned(),
            length: 0,
        })
    }

    #[test]
    fn test_no_matcher() {
        assert!(check_body_matching(test_body("foobar").as_ref(), vec![], State::Crit).is_empty());
    }

    #[test]
    fn test_string_ok() {
        assert_eq!(
            check_body_matching(
                test_body("foobar").as_ref(),
                vec![TextMatcher::Contains("bar".to_string())],
                State::Crit,
            ),
            vec![CheckResult::details(
                State::Ok,
                "Expected string in body: bar (found)"
            ),]
        );
    }

    #[test]
    fn test_string_not_found() {
        assert_eq!(
            check_body_matching(
                test_body("foobär").as_ref(),
                vec![TextMatcher::Contains("bar".to_string())],
                State::Crit,
            ),
            vec![
                CheckResult::summary(State::Crit, "Expected string in body: bar (not found)"),
                CheckResult::details(State::Crit, "Expected string in body: bar (not found)"),
            ]
        );
    }

    #[test]
    fn test_multiple_strings_not_found() {
        assert_eq!(
            check_body_matching(
                test_body("foobär").as_ref(),
                vec![
                    TextMatcher::Contains("bar".to_string()),
                    TextMatcher::Contains("baz".to_string())
                ],
                State::Crit,
            ),
            vec![
                CheckResult::summary(State::Crit, "Expected string in body: bar (not found)"),
                CheckResult::details(State::Crit, "Expected string in body: bar (not found)"),
                CheckResult::summary(State::Crit, "Expected string in body: baz (not found)"),
                CheckResult::details(State::Crit, "Expected string in body: baz (not found)"),
            ]
        );
    }

    #[test]
    fn test_regex_ok() {
        assert_eq!(
            check_body_matching(
                test_body("foobar").as_ref(),
                vec![TextMatcher::from_regex(Regex::new("f.*r").unwrap(), true)],
                State::Crit,
            ),
            vec![CheckResult::details(
                State::Ok,
                "Expected regex in body: f.*r (match found)"
            ),]
        );
    }

    #[test]
    fn test_regex_not_ok() {
        assert_eq!(
            check_body_matching(
                test_body("foobar").as_ref(),
                vec![TextMatcher::from_regex(Regex::new("f.*z").unwrap(), true)],
                State::Crit,
            ),
            vec![
                CheckResult::summary(State::Crit, "Expected regex in body: f.*z (no match found)"),
                CheckResult::details(State::Crit, "Expected regex in body: f.*z (no match found)"),
            ]
        );
    }

    #[test]
    fn test_regex_inverse_ok() {
        assert_eq!(
            check_body_matching(
                test_body("foobar").as_ref(),
                vec![TextMatcher::from_regex(Regex::new("f.*z").unwrap(), false)],
                State::Crit,
            ),
            vec![CheckResult::details(
                State::Ok,
                "Not expected regex in body: f.*z (no match found)"
            ),]
        );
    }

    #[test]
    fn test_regex_inverse_not_ok() {
        assert_eq!(
            check_body_matching(
                test_body("argl").as_ref(),
                vec![TextMatcher::from_regex(Regex::new("argl").unwrap(), false)],
                State::Crit,
            ),
            vec![
                CheckResult::summary(
                    State::Crit,
                    "Not expected regex in body: argl (match found)"
                ),
                CheckResult::details(
                    State::Crit,
                    "Not expected regex in body: argl (match found)"
                )
            ]
        );
    }

    #[test]
    fn test_multiple_matchers_ok() {
        assert_eq!(
            check_body_matching(
                test_body("foobar").as_ref(),
                vec![
                    TextMatcher::Contains("bar".to_string()),
                    TextMatcher::Contains("foo".to_string())
                ],
                State::Crit,
            ),
            vec![
                CheckResult::details(State::Ok, "Expected string in body: bar (found)"),
                CheckResult::details(State::Ok, "Expected string in body: foo (found)"),
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
        assert_eq!(
            check_response_time(
                Duration::new(1, 0),
                Some(Duration::new(4, 0)),
                None,
                Duration::from_secs(10)
            ),
            vec![
                CheckResult::details(State::Ok, "Response time: 5 seconds"),
                CheckResult::metric("response_time", 5., Some('s'), None, Some(0.), Some(10.)),
                CheckResult::metric("time_http_headers", 1., Some('s'), None, None, None),
                CheckResult::metric("time_http_body", 4., Some('s'), None, None, None),
            ]
        );
    }

    #[test]
    fn test_warn_within_bounds() {
        assert_eq!(
            check_response_time(
                Duration::new(1, 0),
                Some(Duration::new(4, 0)),
                Some(UpperLevels::warn(6.)),
                Duration::from_secs(10)
            ),
            vec![
                CheckResult::details(State::Ok, "Response time: 5 seconds"),
                CheckResult::metric(
                    "response_time",
                    5.,
                    Some('s'),
                    Some(UpperLevels::warn(6.)),
                    Some(0.),
                    Some(10.)
                ),
                CheckResult::metric("time_http_headers", 1., Some('s'), None, None, None),
                CheckResult::metric("time_http_body", 4., Some('s'), None, None, None),
            ]
        );
    }

    #[test]
    fn test_warn_is_warn() {
        assert_eq!(
            check_response_time(
                Duration::new(1, 0),
                Some(Duration::new(4, 0)),
                Some(UpperLevels::warn(4.)),
                Duration::from_secs(10)
            ),
            vec![
                CheckResult::summary(State::Warn, "Response time: 5 seconds (warn at 4 seconds)"),
                CheckResult::details(State::Warn, "Response time: 5 seconds (warn at 4 seconds)"),
                CheckResult::metric(
                    "response_time",
                    5.,
                    Some('s'),
                    Some(UpperLevels::warn(4.)),
                    Some(0.),
                    Some(10.)
                ),
                CheckResult::metric("time_http_headers", 1., Some('s'), None, None, None),
                CheckResult::metric("time_http_body", 4., Some('s'), None, None, None),
            ]
        );
    }

    #[test]
    fn test_warncrit_within_bounds() {
        assert_eq!(
            check_response_time(
                Duration::new(1, 0),
                Some(Duration::new(4, 0)),
                Some(UpperLevels::warn_crit(6., 7.)),
                Duration::from_secs(10)
            ),
            vec![
                CheckResult::details(State::Ok, "Response time: 5 seconds"),
                CheckResult::metric(
                    "response_time",
                    5.,
                    Some('s'),
                    Some(UpperLevels::warn_crit(6., 7.)),
                    Some(0.),
                    Some(10.)
                ),
                CheckResult::metric("time_http_headers", 1., Some('s'), None, None, None),
                CheckResult::metric("time_http_body", 4., Some('s'), None, None, None),
            ]
        );
    }

    #[test]
    fn test_warncrit_is_warn() {
        assert_eq!(
            check_response_time(
                Duration::new(1, 0),
                Some(Duration::new(4, 0)),
                Some(UpperLevels::warn_crit(4., 6.)),
                Duration::from_secs(10)
            ),
            vec![
                CheckResult::summary(
                    State::Warn,
                    "Response time: 5 seconds (warn/crit at 4 seconds/6 seconds)"
                ),
                CheckResult::details(
                    State::Warn,
                    "Response time: 5 seconds (warn/crit at 4 seconds/6 seconds)"
                ),
                CheckResult::metric(
                    "response_time",
                    5.,
                    Some('s'),
                    Some(UpperLevels::warn_crit(4., 6.)),
                    Some(0.),
                    Some(10.)
                ),
                CheckResult::metric("time_http_headers", 1., Some('s'), None, None, None),
                CheckResult::metric("time_http_body", 4., Some('s'), None, None, None),
            ]
        );
    }

    #[test]
    fn test_warncrit_is_crit() {
        assert_eq!(
            check_response_time(
                Duration::new(1, 0),
                Some(Duration::new(4, 0)),
                Some(UpperLevels::warn_crit(2., 3.)),
                Duration::from_secs(10)
            ),
            vec![
                CheckResult::summary(
                    State::Crit,
                    "Response time: 5 seconds (warn/crit at 2 seconds/3 seconds)"
                ),
                CheckResult::details(
                    State::Crit,
                    "Response time: 5 seconds (warn/crit at 2 seconds/3 seconds)"
                ),
                CheckResult::metric(
                    "response_time",
                    5.,
                    Some('s'),
                    Some(UpperLevels::warn_crit(2., 3.)),
                    Some(0.),
                    Some(10.)
                ),
                CheckResult::metric("time_http_headers", 1., Some('s'), None, None, None),
                CheckResult::metric("time_http_body", 4., Some('s'), None, None, None),
            ]
        );
    }

    #[test]
    fn test_no_body() {
        assert_eq!(
            check_response_time(
                Duration::new(5, 0),
                None,
                Some(UpperLevels::warn_crit(2., 3.)),
                Duration::from_secs(10)
            ),
            vec![
                CheckResult::summary(
                    State::Crit,
                    "Response time: 5 seconds (warn/crit at 2 seconds/3 seconds)"
                ),
                CheckResult::details(
                    State::Crit,
                    "Response time: 5 seconds (warn/crit at 2 seconds/3 seconds)"
                ),
                CheckResult::metric(
                    "response_time",
                    5.,
                    Some('s'),
                    Some(UpperLevels::warn_crit(2., 3.)),
                    Some(0.),
                    Some(10.)
                ),
                CheckResult::metric("time_http_headers", 5., Some('s'), None, None, None),
            ]
        );
    }

    #[test]
    fn test_formatting() {
        assert_eq!(
            check_response_time(
                Duration::new(1, 100_000_000),
                Some(Duration::new(4, 23_456_789)),
                Some(UpperLevels::warn_crit(2.1, 3.12)),
                Duration::from_secs(10)
            ),
            vec![
                CheckResult::summary(
                    State::Crit,
                    "Response time: 5.123 seconds (warn/crit at 2.1 seconds/3.12 seconds)"
                ),
                CheckResult::details(
                    State::Crit,
                    "Response time: 5.123 seconds (warn/crit at 2.1 seconds/3.12 seconds)"
                ),
                CheckResult::metric(
                    "response_time",
                    5.123456789,
                    Some('s'),
                    Some(UpperLevels::warn_crit(2.1, 3.12)),
                    Some(0.),
                    Some(10.)
                ),
                CheckResult::metric("time_http_headers", 1.1, Some('s'), None, None, None),
                CheckResult::metric("time_http_body", 4.023456789, Some('s'), None, None, None),
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
        assert!(check_page_age(
            system_time(UNIX_TIME_2023_11_16),
            Some(&header_date("We don't care")),
            None,
        )
        .is_empty());
    }

    #[test]
    fn test_missing_header_value() {
        assert_eq!(
            check_page_age(
                system_time(UNIX_TIME_2023_11_16),
                None,
                Some(UpperLevels::warn(THIRTYSIX_HOURS)),
            ),
            vec![
                CheckResult::summary(State::Crit, "Can't determine page age"),
                CheckResult::details(State::Crit, "Can't determine page age")
            ]
        );
    }

    #[test]
    fn test_erroneous_date() {
        assert_eq!(
            check_page_age(
                system_time(UNIX_TIME_2023_11_16),
                Some(&header_date("Something wrong")),
                Some(UpperLevels::warn(THIRTYSIX_HOURS)),
            ),
            vec![
                CheckResult::summary(State::Crit, "Can't decode page age"),
                CheckResult::details(State::Crit, "Can't decode page age")
            ]
        );
    }

    #[test]
    fn test_date_in_future() {
        assert_eq!(
            check_page_age(
                system_time(UNIX_TIME_2023_11_16),
                Some(&header_date(DATE_2023_11_17)),
                Some(UpperLevels::warn(THIRTYSIX_HOURS)),
            ),
            vec![
                CheckResult::summary(State::Crit, "Can't decode page age"),
                CheckResult::details(State::Crit, "Can't decode page age")
            ]
        );
    }

    #[test]
    fn test_ok() {
        assert_eq!(
            check_page_age(
                system_time(UNIX_TIME_2023_11_16),
                Some(&header_date(DATE_2023_11_15)),
                Some(UpperLevels::warn(THIRTYSIX_HOURS)),
            ),
            vec![CheckResult::details(State::Ok, "Page age: 86400 seconds")]
        );
    }

    #[test]
    fn test_warn() {
        assert_eq!(
            check_page_age(
                system_time(UNIX_TIME_2023_11_16),
                Some(&header_date(DATE_2023_11_15)),
                Some(UpperLevels::warn(TWELVE_HOURS)),
            ),
            vec![
                CheckResult::summary(
                    State::Warn,
                    "Page age: 86400 seconds (warn at 43200 seconds)"
                ),
                CheckResult::details(
                    State::Warn,
                    "Page age: 86400 seconds (warn at 43200 seconds)"
                )
            ]
        );
    }
}

#[cfg(test)]
mod test_check_user_agent {
    use std::vec;

    use super::*;

    #[test]
    fn test_ok() {
        assert_eq!(
            check_user_agent("Agent Smith".to_string()),
            vec![CheckResult::details(State::Ok, "User agent: Agent Smith"),]
        )
    }
}
