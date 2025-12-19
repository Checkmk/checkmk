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
use mk_oracle::{config, setup};

#[tokio::main]
async fn main() {
    let args: Vec<String> = std::env::args().collect();
    let result = setup::init(std::env::args_os());
    let code = if let Ok((config, environment)) = result {
        if let Some(p) = environment.generate_plugins() {
            let cache_age = config.ora_sql().unwrap().cache_age();
            std::process::exit(setup::create_plugins(p, cache_age));
        };

        if need_execution(args.as_slice()) {
            execute(config, environment).await
        } else if let Some(old_path) = setup::add_runtime_path_to_env(&config, None, None) {
            log::info!("Spawn new process");
            setup::spawn_new_process(args, old_path)
        } else {
            log::error!("No runtime");
            1
        }
    } else {
        setup::display_and_log(result.err().unwrap());
        1
    };
    std::process::exit(code);
}

fn need_execution(args: &[String]) -> bool {
    ["--detect-only", "--find-runtime", "--runtime-ready"]
        .into_iter()
        .map(String::from)
        .any(|c| args.contains(&c))
}

async fn execute(config: config::OracleConfig, environment: setup::Env) -> i32 {
    let env_var = if cfg!(windows) {
        "PATH"
    } else {
        "LD_LIBRARY_PATH"
    };
    let env_var_value = std::env::var(env_var).unwrap_or_default();
    log::info!("Current {env_var}={env_var_value}");
    match config.exec(&environment).await {
        Ok(output) => {
            print!("{output}");
            log::info!("Success");
            0
        }
        Err(e) => {
            setup::display_and_log(e);
            1
        }
    }
}
