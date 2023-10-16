use anyhow::Result as AnyhowResult;
use clap::Parser;
use http::{HeaderMap, HeaderName, HeaderValue};
use reqwest::{header::USER_AGENT, RequestBuilder};
use std::time::{Duration, Instant};

mod cli;
mod pwstore;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args = cli::Cli::parse();

    let req = prepare_request(
        args.url,
        args.user_agent,
        args.headers,
        Duration::from_secs(args.timeout),
        args.auth_user,
        args.auth_pw.auth_pw_plain.or(args.auth_pw.auth_pwstore),
    )?;

    let now = Instant::now();

    let resp = req.send().await?;

    let headers = resp.headers();
    println!("{:#?}", headers);

    let body = match args.without_body {
        false => resp.text().await?,
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
        for (name, value) in hds.into_iter() {
            cli_headers.insert(name, value);
        }
    }

    let client = reqwest::Client::builder()
        .timeout(timeout)
        .default_headers(cli_headers)
        .build()?;

    let req = client.get(url);
    if let Some(user) = auth_user {
        Ok(req.basic_auth(user, auth_pw))
    } else {
        Ok(req)
    }
}
