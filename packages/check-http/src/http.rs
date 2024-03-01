use std::{
    sync::{Arc, Mutex},
    time::{Duration, Instant},
};

pub use client::{ClientConfig, ForceIP, OnRedirect};
pub use request::{Body, ProcessedResponse, RequestConfig};
use reqwest::Url;

mod client;
mod request;

pub async fn perform_request(
    client_cfg: ClientConfig,
    request_cfg: RequestConfig,
) -> Result<(ProcessedResponse, Duration), reqwest::Error> {
    let record_redirect = Arc::new(Mutex::<Option<Url>>::new(None));
    let client = client::build(client_cfg, record_redirect.clone())?;
    let now = Instant::now();
    let response = request::send(client, request_cfg, record_redirect).await?;
    let elapsed = now.elapsed();
    Ok((response, elapsed))
}
