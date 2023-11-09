// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use std::time::Instant;

use crate::checking::{self, CheckParameters, CheckResult, State};
use crate::connection::ConnectionConfig;
use crate::http::{self, ClientConfig, RequestConfig};

pub async fn collect_checks(
    client_config: ClientConfig,
    connection_cfg: ConnectionConfig,
    request_cfg: RequestConfig,
    check_params: CheckParameters,
) -> Vec<CheckResult> {
    let Ok(request) = http::prepare_request(client_config, connection_cfg) else {
        return vec![CheckResult {
            state: State::Unknown,
            summary: "Error building the request".to_string(),
        }];
    };

    let now = Instant::now();
    let response = match http::perform_request(request, request_cfg).await {
        Ok(resp) => resp,
        Err(err) => {
            if err.is_timeout() {
                return vec![CheckResult {
                    state: State::Crit,
                    summary: "timeout".to_string(),
                }];
            } else if err.is_connect() {
                return vec![CheckResult {
                    state: State::Crit,
                    summary: "Failed to connect".to_string(),
                }];
            } else if err.is_redirect() {
                return vec![CheckResult {
                    state: State::Crit,
                    summary: err.to_string(),
                }];
            // Hit one of max_redirs, sticky, stickyport
            } else {
                return vec![CheckResult {
                    state: State::Unknown,
                    summary: "Error while sending request".to_string(),
                }];
            }
        }
    };
    let elapsed = now.elapsed();

    checking::collect_response_checks(response, elapsed, check_params)
}
