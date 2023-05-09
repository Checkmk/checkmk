// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use anyhow::Error as AnyhowError;

pub fn anyhow_error_to_human_readable(err: &AnyhowError) -> String {
    err.chain()
        .map(|e| e.to_string())
        .collect::<Vec<String>>()
        .join("\n")
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
