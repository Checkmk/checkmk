// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

#[cfg(windows)]
use is_elevated::is_elevated;

use anyhow::Error as AnyhowError;
#[cfg(windows)]
use anyhow::{anyhow, Result as AnyhowResult};

pub fn anyhow_error_to_human_readable(err: &AnyhowError) -> String {
    err.chain()
        .map(|e| e.to_string())
        .collect::<Vec<String>>()
        .join("\n")
}

#[cfg(windows)]
pub fn validate_elevation() -> AnyhowResult<()> {
    const MESSAGE_NOT_ELEVATED: &str =
    "You must be elevated to execute the agent controller. Please, try 'Run as administrator...'";

    if is_elevated() {
        Ok(())
    } else {
        // The elevation elevation may happen at any moment, even when the logger is not ready.
        // Ergo, to avoid strange | duplicated output we write two different message in the log
        // and stderr thus providing correct information for a user
        eprintln!("{}", MESSAGE_NOT_ELEVATED);
        Err(anyhow!("Not elevated, exiting...".to_string()))
    }
}

#[cfg(test)]
mod test {
    use super::*;
    use anyhow::anyhow;

    #[test]
    fn test_anyhow_error_to_human_readable() {
        assert_eq!(
            anyhow_error_to_human_readable(
                &anyhow!("something went wrong").context("some context")
            ),
            "some context\nsomething went wrong"
        )
    }
}
