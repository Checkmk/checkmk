// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use std::time::{Duration, Instant};

use crate::checking::{self, CheckParameters, CheckResult};
use crate::http::request::ProcessedResponse;
use crate::http::{
    client::{self, ClientConfig},
    request::{self, RequestConfig},
};

pub async fn collect_checks(
    client_cfg: ClientConfig,
    request_cfg: RequestConfig,
    check_params: CheckParameters,
) -> Vec<CheckResult> {
    let response = perform_request(client_cfg, request_cfg).await;

    checking::collect_response_checks(response, check_params)
}

async fn perform_request(
    client_cfg: ClientConfig,
    request_cfg: RequestConfig,
) -> Result<(ProcessedResponse, Duration), reqwest::Error> {
    let client = client::build(client_cfg)?;
    let now = Instant::now();
    let response = request::send(client, request_cfg).await?;
    let elapsed = now.elapsed();
    Ok((response, elapsed))
}
