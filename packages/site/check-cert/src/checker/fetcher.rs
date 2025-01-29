// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use crate::check::{pretty_levels, Check, CheckResult, Levels, Metric, Real};
use std::time::Duration;
use typed_builder::TypedBuilder;

#[derive(Debug, TypedBuilder)]
#[builder(field_defaults(default))]
pub struct Config {
    response_time: Option<Levels<Duration>>,
}

pub fn check(response_time: Duration, config: Config) -> Check {
    Check::from(&mut vec![check_response_time(
        response_time,
        config.response_time,
    )
    .unwrap_or_default()])
}

fn check_response_time(
    response_time: Duration,
    levels: Option<Levels<Duration>>,
) -> Option<CheckResult<Real>> {
    levels.map(|levels| {
        CheckResult::notice_from_levels(
            pretty_levels(
                &format!("Response time: {} ms", response_time.as_millis()),
                levels.clone().map(|x| Real::from(x.as_millis() as isize)),
                "ms",
            ),
            Metric::builder()
                .label("overall_response_time")
                .value(response_time)
                .uom("s".parse().unwrap())
                .levels(Some(levels))
                .build()
                .map(|x| Real::from(x.as_secs_f64())),
        )
    })
}
