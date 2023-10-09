use clap::Parser;
use http::{HeaderMap, HeaderValue};
use reqwest::header::USER_AGENT;
use std::time::{Duration, Instant};

mod cli;
mod pwstore;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let patched_args = pwstore::patch_args(std::env::args());
    let args = cli::Args::parse_from(patched_args);

    let mut cli_headers = HeaderMap::new();
    if let Some(ua) = args.user_agent {
        cli_headers.insert(USER_AGENT, HeaderValue::from_str(&ua)?);
    }

    let client = reqwest::Client::builder()
        .timeout(Duration::from_secs(args.timeout))
        .default_headers(cli_headers)
        .build()?;

    let now = Instant::now();

    let resp = client.get(args.url).send().await?;

    let headers = resp.headers();
    println!("{:#?}", headers);

    let body = match args.without_body {
        true => resp.text().await?,
        false => "".to_string(),
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
