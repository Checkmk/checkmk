// Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.
use clap::Parser;
use std::path::PathBuf;

#[derive(Parser)]
#[command(name = "package_validator")]
#[command(version)]
#[command(about = "Validates dependencies for binaries and shared libraries in deb/rpm packages")]
pub(crate) struct Args {
    /// Path to the package file (deb or rpm) to validate.
    pub package: PathBuf,

    /// Path to the file to write the validation results in JSON format.
    pub report: PathBuf,

    #[arg(
        long,
        long_help = "Path to a text file of known system dependencies.\n\
                Each line contains an exact dependency name.\n\
                Empty lines and lines starting with # are ignored."
    )]
    pub system_dependencies: Option<PathBuf>,
}
