use anyhow::Result as AnyhowResult;
use http::{HeaderMap, HeaderName, HeaderValue, Method};
use reqwest::{header::USER_AGENT, RequestBuilder};
use std::time::{Duration, Instant};

pub mod cli;
mod pwstore;

#[tokio::main]
pub async fn check_http(args: cli::Cli) -> AnyhowResult<()> {
    let request = prepare_request(
        args.url,
        args.method,
        args.user_agent,
        args.headers,
        args.timeout,
        args.auth_user,
        args.auth_pw.auth_pw_plain.or(args.auth_pw.auth_pwstore),
    )?;

    let now = Instant::now();

    let response = request.send().await?;

    let headers = response.headers();
    println!("{:#?}", headers);

    let body = match args.without_body {
        false => response.text().await?,
        true => "".to_string(),
    };

    let elapsed = now.elapsed();

    println!(
        "Downloaded {} bytes in {}.{} seconds.",
        body.len(),
        elapsed.as_secs(),
        elapsed.subsec_millis()
    );
    Ok(())
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
