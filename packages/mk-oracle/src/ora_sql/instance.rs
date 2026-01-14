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

use crate::config::{self, OracleConfig};
use crate::ora_sql::backend::{make_custom_spot, make_spot, ClosedSpot, Opened, OpenedSpot, Spot};
use crate::ora_sql::custom::get_sql_dir;
use crate::ora_sql::section::Section;
use crate::ora_sql::system::WorkInstances;
use crate::setup::{detect_runtime, Env};
use crate::types::{InstanceName, SqlBindParam, SqlQuery, UseHostClient};
use std::collections::HashSet;

use crate::config::connection::add_tns_admin_to_env;
use crate::config::defines::defaults::SECTION_SEPARATOR;
use crate::config::ora_sql::CustomService;
use crate::platform::get_local_instances;
use anyhow::{Context, Result};
use std::sync::{Arc, Mutex};

impl OracleConfig {
    pub async fn exec(&self, environment: &Env) -> Result<String> {
        if let Some(ora_sql) = self.ora_sql() {
            if environment.detect_only() {
                return Ok(dump_local_instances());
            }
            if environment.find_runtime() {
                let use_host_client: UseHostClient = ora_sql.options().use_host_client().clone();
                return Ok(detect_runtime(&use_host_client, None)
                    .map(|t| format!("{:?}", t))
                    .unwrap_or_else(|| {
                        log::error!("Error detecting runtime");
                        "Error detecting runtime".to_string()
                    }));
            }
            log::info!("Generating main data");
            let mut output: Vec<String> = Vec::new();
            output.extend(
                generate_data(ora_sql, environment)
                    .await
                    .unwrap_or_else(|e| {
                        log::error!("Error generating data at main config: {e}");
                        vec![format!("{e}\n")]
                    }),
            );
            for (num, config) in std::iter::zip(0.., ora_sql.configs()) {
                log::info!("Generating configs data");
                let configs_data = generate_data(config, environment)
                    .await
                    .unwrap_or_else(|e| {
                        log::error!("Error generating data at config {num}: {e}");
                        vec![format!("{e}\n")]
                    });
                output.extend(configs_data);
            }
            // on Linux we must supply CR
            let mut x = output.join("\n");
            if !x.ends_with('\n') {
                x.push('\n');
            }
            Ok(x)
        } else {
            log::error!("No config");
            anyhow::bail!("No Config")
        }
    }
}

fn dump_local_instances() -> String {
    let instances = get_local_instances().unwrap_or_else(|e| {
        log::error!("{:?}", e);
        vec![]
    });
    let rows = instances
        .iter()
        .map(|i| {
            format!(
                "'{:16}': home={:60} base={:60}",
                i.name,
                i.home.display().to_string(),
                i.base.display().to_string()
            )
        })
        .collect::<Vec<String>>()
        .join("\n");
    format!("{}\nTotal instances found: {}\n", rows, instances.len())
}

type InstanceWorks = (InstanceName, Vec<(Vec<SqlQuery>, String)>);
type SpotWorks = (ClosedSpot, Vec<InstanceWorks>);

/// Generate data as defined by config
/// Consists from two parts: instance entries + sections for every instance
pub async fn generate_data(
    ora_sql: &config::ora_sql::Config,
    environment: &Env,
) -> Result<Vec<String>> {
    // we need to set TNS_ADMIN for Oracle client for the case alias is used
    add_tns_admin_to_env(ora_sql.conn());

    // TODO: detect instances
    // TODO: apply to config detected instances
    // TODO: customize instances
    // TODO: resulting in the list of endpoints

    let all = calc_all_spots(vec![ora_sql.endpoint()], ora_sql.instances());
    let all = filter_spots(all, ora_sql.discovery());
    let connected = connect_spots(all, None);

    let sections = ora_sql
        .product()
        .sections()
        .iter()
        .filter_map(|s| {
            if !s.is_allowed(environment.execution()) {
                log::info!(
                    "Skip section: {:?} not allowed in {:?}",
                    s,
                    environment.execution()
                );
                return None;
            }
            let s = Section::new(s, ora_sql.product().cache_age());
            Some(s)
        })
        .collect::<Vec<_>>();
    let mut output: Vec<String> = sections
        .iter()
        .filter_map(|s| s.to_signaling_header())
        .collect();
    let works = make_spot_works(connected, sections, ora_sql.params());
    if ora_sql.options().threads() > 1 {
        output.extend(process_spot_works_para(works, ora_sql.options().threads()));
    } else {
        output.extend(process_spot_works(works));
    }
    Ok(output)
}

fn make_spot_works(
    spots: Vec<OpenedSpot>,
    sections: Vec<Section>,
    params: &[SqlBindParam],
) -> Vec<SpotWorks> {
    spots
        .into_iter()
        .map(|spot| {
            let instances = WorkInstances::new(&spot, None);
            let closed = spot.close();
            let instance_works = instances
                .all()
                .keys()
                .filter_map(|instance| {
                    if let Some(info) = instances.get_info(instance) {
                        Some((instance, info))
                    } else {
                        log::warn!("No info found for instance: {}", instance);
                        None
                    }
                })
                .map(|(service, info)| {
                    let queries = sections
                        .iter()
                        .filter_map(|section| {
                            if !service.is_suitable_affinity(section.affinity()) {
                                log::info!(
                                    "Skip section with not suitable affinity: {:?} instance {}",
                                    section,
                                    service
                                );
                                return None;
                            }
                            section
                                .find_queries(get_sql_dir(), info.0, info.1, params)
                                .map(|q| (q, section.to_work_header()))
                        })
                        .collect::<Vec<(Vec<SqlQuery>, String)>>();
                    (service.clone(), queries)
                })
                .collect::<Vec<InstanceWorks>>();
            (closed, instance_works)
        })
        .collect::<Vec<SpotWorks>>()
}

fn process_spot_works(works: Vec<SpotWorks>) -> Vec<String> {
    works
        .into_iter()
        .flat_map(|(spot, instance_works)| {
            log::info!("Spot: {:?}", spot.target());
            instance_works
                .iter()
                .flat_map(|(instance, queries)| {
                    log::info!("Instance: {}", instance);
                    let r = spot.clone().connect(Some(instance));
                    match r {
                        Ok(opened) => queries
                            .iter()
                            .map(|(query, title)| {
                                log::info!("Query: {}", title);
                                let mut results = vec![title.clone()];
                                results.extend(_exec_queries(&opened, instance, query));
                                results.join("\n")
                            })
                            .collect::<Vec<String>>(),
                        Err(e) => {
                            log::error!("Failed to connect to instance {}: {}", instance, e);
                            vec![] // Skip this instance if connection fails
                        }
                    }
                })
                .collect::<Vec<_>>()
        })
        .collect::<Vec<_>>()
}

fn process_spot_works_para(works: Vec<SpotWorks>, threads: usize) -> Vec<String> {
    let threads = threads.clamp(1, MAX_THREAD_COUNT);
    works
        .into_iter()
        .flat_map(|(spot, instance_works)| {
            log::info!("Spot: {:?}", spot.target());
            instance_works
                .iter()
                .flat_map(|(instance, queries)| {
                    log::info!("Instance: {}", instance);
                    let spots = open_spots(&spot, instance, threads);
                    if spots.is_empty() {
                        log::error!("Failed to connect to instance {}", instance);
                        return vec![];
                    }
                    let job_data: Vec<JobData> = make_job_data(spots, queries);
                    let thread_pool = build_thread_pool(threads);
                    let global_output = Arc::new(Mutex::new(Vec::new()));
                    thread_pool.scope(|scope| {
                        for job in job_data {
                            let thread_output = Arc::clone(&global_output);
                            scope.spawn(move |_| {
                                let result = job
                                    .blocks
                                    .iter()
                                    .flat_map(|block| {
                                        let (queries, title) = block;
                                        log::debug!("Executing queries for instance: {}", instance);
                                        _exec_queries_on_spot(
                                            &job.spot,
                                            instance,
                                            queries,
                                            title.as_str(),
                                        )
                                    })
                                    .collect::<Vec<String>>();
                                thread_output.lock().unwrap().extend(result);
                            })
                        }
                    });
                    Arc::try_unwrap(global_output)
                        .unwrap()
                        .into_inner()
                        .unwrap()
                })
                .collect::<Vec<_>>()
        })
        .collect::<Vec<_>>()
}

fn open_spots(
    spot: &ClosedSpot,
    instance_name: &InstanceName,
    thread_count: usize,
) -> Vec<OpenedSpot> {
    std::iter::repeat_with(|| spot.clone().connect(Some(instance_name)))
        .take(thread_count)
        .filter_map(|r| match r {
            Ok(conn) => Some(conn),
            Err(e) => {
                log::error!("Failed to connect to instance {}: {}", instance_name, e);
                None
            }
        })
        .collect::<Vec<_>>()
}

fn build_thread_pool(threads: usize) -> rayon::ThreadPool {
    rayon::ThreadPoolBuilder::new()
        .num_threads(threads)
        .build()
        .context("Failed to build thread pool")
        .unwrap()
}

/// builds a table [(OpenedSpot, ([Query, ...], Title)), ...]
fn make_job_data(spots: Vec<Spot<Opened>>, queries: &[(Vec<SqlQuery>, String)]) -> Vec<JobData> {
    let job_count = spots.len();
    let chunk_size = queries.len().div_ceil(job_count);
    let query_chunks = queries.chunks(chunk_size);
    println!(
        "{} {} {} {}",
        queries.len(),
        job_count,
        chunk_size,
        query_chunks.len()
    );
    spots
        .into_iter()
        .zip(query_chunks)
        .map(|(spot, chunk)| JobData {
            spot,
            blocks: chunk.to_vec(),
        })
        .collect::<Vec<_>>()
}

/// Execute queries on an opened spot and return results with title headers ahead
fn _exec_queries_on_spot(
    spot: &Spot<Opened>,
    instance_name: &InstanceName,
    queries: &[SqlQuery],
    title: &str,
) -> Vec<String> {
    queries
        .iter()
        .flat_map(|query| {
            log::debug!("Executing query: {}", query.as_str());
            let mut result = spot
                .query_table(query)
                .format(&SECTION_SEPARATOR.to_string())
                .unwrap_or_else(|e| {
                    log::error!(
                        "Failed to execute query for instance {}: {}",
                        instance_name,
                        e
                    );
                    vec![e.to_string()]
                });
            result.insert(0, title.to_string());
            result
        })
        .collect::<Vec<String>>()
}

const MAX_THREAD_COUNT: usize = 8;

struct JobData {
    spot: Spot<Opened>,
    blocks: Vec<(Vec<SqlQuery>, String)>,
}

fn _exec_queries(
    spot: &OpenedSpot,
    service_name: &InstanceName,
    queries: &[SqlQuery],
) -> Vec<String> {
    log::info!("Connected to : {}", service_name);
    queries
        .iter()
        .flat_map(|query| {
            log::debug!("Executing query: {}", query.as_str());
            let result = spot
                .query_table(query)
                .format(&SECTION_SEPARATOR.to_string())
                .unwrap_or_else(|e| {
                    log::error!(
                        "Failed to execute query for instance {}: {}",
                        service_name,
                        e
                    );
                    vec![e.to_string()]
                });
            result
        })
        .collect::<Vec<_>>()
}

// tested only in integration tests
fn connect_spots(spots: Vec<ClosedSpot>, service_name: Option<&InstanceName>) -> Vec<OpenedSpot> {
    let connected = spots
        .into_iter()
        .filter_map(|t| match t.connect(service_name) {
            Ok(opened) => {
                log::info!("Connected to instance: {:?}", &opened.target());
                Some(opened)
            }
            Err(e) => {
                log::error!("Error connecting to instance: {}", e);
                None
            }
        })
        .collect::<Vec<OpenedSpot>>();
    log::info!(
        "CONNECTED SPOTS: {:?}",
        connected.iter().map(|t| t.target()).collect::<Vec<_>>()
    );

    connected
}

fn calc_all_spots(
    endpoints: Vec<config::ora_sql::Endpoint>,
    instances: &[CustomService],
) -> Vec<ClosedSpot> {
    let mut all = calc_main_spots(endpoints);
    all.extend(calc_custom_spots(instances));
    all
}

fn filter_spots(spots: Vec<ClosedSpot>, discovery: &config::ora_sql::Discovery) -> Vec<ClosedSpot> {
    let include: HashSet<&String> = HashSet::from_iter(discovery.include());
    let exclude: HashSet<&String> = if include.is_empty() {
        HashSet::from_iter(discovery.exclude())
    } else {
        HashSet::new()
    };
    spots
        .into_iter()
        .filter(|spot| {
            let service_name: String = spot
                .target()
                .service_name
                .clone()
                .unwrap_or_default()
                .into();
            let uppercased_name: String = service_name.to_uppercase();
            if !include.is_empty() {
                return include.contains(&uppercased_name);
            } else if !exclude.is_empty() {
                return !exclude.contains(&uppercased_name);
            }
            true
        })
        .collect()
}

fn calc_main_spots(endpoints: Vec<config::ora_sql::Endpoint>) -> Vec<ClosedSpot> {
    log::info!("ENDPOINTS: {:?}", endpoints);
    endpoints
        .into_iter()
        .filter_map(|ep| {
            make_spot(&ep).map_or_else(
                |error| {
                    log::error!("Error creating spot for endpoint {error}");
                    None
                },
                Some,
            )
        })
        .collect::<Vec<ClosedSpot>>()
}

fn calc_custom_spots(instances: &[CustomService]) -> Vec<ClosedSpot> {
    log::info!("CUSTOM INSTANCES: {:?}", instances);
    instances
        .iter()
        .filter_map(|instance| {
            make_custom_spot(instance).map_or_else(
                |error| {
                    log::error!("Error creating spot for endpoint {error}");
                    None
                },
                Some,
            )
        })
        .collect::<Vec<ClosedSpot>>()
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::config::ora_sql::Discovery;
    use crate::config::yaml::test_tools::create_yaml;
    use crate::types::ServiceName;

    #[test]
    fn test_calc_spots() {
        assert!(calc_main_spots(vec![]).is_empty());
        let all = calc_main_spots(vec![
            config::ora_sql::Endpoint::default(),
            config::ora_sql::Endpoint::default(),
        ]);
        assert_eq!(all.len(), 2);
    }
    fn make_instance(service_name: &str) -> config::ora_sql::CustomService {
        config::ora_sql::CustomService::new(
            ServiceName::from(service_name),
            config::authentication::Authentication::default(),
            config::connection::Connection::default(),
            None,
            None,
            None,
        )
    }
    #[test]
    fn test_calc_custom_spots() {
        assert!(calc_custom_spots(&[]).is_empty());
        let all = calc_custom_spots(&[make_instance("A"), make_instance("B")]);
        assert_eq!(all.len(), 2);
        assert_eq!(
            all[0].target().service_name.as_ref().unwrap(),
            &ServiceName::from("A")
        );
        assert_eq!(
            all[1].target().service_name.as_ref().unwrap(),
            &ServiceName::from("B")
        );
    }

    fn make_instance_with_custom_conn(service_name: &str) -> config::ora_sql::CustomService {
        config::ora_sql::CustomService::new(
            ServiceName::from(service_name),
            config::authentication::Authentication::default(),
            config::connection::Connection::from_yaml(&create_yaml(
                "connection:\n    service_name: X",
            ))
            .unwrap()
            .unwrap(),
            None,
            None,
            None,
        )
    }
    #[test]
    fn test_calc_custom_spot_with_custom_conn() {
        assert!(calc_custom_spots(&[]).is_empty());
        let all = calc_custom_spots(&[
            make_instance_with_custom_conn("A"),
            make_instance_with_custom_conn("B"),
        ]);
        assert_eq!(all.len(), 2);
        assert_eq!(
            all[0].target().service_name.as_ref().unwrap(),
            &ServiceName::from("X")
        );
        assert_eq!(
            all[1].target().service_name.as_ref().unwrap(),
            &ServiceName::from("X")
        );
    }
    #[test]
    fn test_filter_spots() {
        let all = calc_all_spots(
            vec![config::ora_sql::Endpoint::default()],
            &[make_instance("A"), make_instance("B")],
        );
        assert_eq!(all.len(), 3);
        let d = Discovery::default();
        assert_eq!(filter_spots(all.clone(), &d).len(), 3);
        let d = Discovery::new(false, vec!["".to_string()], vec![]);
        assert_eq!(filter_spots(all.clone(), &d).len(), 1);
        let d = Discovery::new(
            false,
            vec!["".to_string(), "A".to_string(), "x".to_string()], // 2 left
            vec!["".to_string(), "A".to_string(), "B".to_string()], // ignored
        );
        assert_eq!(filter_spots(all.clone(), &d).len(), 2);
        let d = Discovery::new(
            false,
            vec![],                                                 // 2 left
            vec!["".to_string(), "A".to_string(), "B".to_string()], // ignored
        );
        assert_eq!(filter_spots(all.clone(), &d).len(), 0);
        let d = Discovery::new(
            false,
            vec![],                                 // 2 left
            vec!["A".to_string(), "B".to_string()], // ignored
        );
        assert_eq!(filter_spots(all.clone(), &d).len(), 1);
    }
}
