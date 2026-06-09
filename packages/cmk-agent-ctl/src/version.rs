// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

// Bazel replaces this file entirely via file_from_flag.
// Cargo uses this as-is: CMK_VERSION env overrides the fallback at compile time.
pub const VERSION: &str = match option_env!("CMK_VERSION") {
    Some(v) => v,
    None => "2.5.0b1",
};
