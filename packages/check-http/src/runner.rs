// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use std::time::Instant;

use crate::checking::{self, CheckParameters, CheckResult, State};
use crate::connection::{self, ClientConfig};
use crate::http::{self, RequestConfig};

pub async fn collect_checks(
    client_config: ClientConfig,
    request_cfg: RequestConfig,
    check_params: CheckParameters,
) -> Vec<CheckResult> {
    let Ok(client) = connection::get_client(client_config) else {
        return vec![CheckResult::summary(State::Unknown, "Error building the request").unwrap()];
    };

    let now = Instant::now();
    let response = match http::perform_request(client, request_cfg).await {
        Ok(resp) => resp,
        Err(err) => {
            if err.is_timeout() {
                return vec![CheckResult::summary(State::Crit, "timeout").unwrap()];
            } else if err.is_connect() {
                return vec![CheckResult::summary(State::Crit, "Failed to connect").unwrap()];
            } else if err.is_redirect() {
                return vec![CheckResult::summary(State::Crit, &err.to_string()).unwrap()];
            // Hit one of max_redirs, sticky, stickyport
            } else {
                return vec![
                    CheckResult::summary(State::Unknown, "Error while sending request").unwrap(),
                ];
            }
        }
    };
    let elapsed = now.elapsed();

    checking::collect_response_checks(response, elapsed, check_params)
}
