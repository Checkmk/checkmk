use anyhow::Result as AnyhowResult;
use http::{HeaderMap, HeaderName, HeaderValue};
use reqwest::{header::USER_AGENT, Error as ReqwestError, Method, RequestBuilder, Response};
use std::{
    fmt::{Display, Formatter, Result as FormatResult},
    time::{Duration, Instant},
};

pub mod cli;
mod pwstore;

#[derive(PartialEq, Eq)]
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

pub struct Output {
    pub state: State,
    pub summary: String,
    pub details: Option<String>,
}

impl Display for Output {
    fn fmt(&self, f: &mut Formatter) -> FormatResult {
        match &self.details {
            Some(det) => write!(f, "HTTP {} - {}\n{}", self.state, self.summary, det),
            None => write!(f, "HTTP {} - {}", self.state, self.summary),
        }
    }
}

impl Output {
    pub fn from_short(state: State, summary: &str) -> Self {
        Self {
            state,
            summary: summary.to_string(),
            details: None,
        }
    }
}

pub async fn check_http(args: cli::Cli) -> Output {
    let request = match prepare_request(
        args.url,
        args.method,
        args.user_agent,
        args.headers,
        args.timeout,
        args.auth_user,
        args.auth_pw.auth_pw_plain.or(args.auth_pw.auth_pwstore),
    ) {
        Ok(req) => req,
        Err(_) => {
            return Output::from_short(State::Unknown, "Error building the request");
        }
    };
    let now = Instant::now();
    let response = request.send().await;
    analyze_response(response, now, args.without_body).await
}

fn prepare_request(
    url: String,
    method: Method,
    user_agent: Option<HeaderValue>,
    headers: Option<Vec<(HeaderName, HeaderValue)>>,
    timeout: Duration,
    auth_user: Option<String>,
    auth_pw: Option<String>,
) -> AnyhowResult<RequestBuilder> {
    let mut cli_headers = HeaderMap::new();
    if let Some(ua) = user_agent {
        cli_headers.insert(USER_AGENT, ua);
    }
    if let Some(hds) = headers {
        cli_headers.extend(hds);
    }

    let client = reqwest::Client::builder()
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

async fn analyze_response(
    response: Result<Response, ReqwestError>,
    start_time: Instant,
    without_body: bool,
) -> Output {
    let response = match response {
        Ok(resp) => resp,
        Err(err) => {
            if err.is_timeout() {
                return Output::from_short(State::Crit, "timeout");
            } else if err.is_connect() {
                return Output::from_short(State::Crit, "Failed to connect");
            } else {
                return Output::from_short(State::Unknown, "Error while sending request");
            }
        }
    };

    let status = response.status();
    let http_version = response.version();
    let response_state = if status.is_client_error() {
        State::Warn
    } else if status.is_server_error() {
        State::Crit
    } else {
        State::Ok
    };

    let body = match without_body {
        false => match response.text().await {
            Ok(bd) => bd,
            Err(_) => {
                return Output::from_short(State::Unknown, "Error fetching the reponse body");
            }
        },
        true => "".to_string(),
    };

    let elapsed = start_time.elapsed();

    Output::from_short(
        response_state,
        &format!(
            "{:?} {} - {} bytes in {}.{} second response time",
            http_version,
            status,
            body.len(),
            elapsed.as_secs(),
            elapsed.subsec_millis()
        ),
    )
}
