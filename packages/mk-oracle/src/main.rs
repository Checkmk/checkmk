// Copyright (C) 2025 Checkmk GmbH
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
//
// SPDX-License-Identifier: Apache-2.0
use mk_oracle::ora_sql::detect::{dump_detected_sids, get_local_sid_names};
use mk_oracle::{args::Args, config, emit, setup};

use clap::Parser;

#[tokio::main]
async fn main() {
    let cli = Args::parse();
    if let Some(input) = &cli.migrate_config {
        #[cfg(not(windows))]
        let dir = cli.migrate_subdir;
        #[cfg(windows)]
        let dir: Option<std::path::PathBuf> = None;
        let code = match config::migration::migrate(input, dir.as_deref()) {
            Ok(yml) => match &cli.migrate_output {
                Some(output) => match std::fs::write(output, &yml) {
                    Ok(()) => 0,
                    Err(e) => {
                        eprintln!("Cannot write {}: {e}", output.display());
                        1
                    }
                },
                None => {
                    print!("{yml}");
                    0
                }
            },
            Err(e) => {
                // `{e:#}` prints the context chain, so the offending config file
                // and the underlying cause are both visible.
                eprintln!("Migration failed: {e:#}");
                1
            }
        };
        std::process::exit(code);
    }

    let args: Vec<String> = std::env::args().collect();
    let result = setup::init(std::env::args_os());
    let code = if let Ok((config, environment)) = result {
        if let Some(p) = environment.generate_plugins() {
            let ora_sql = config.ora_sql().unwrap();
            std::process::exit(setup::create_plugins(
                p,
                ora_sql.cache_age(),
                ora_sql.custom_metrics_cache_age(),
            ));
        };

        if let Some(ora_sql) = config.ora_sql() {
            log::info!("Sandbox needed: {}", ora_sql.need_sandbox());
        }

        if environment.detect_sids() || environment.find_runtime() {
            run_utility_command(&config, &environment)
        } else if environment.runtime_ready() {
            // the parent process has already prepared the environment
            execute(config, environment).await
        } else {
            // Select the Oracle client and the ORACLE_HOME that goes with it,
            // export both, and re-run ourselves: the child sees
            // --runtime-ready and executes the actual monitoring. The re-run
            // is what makes the library search path take effect, since the
            // dynamic loader reads it once, when a process starts.
            match setup::detect_runtime_env(&config) {
                Err(e) => report_fatal_error(e),
                Ok(runtime_env) => match setup::apply_runtime_env(&runtime_env, None, None) {
                    None => report_fatal_error("No Oracle client runtime found"),
                    Some(old_path) => {
                        // old_path is the search path as it was before the runtime was
                        // prepended; it is kept so that reset_env can restore it.
                        log::info!(
                            "Spawn new process {args:?}, previous {}={old_path:?}",
                            setup::RUNTIME_PATH_ENV_VAR
                        );
                        setup::spawn_new_process(args, old_path)
                    }
                },
            }
        }
    } else {
        report_fatal_error(result.err().unwrap())
    };
    std::process::exit(code);
}

/// Handles --detect-sids and --find-runtime: reports on stdout what the
/// monitoring run would work with, without touching the environment.
fn run_utility_command(config: &config::OracleConfig, environment: &setup::Env) -> i32 {
    if config.ora_sql().is_none() {
        setup::display_and_log("No Config");
        return 1;
    }
    if environment.detect_sids() {
        print!("{}", dump_detected_sids());
        return 0;
    }
    let runtime_env = match setup::detect_runtime_env(config) {
        Ok(runtime_env) => runtime_env,
        Err(e) => {
            setup::display_and_log(e);
            return 1;
        }
    };
    let current = std::env::var(setup::RUNTIME_PATH_ENV_VAR).unwrap_or_default();
    print!("{}", setup::format_runtime_env(&runtime_env, &current));
    0
}

fn log_current_env_var(name: &str) {
    let value = std::env::var(name).unwrap_or_default();
    if !value.is_empty() {
        log::info!("Current {name}={value}");
    }
}

async fn execute(config: config::OracleConfig, environment: setup::Env) -> i32 {
    log_current_env_var(setup::RUNTIME_PATH_ENV_VAR);
    log_current_env_var(setup::ORACLE_HOME_ENV_VAR);
    match config.exec(&environment).await {
        Ok(output) => {
            print!("{output}");
            log::info!("Successfully executed");
            0
        }
        Err(e) => report_fatal_error(e),
    }
}

fn report_fatal_error(e: impl std::fmt::Display) -> i32 {
    setup::display_and_log(&e);
    print!(
        "{}",
        emit::fatal_error_section(&get_local_sid_names(), &e.to_string())
    );
    1
}
