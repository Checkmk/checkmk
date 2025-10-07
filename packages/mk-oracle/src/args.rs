// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use crate::types::SectionFilter;
use crate::version;
use clap::Parser;
use std::path::PathBuf;

#[derive(Parser, Default)]
#[command(about = "Oracle plugin.", version = version::VERSION)]
pub struct Args {
    /// Enable verbose output. Use once (-v) for logging level DEBUG and twice (-vv) for logging
    /// level TRACE.
    #[arg(short, long, action = clap::ArgAction::Count)]
    pub verbose: u8,

    /// Sends log to stderr.
    #[arg(short = 'l', long)]
    pub display_log: bool,
    /// Prints config, parameters, important variables into the log file
    #[arg(long)]
    pub print_info: bool,

    /// Use custom log dir
    #[arg(long)]
    pub log_dir: Option<PathBuf>,

    /// Use custom temp dir
    #[arg(long)]
    pub temp_dir: Option<PathBuf>,

    /// Use custom state dir
    #[arg(long)]
    pub state_dir: Option<PathBuf>,

    /// All sections are generated as sync
    #[arg(long)]
    pub no_spool: bool,

    /// Use custom config file
    #[arg(short, long)]
    pub config_file: Option<PathBuf>,

    #[arg(long)]
    pub detect_only: bool,

    /// Prepared runtime status, If yes skip setting PATH LD_LIBRARY_PATH, whatever
    #[arg(long)]
    pub runtime_ready: bool,

    /// Select which sections to execute.
    /// If not specified, all sections are executed.
    /// Use `all` to run all sections.
    /// Use `sync` to run only synchronous sections.
    /// Use `async` to run only asynchronous sections
    #[arg(short, long)]
    pub filter: Option<SectionFilter>,

    /// Create plugins in the given directory and exit
    /// The directory must exist
    /// Linux: async plugin will be created in corresponding subdir
    /// Windows: entry will be added to the bakery file
    #[arg(short, long)]
    pub generate_plugins: Option<PathBuf>,
}

impl Args {
    pub fn logging_level(&self) -> Option<log::Level> {
        match self.verbose {
            2.. => Some(log::Level::Trace),
            1 => Some(log::Level::Debug),
            _ => None,
        }
    }
}
