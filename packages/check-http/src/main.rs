use http::{HeaderMap, HeaderValue};
use clap::Parser;
mod cli;
use reqwest::header::USER_AGENT;
use std::time::{Duration, Instant};


#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args = cli::Args::parse();

    let mut cli_headers = HeaderMap::new();
    if let Some(ua) = args.user_agent {
        cli_headers.insert(USER_AGENT, HeaderValue::from_str(&ua)?);
    }

    let client = reqwest::Client::builder()
        .timeout(Duration::from_secs(args.timeout))
        .default_headers(cli_headers)
        .build()?;

    let now = Instant::now();

    let resp = client
        .get(args.url)
        .send()
        .await?;

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
