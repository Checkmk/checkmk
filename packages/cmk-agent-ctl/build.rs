// Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

/// Inject CMK_VERSION into the build as a compile-time env var.
///
/// Bazel builds don't use this: file_from_flag replaces src/version.rs entirely.
/// Cargo builds (AIX, Solaris, Windows) use this to override the fallback version
/// in src/version.rs via option_env!("CMK_VERSION").
///
/// CI sets CMK_VERSION before invoking ./run or run.cmd.
/// Local builds without CMK_VERSION get the hardcoded fallback from version.rs.
fn main() {
    println!("cargo:rerun-if-env-changed=CMK_VERSION");
    if let Ok(v) = std::env::var("CMK_VERSION") {
        let v = v.replace(['\'', '"'], "");
        if !v.is_empty() {
            println!("cargo:rustc-env=CMK_VERSION={v}");
        }
    }
}
