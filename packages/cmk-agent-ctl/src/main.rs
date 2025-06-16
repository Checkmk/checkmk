// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use log::{error, info};
use rustls::crypto::ring::default_provider;

fn main() {
    let (cli, paths) = match cmk_agent_ctl::init(std::env::args_os()) {
        Ok(cli_and_paths) => cli_and_paths,
        Err(error) => {
            return exit_with_error(error);
        }
    };

    info!("starting");
    if let Err(err) = default_provider().install_default() {
        return exit_with_error(err);
    }

    let result = cmk_agent_ctl::run_requested_mode(cli, paths);

    if let Err(error) = &result {
        exit_with_error(error)
    }
}

fn exit_with_error(err: impl std::fmt::Debug) {
    // In case of an error, we want a non-zero exit code and log the error, which
    // goes to stderr under Unix and to stderr and logfile under Windows.

    // In the future, implementing std::process::Termination looks like the right thing to do.
    // However, this trait is still experimental at the moment. See also
    // https://www.joshmcguigan.com/blog/custom-exit-status-codes-rust/
    error!("{:?}", err);
    std::process::exit(1);
}
