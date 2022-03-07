// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.
use log::{error, info};

fn main() {
    let (args, paths) = match cmk_agent_ctl::init() {
        Ok(args) => args,
        Err(error) => {
            return exit_with_error(error);
        }
    };

    info!("starting");
    let result = cmk_agent_ctl::run_requested_mode(args, paths);

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
