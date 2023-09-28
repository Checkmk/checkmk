use clap::Parser;
use http::{HeaderMap, HeaderValue};
use reqwest;
use reqwest::header::USER_AGENT;
use std::time::{Duration, Instant};

#[derive(Parser, Debug)]
#[command(about = "check_http")]
struct Args {
    /// URL to check
    #[arg(short, long)]
    url: String,

    /// Set timeout in seconds
    #[arg(long, default_value_t = 10)]
    timeout: u64,

    /// Wait for document body
    #[arg(long)]
    without_body: bool,

    /// Set user-agent
    #[arg(long)]
    user_agent: Option<String>,
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args = Args::parse();

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
