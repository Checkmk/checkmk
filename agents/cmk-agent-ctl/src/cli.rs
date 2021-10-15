// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use structopt::StructOpt;

#[derive(StructOpt)]
#[structopt(name = "cmk-agent-ctl", about = "Checkmk agent controller.")]
pub struct Args {
    #[structopt(help = "Execution mode, should be one of 'register', 'push', 'dump', 'status'")]
    pub mode: String,

    #[structopt(long, parse(from_str))]
    pub server: Option<Vec<String>>,

    #[structopt(long, parse(from_str))]
    pub package_name: Option<String>,
}
