use std::time::{Duration, Instant};

pub use client::{ClientConfig, ForceIP, OnRedirect};
pub use request::{Body, ProcessedResponse, RequestConfig};

mod client;
mod request;

pub async fn perform_request(
    client_cfg: ClientConfig,
    request_cfg: RequestConfig,
) -> Result<(ProcessedResponse, Duration), reqwest::Error> {
    let client = client::build(client_cfg)?;
    let now = Instant::now();
    let response = request::send(client, request_cfg).await?;
    let elapsed = now.elapsed();
    Ok((response, elapsed))
}
