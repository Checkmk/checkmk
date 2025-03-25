pub use client::{ClientConfig, ForceIP, OnRedirect};
pub use request::{Body, ProcessedResponse, RequestConfig};

mod client;
mod request;

pub async fn perform_request(
    client_cfg: ClientConfig,
    request_cfg: RequestConfig,
) -> Result<ProcessedResponse, reqwest::Error> {
    let client = client::ClientAdapter::new(client_cfg)?;
    let response = request::send(client, request_cfg).await?;
    Ok(response)
}
