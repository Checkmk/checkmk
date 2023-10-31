use anyhow::Result as AnyhowResult;
use bytes::Bytes;
use cli::{Cli, DocumentAgeLevels, ForceIP, PageSizeLimits, ResponseTimeLevels};
use http::{HeaderMap, HeaderName, HeaderValue};
use httpdate::parse_http_date;
use reqwest::{
    header::USER_AGENT,
    redirect::{Action, Attempt, Policy},
    Error as ReqwestError, Method, RequestBuilder, Result as ReqwestResult, StatusCode, Version,
};
use std::{
    net::{IpAddr, Ipv4Addr, Ipv6Addr, SocketAddr},
    time::{Duration, Instant, SystemTime},
};

use crate::checking::{Output, State};
use crate::cli::OnRedirect;

pub mod checking;
pub mod cli;
mod pwstore;

struct ProcessedResponse {
    pub version: Version,
    pub status: StatusCode,
    pub headers: HeaderMap, // TODO(au): use
    pub body: Option<ReqwestResult<Bytes>>,
    pub elapsed: Duration,
}

pub async fn check_http(args: Cli) -> Output {
    let Ok(request) = prepare_request(
        args.url,
        args.method,
        args.user_agent,
        args.headers,
        args.timeout,
        args.auth_user,
        args.auth_pw.auth_pw_plain.or(args.auth_pw.auth_pwstore),
        args.onredirect.clone(),
        args.max_redirs,
        args.force_ip_version,
    ) else {
        return output_from_preparation_error();
    };

    let response = match perform_request(request, args.without_body).await {
        Ok(resp) => resp,
        Err(err) => {
            return output_from_request_error(err);
        }
    };

    check_response(
        response,
        args.onredirect,
        args.page_size,
        args.response_time_levels,
        args.document_age_levels,
    )
    .await
}

fn output_from_preparation_error() -> Output {
    Output::from_summary(State::Unknown, "Error building the request")
}

#[allow(clippy::too_many_arguments)] //TODO(au): Fix - Introduce separate configs/options for each function
fn prepare_request(
    url: String,
    method: Method,
    user_agent: Option<HeaderValue>,
    headers: Option<Vec<(HeaderName, HeaderValue)>>,
    timeout: Duration,
    auth_user: Option<String>,
    auth_pw: Option<String>,
    onredirect: OnRedirect,
    max_redirs: usize,
    force_ip: Option<ForceIP>,
) -> AnyhowResult<RequestBuilder> {
    let mut cli_headers = HeaderMap::new();
    if let Some(ua) = user_agent {
        cli_headers.insert(USER_AGENT, ua);
    }
    if let Some(hds) = headers {
        cli_headers.extend(hds);
    }

    let redirect_policy = get_redirect_policy(onredirect, force_ip.clone(), max_redirs);
    let client = reqwest::Client::builder();

    let client = match force_ip {
        None => client,
        Some(ipv) => match ipv {
            ForceIP::Ipv4 => client.local_address(IpAddr::V4(Ipv4Addr::UNSPECIFIED)),
            ForceIP::Ipv6 => client.local_address(IpAddr::V6(Ipv6Addr::UNSPECIFIED)),
        },
    };

    let client = client
        .redirect(redirect_policy)
        .timeout(timeout)
        .default_headers(cli_headers)
        .build()?;

    let req = client.request(method, url);
    if let Some(user) = auth_user {
        Ok(req.basic_auth(user, auth_pw))
    } else {
        Ok(req)
    }
}

fn output_from_request_error(err: ReqwestError) -> Output {
    if err.is_timeout() {
        Output::from_summary(State::Crit, "timeout")
    } else if err.is_connect() {
        Output::from_summary(State::Crit, "Failed to connect")
    } else if err.is_redirect() {
        Output::from_summary(State::Crit, &err.to_string()) // Hit one of max_redirs, sticky, stickyport
    } else {
        Output::from_summary(State::Unknown, "Error while sending request")
    }
}

fn get_redirect_policy(
    onredirect: OnRedirect,
    force_ip: Option<ForceIP>,
    max_redirs: usize,
) -> Policy {
    match onredirect {
        OnRedirect::Ok | OnRedirect::Warning | OnRedirect::Critical => Policy::none(),
        OnRedirect::Follow => Policy::limited(max_redirs),
        OnRedirect::Sticky => {
            Policy::custom(move |att| policy_sticky(att, force_ip.clone(), max_redirs, false))
        }
        OnRedirect::Stickyport => {
            Policy::custom(move |att| policy_sticky(att, force_ip.clone(), max_redirs, true))
        }
    }
}

fn policy_sticky(
    attempt: Attempt,
    force_ip: Option<ForceIP>,
    max_redirs: usize,
    sticky_port: bool,
) -> Action {
    if attempt.previous().len() > max_redirs {
        return attempt.error("too many redirects");
    }

    let previous_socket_addrs = attempt
        .previous()
        .last()
        .unwrap()
        .socket_addrs(|| None)
        .unwrap();
    let socket_addrs = attempt.url().socket_addrs(|| None).unwrap();

    let previous_socket_addr = filter_socket_addrs(previous_socket_addrs, force_ip.clone());
    let socket_addr = filter_socket_addrs(socket_addrs, force_ip);

    match sticky_port {
        false => {
            if contains_unchanged_ip(&previous_socket_addr, &socket_addr) {
                attempt.follow()
            } else {
                attempt.error("Detected changed IP")
            }
        }
        true => {
            if contains_unchanged_addr(&previous_socket_addr, &socket_addr) {
                attempt.follow()
            } else {
                attempt.error("Detected changed IP/port")
            }
        }
    }
}

fn filter_socket_addrs(addrs: Vec<SocketAddr>, force_ip: Option<ForceIP>) -> Vec<SocketAddr> {
    match force_ip {
        None => addrs,
        Some(ipv) => match ipv {
            ForceIP::Ipv4 => addrs.into_iter().filter(|addr| addr.is_ipv4()).collect(),
            ForceIP::Ipv6 => addrs.into_iter().filter(|addr| addr.is_ipv6()).collect(),
        },
    }
}

fn contains_unchanged_ip(old: &[SocketAddr], new: &[SocketAddr]) -> bool {
    old.iter()
        .any(|addr| new.iter().any(|prev_addr| prev_addr.ip() == addr.ip()))
}

fn contains_unchanged_addr(old: &[SocketAddr], new: &[SocketAddr]) -> bool {
    old.iter()
        .any(|addr| new.iter().any(|prev_addr| prev_addr == addr))
}

async fn perform_request(
    request: RequestBuilder,
    without_body: bool,
) -> Result<ProcessedResponse, ReqwestError> {
    let now = Instant::now();
    let response = request.send().await?;

    let headers = response.headers().to_owned();
    let version = response.version();
    let status = response.status();
    let body = match without_body {
        false => Some(response.bytes().await),
        true => None,
    };
    let elapsed = now.elapsed();

    Ok(ProcessedResponse {
        version,
        status,
        headers,
        body,
        elapsed,
    })
}

async fn check_response(
    response: ProcessedResponse,
    onredirect: OnRedirect,
    page_size_limits: Option<PageSizeLimits>,
    response_time_levels: Option<ResponseTimeLevels>,
    document_age_levels: Option<DocumentAgeLevels>,
) -> Output {
    let mut outputs: Vec<Output> = Vec::new();

    outputs.push(check_status(response.status, response.version, onredirect));

    if let Some(body) = response.body {
        match body {
            Ok(bd) => {
                outputs.push(check_page_size(bd.len(), page_size_limits));
            }
            Err(_) => {
                outputs.push(Output::from_summary(
                    State::Crit,
                    "Error fetching the reponse body",
                ));
            }
        };
    };

    outputs.push(check_response_time(response.elapsed, response_time_levels));

    outputs.push(check_document_age(&response.headers, document_age_levels));

    merge_outputs(&outputs)
}

fn check_status(status: StatusCode, version: Version, onredirect: OnRedirect) -> Output {
    let response_state = if status.is_client_error() {
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

    Output::from_summary(response_state, &format!("{:?} {}", version, status))
}

fn check_page_size(page_size: usize, page_size_limits: Option<PageSizeLimits>) -> Output {
    let output_fn = |state| Output::from_summary(state, &format!("Page size: {} bytes", page_size));

    match page_size_limits {
        Some((lower, _)) if page_size < lower => output_fn(State::Warn),
        Some((_, Some(upper))) if page_size > upper => output_fn(State::Warn),
        _ => output_fn(State::Ok),
    }
}

fn check_response_time(
    response_time: Duration,
    response_time_levels: Option<ResponseTimeLevels>,
) -> Output {
    let output_fn = |state| {
        Output::from_summary(
            state,
            &format!(
                "Response time: {}.{}s",
                response_time.as_secs(),
                response_time.subsec_millis()
            ),
        )
    };

    match response_time_levels {
        Some((_, Some(crit))) if response_time.as_secs_f64() >= crit => output_fn(State::Crit),
        Some((warn, _)) if response_time.as_secs_f64() >= warn => output_fn(State::Warn),
        _ => output_fn(State::Ok),
    }
}

fn check_document_age(
    headers: &HeaderMap,
    document_age_levels: Option<DocumentAgeLevels>,
) -> Output {
    if document_age_levels.is_none() {
        return Output::from_state(State::Ok);
    };

    let now = SystemTime::now();

    let age_header = headers.get("last-modified").or(headers.get("date"));
    let Some(document_age) = age_header else {
        return Output::from_summary(State::Crit, "Can't determine document age");
    };
    let Ok(Ok(age)) = document_age.to_str().map(parse_http_date) else {
        return Output::from_summary(State::Crit, "Can't decode document age");
    };

    //TODO(au): Specify "too old" in Output
    match document_age_levels {
        Some((_, Some(crit))) if now - Duration::from_secs(crit) > age => {
            Output::from_summary(State::Crit, "Document age too old")
        }
        Some((warn, _)) if now - Duration::from_secs(warn) > age => {
            Output::from_summary(State::Warn, "Document age too old")
        }
        _ => Output::from_state(State::Ok),
    }
}

fn merge_outputs(outputs: &[Output]) -> Output {
    let summary = outputs
        .iter()
        .filter_map(|output| output.summary.clone())
        .collect::<Vec<String>>()
        .join(", ");
    let summary = if summary.is_empty() {
        None
    } else {
        Some(summary)
    };
    let details = outputs
        .iter()
        .filter_map(|output| output.details.clone())
        .collect::<Vec<String>>()
        .join("\n");
    let details = if details.is_empty() {
        None
    } else {
        Some(details)
    };

    let state = outputs
        .iter()
        .map(|output| output.state.clone())
        .max()
        .unwrap();

    Output {
        state,
        summary,
        details,
    }
}

#[cfg(test)]
mod tests {
    use std::net::SocketAddr;

    use crate::{contains_unchanged_addr, contains_unchanged_ip, filter_socket_addrs, ForceIP};

    #[test]
    fn test_contains_unchanged_ip() {
        let old_addrs: Vec<SocketAddr> = vec![
            "1.2.3.4:80".parse().unwrap(),
            "[1234:abcd::]:80".parse().unwrap(),
        ];
        let new_addrs = old_addrs.clone();
        assert!(contains_unchanged_ip(&old_addrs, &new_addrs));

        let new_addrs: Vec<SocketAddr> = vec![
            "1.2.3.4:443".parse().unwrap(),
            "[2345:abcd::]:80".parse().unwrap(),
        ];
        assert!(contains_unchanged_ip(&old_addrs, &new_addrs));

        let new_addrs: Vec<SocketAddr> = vec![
            "2.3.4.5:80".parse().unwrap(),
            "[2345:abcd::]:80".parse().unwrap(),
        ];
        assert!(!contains_unchanged_ip(&old_addrs, &new_addrs));
    }

    #[test]
    fn test_contains_unchanged_addr() {
        let old_addrs: Vec<SocketAddr> = vec![
            "1.2.3.4:80".parse().unwrap(),
            "[1234:abcd::]:80".parse().unwrap(),
        ];
        let new_addrs = old_addrs.clone();
        assert!(contains_unchanged_addr(&old_addrs, &new_addrs));

        let new_addrs: Vec<SocketAddr> = vec![
            "1.2.3.4:443".parse().unwrap(),
            "[2345:abcd::]:80".parse().unwrap(),
        ];
        assert!(!contains_unchanged_addr(&old_addrs, &new_addrs));
    }

    #[test]
    fn test_filter_socket_addrs() {
        let addrs: Vec<SocketAddr> = vec![
            "1.2.3.4:443".parse().unwrap(),
            "2.3.4.5:1234".parse().unwrap(),
            "[2345:abcd::]:80".parse().unwrap(),
            "[1234:abcd::]:8888".parse().unwrap(),
        ];
        let ipv4_addrs: Vec<SocketAddr> = vec![
            "1.2.3.4:443".parse().unwrap(),
            "2.3.4.5:1234".parse().unwrap(),
        ];
        let ipv6_addrs: Vec<SocketAddr> = vec![
            "[2345:abcd::]:80".parse().unwrap(),
            "[1234:abcd::]:8888".parse().unwrap(),
        ];
        assert_eq!(addrs, filter_socket_addrs(addrs.clone(), None));
        assert_eq!(
            ipv4_addrs,
            filter_socket_addrs(addrs.clone(), Some(ForceIP::Ipv4))
        );
        assert_eq!(ipv6_addrs, filter_socket_addrs(addrs, Some(ForceIP::Ipv6)));
    }
}

#[cfg(test)]
mod test_output_format {
    use crate::{merge_outputs, Output, State};

    fn s(s: &str) -> Option<String> {
        Some(String::from(s))
    }

    #[test]
    fn test_output_with_state_only() {
        assert_eq!(
            format!(
                "{}",
                Output {
                    state: State::Ok,
                    summary: None,
                    details: None
                }
            ),
            "HTTP OK"
        );
    }

    #[test]
    fn test_output_with_empty_fields() {
        assert_eq!(
            format!(
                "{}",
                Output {
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
    fn test_output_with_summary() {
        assert_eq!(
            format!(
                "{}",
                Output {
                    state: State::Ok,
                    summary: s("this is the summary"),
                    details: None
                }
            ),
            "HTTP OK - this is the summary"
        );
    }

    #[test]
    fn test_output_with_details() {
        assert_eq!(
            format!(
                "{}",
                Output {
                    state: State::Ok,
                    summary: None,
                    details: s("these are the details")
                }
            ),
            "HTTP OK\nthese are the details"
        );
    }

    #[test]
    fn test_output_with_summary_and_details() {
        assert_eq!(
            format!(
                "{}",
                Output {
                    state: State::Ok,
                    summary: s("this is the summary"),
                    details: s("these are the details")
                }
            ),
            "HTTP OK - this is the summary\nthese are the details"
        );
    }

    #[test]
    fn test_merge_outputs_with_state_only() {
        let o1 = Output {
            state: State::Ok,
            summary: None,
            details: None,
        };
        let o2 = Output {
            state: State::Ok,
            summary: None,
            details: None,
        };
        let o3 = Output {
            state: State::Ok,
            summary: None,
            details: None,
        };
        assert_eq!(format!("{}", merge_outputs(&[o1, o2, o3])), "HTTP OK");
    }

    #[test]
    fn test_merge_outputs_with_summary() {
        let o1 = Output {
            state: State::Ok,
            summary: s("summary 1"),
            details: None,
        };
        let o2 = Output {
            state: State::Ok,
            summary: s("summary 2"),
            details: None,
        };
        let o3 = Output {
            state: State::Ok,
            summary: s("summary 3"),
            details: None,
        };
        assert_eq!(
            format!("{}", merge_outputs(&[o1, o2, o3])),
            "HTTP OK - summary 1, summary 2, summary 3"
        );
    }

    #[test]
    fn test_merge_outputs_with_details() {
        let o1 = Output {
            state: State::Ok,
            summary: None,
            details: s("details 1"),
        };
        let o2 = Output {
            state: State::Ok,
            summary: None,
            details: s("details 2"),
        };
        let o3 = Output {
            state: State::Ok,
            summary: None,
            details: s("details 3"),
        };
        assert_eq!(
            format!("{}", merge_outputs(&[o1, o2, o3])),
            "HTTP OK\ndetails 1\ndetails 2\ndetails 3"
        );
    }

    #[test]
    fn test_merge_outputs_with_summary_and_details() {
        let o1 = Output {
            state: State::Ok,
            summary: s("summary 1"),
            details: s("details 1"),
        };
        let o2 = Output {
            state: State::Ok,
            summary: s("summary 2"),
            details: s("details 2"),
        };
        let o3 = Output {
            state: State::Ok,
            summary: s("summary 3"),
            details: s("details 3"),
        };
        assert_eq!(
            format!("{}", merge_outputs(&[o1, o2, o3])),
            "HTTP OK - summary 1, summary 2, summary 3\ndetails 1\ndetails 2\ndetails 3"
        );
    }
}
