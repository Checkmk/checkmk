// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

mod cli;
mod config;
mod marcv_api;
mod monitoring_data;
mod uuid;
use std::io::{self, Result as IOResult, Write};
use std::path::Path;
use structopt::StructOpt;

fn register(config: config::Config, path_state: &Path) {
    let marcv_addresses = config
        .marcv_addresses
        .expect("Server addresses not specified");
    let identifier = config.uuid.unwrap_or(uuid::make());
    match marcv_api::register(&marcv_addresses[0], &identifier) {
        Ok(message) => println!("{}", message),
        Err(error) => panic!("Error during registration: {}", error),
    }
    match (config::Config {
        marcv_addresses: Option::from(marcv_addresses),
        uuid: Option::from(identifier),
        package_name: config.package_name,
    }
    .to_file(path_state))
    {
        Err(error) => panic!(
            "Error while saving state file after registration: {}",
            error
        ),
        _ => {}
    }
}

fn push(config: config::Config) {
    let marcv_addresses = config
        .marcv_addresses
        .expect("Server addresses not specified");
    let identifier = config.uuid.expect("UUID not set");
    match monitoring_data::collect(&config.package_name) {
        Ok(mon_data) => match marcv_api::agent_data(&marcv_addresses[0], &identifier, mon_data) {
            Ok(message) => println!("{}", message),
            Err(error) => panic!("Error pushing monitoring data: {}", error),
        },
        Err(error) => panic!("Error collecting monitoring data: {}", error),
    }
}

fn dump(config: config::Config) {
    match monitoring_data::collect(&config.package_name) {
        Ok(mon_data) => match io::stdout().write_all(&mon_data) {
            Err(error) => panic!("Error writing monitoring data to stdout: {}", error),
            _ => {}
        },
        Err(error) => panic!("Error collecting monitoring data: {}", error),
    }
}

fn status(_config: config::Config) {
    panic!("Status mode not yet implemented")
}

fn get_configuration(
    path_config: &Path,
    path_state: &Path,
    args: cli::Args,
) -> IOResult<config::Config> {
    return Ok(config::Config::merge_two_configs(
        config::Config::merge_two_configs(
            config::Config::from_file(path_state)?,
            config::Config::from_file(path_config)?,
        ),
        config::Config::from_args(args),
    ));
}

fn main() {
    let path_state_file = Path::new("state.json");
    let args = cli::Args::from_args();
    let mode = String::from(&args.mode);

    match get_configuration(&Path::new("config.json"), &path_state_file, args) {
        Ok(config) => match mode.as_str() {
            "dump" => dump(config),
            "register" => register(config, &path_state_file),
            "push" => push(config),
            "status" => status(config),
            _ => {
                panic!("Invalid mode: {}", mode)
            }
        },
        Err(error) => panic!("Error while obtaining configuration: {}", error),
    }
}
