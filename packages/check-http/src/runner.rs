// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use crate::checking_types::CheckResult;
use crate::checks::{self, CheckParameters};
use crate::http::{self, ClientConfig, RequestConfig};

pub async fn collect_checks(
    client_cfg: ClientConfig,
    request_cfg: RequestConfig,
    check_params: CheckParameters,
) -> Vec<CheckResult> {
    let url = request_cfg.url.clone();
    let response = http::perform_request(client_cfg, request_cfg).await;
    checks::collect_response_checks(url, response, check_params)
}
