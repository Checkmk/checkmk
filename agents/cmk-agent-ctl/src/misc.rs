// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

#[cfg(windows)]
use is_elevated::is_elevated;

use anyhow::Error as AnyhowError;

pub fn anyhow_error_to_human_redable(err: &AnyhowError) -> String {
    err.chain()
        .map(|e| e.to_string())
        .collect::<Vec<String>>()
        .join("\n")
}

#[cfg(windows)]
pub fn validate_elevation<F>(mut on_error: F)
where
    F: FnMut(),
{
    if !is_elevated() {
        on_error();
    }
}

#[cfg(test)]
mod test {
    use super::*;
    use anyhow::anyhow;

    #[test]
    fn test_anyhow_error_to_string() {
        assert_eq!(
            anyhow_error_to_human_redable(&anyhow!("something went wrong").context("some context")),
            "some context\nsomething went wrong"
        )
    }
}
