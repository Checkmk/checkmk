// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

mod certs;
mod cli;
mod config;
mod marcv_api;
mod monitoring_data;
mod uuid;
use config::RegistrationState;
use std::io::{self, Write};
use std::path::Path;
use structopt::StructOpt;

fn register(config: config::Config, mut reg_state: RegistrationState, path_state_out: &Path) {
    let marcv_addresses = config
        .marcv_addresses
        .expect("Server addresses not specified");

    for marcv_address in marcv_addresses {
        // TODO: what if registration_state.contains_key(marcv_address) (already registered)?
        let root_cert = match &config.root_certificate {
            Some(cert) => cert.clone(),
            None => match certs::fetch_root_cert(&marcv_address) {
                Ok(cert) => cert,
                Err(error) => panic!("Error establishing trust with marcv: {}", error),
            },
        };

        let (csr, private_key) = match certs::make_csr(&reg_state.uuid) {
            Ok(data) => data,
            Err(error) => panic!("Error creating CSR: {}", error),
        };
        let certificate =
            // TODO: geht username and passsword from config
            match marcv_api::register(&marcv_address, &root_cert, csr, "cmkadmin", "cmk") {
                Ok(cert) => cert,
                Err(error) => panic!("Error registering at {}: {}", &marcv_address, error),
            };

        let client_chain = private_key + &certificate;

        reg_state.server_specs.insert(
            marcv_address,
            config::ServerSpec {
                client_chain,
                root_cert,
            },
        );
    }

    reg_state.to_file(path_state_out).unwrap();
}

fn push(config: config::Config, reg_state: config::RegistrationState) {
    match monitoring_data::collect(config.package_name) {
        Ok(mon_data) => {
            for (marcv_address, server_spec) in reg_state.server_specs.iter() {
                // TODO: Find a way we don't have to clone the mon_data (lifetimes?)
                match marcv_api::agent_data(
                    &reg_state.uuid,
                    marcv_address,
                    server_spec,
                    mon_data.clone(),
                ) {
                    Ok(message) => println!("{}", message),
                    Err(error) => panic!("Error pushing monitoring data: {}", error),
                };
            }
        }
        Err(error) => panic!("Error collecting monitoring data: {}", error),
    }
}

fn dump(config: config::Config) {
    match monitoring_data::collect(config.package_name) {
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

fn get_configuration(path_config: &Path, args: cli::Args) -> io::Result<config::Config> {
    return Ok(config::Config::merge_two_configs(
        config::Config::from_file(path_config)?,
        config::Config::from_args(args),
    ));
}

fn get_reg_state(path: &Path) -> io::Result<config::RegistrationState> {
    return Ok(config::RegistrationState::from_file(path)?);
}

fn main() {
    let path_state_file = Path::new("state.json");
    let args = cli::Args::from_args();
    let mode = String::from(&args.mode);

    let config = match get_configuration(&Path::new("config.json"), args) {
        Ok(cfg) => cfg,
        Err(error) => panic!("Error while obtaining configuration: {}", error),
    };

    let reg_state = match get_reg_state(&path_state_file) {
        Ok(cfg) => cfg,
        Err(error) => panic!("Error while obtaining configuration: {}", error),
    };

    match mode.as_str() {
        "dump" => dump(config),
        "register" => register(config, reg_state, &path_state_file),
        "push" => push(config, reg_state),
        "status" => status(config),
        _ => {
            panic!("Invalid mode: {}", mode)
        }
    }
}
