// Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.
use mk_oracle::setup;

#[tokio::main]
async fn main() {
    let args: Vec<String> = std::env::args().collect();
    let result = setup::init(std::env::args_os());
    let code = if let Ok((config, environment)) = result {
        if let Some(p) = environment.generate_plugins() {
            log::info!("PLUGINS GENERATED for path {p:?}");
            let cache_age = config.ora_sql().unwrap().cache_age();
            if cfg!(windows) {
                setup::create_plugin("oracle_unified_sync.ps1", p, None);
                setup::create_plugin("oracle_unified_async.ps1", p, Some(cache_age));
            } else {
                setup::create_plugin("oracle_unified_sync", p, None);
                setup::create_plugin("oracle_unified_async", p, Some(cache_age));
            }

            if p.is_dir() {
                log::info!("PLUGINS DIR={}", p.display());
            } else {
                log::info!("{} is not a directory", p.display());
                std::process::exit(1);
            }
            std::process::exit(0);
        };

        if args.contains(&"--runtime-ready".to_string()) {
            log::info!("SKIP RUNTIME ADDING");
            log::info!("Current PATH={}", std::env::var("PATH").unwrap_or_default());
            log::info!(
                "Current LD_LIBRARY_PATH={}",
                std::env::var("LD_LIBRARY_PATH").unwrap_or_default()
            );
            match config.exec(&environment).await {
                Ok(output) => {
                    print!("{output}");
                    log::info!("Success");
                    0
                }
                Err(e) => {
                    display_and_log(e);
                    1
                }
            }
        } else if let Some(old_path) = setup::add_runtime_path_to_env(&config, None, None) {
            log::info!("Spawn new process");
            spawn_new_process(args, old_path)
        } else {
            log::error!("No runtime");
            1
        }
    } else {
        display_and_log(result.err().unwrap());
        1
    };
    std::process::exit(code);
}

fn display_and_log(e: impl std::fmt::Display) {
    log::error!("{e}",);
    eprintln!("Stop on error: `{e}`",);
}

fn spawn_new_process(args: Vec<String>, old_path: std::path::PathBuf) -> i32 {
    let mut new_args = args.clone();
    new_args.push("--runtime-ready".to_string());
    let exe = std::env::current_exe().expect("Failed to get current exe");
    let status = std::process::Command::new(exe)
        .args(&new_args[1..]) // skip the old program name
        .status()
        .unwrap_or_else(|e| {
            display_and_log(e);
            setup::reset_env(&old_path, None);
            std::process::exit(1);
        });
    setup::reset_env(&old_path, None);
    status.code().unwrap_or_default()
}
