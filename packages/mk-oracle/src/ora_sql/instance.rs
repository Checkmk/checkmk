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

use crate::config::ora_sql::Piggyback;
use crate::config::{self, OracleConfig};
use crate::emit::{header, piggyback_footer, piggyback_header};
use crate::ora_sql::backend::{
    make_custom_spot, make_spot, sanitize_failure_message, with_container, ClosedSpot, Opened,
    OpenedSpot, Spot,
};
use crate::ora_sql::detect::parse_tns_names_ora;
use crate::ora_sql::perf::{Label, PerfTimer};
use crate::ora_sql::section::Section;
use crate::setup::{
    Env, LOCAL_ORACLE_HOME_TARGETS_ENV_VAR, ORACLE_HOME_ENV_VAR, TNS_ADMIN_ENV_VAR,
};
use crate::types::{InstanceName, LocalInstance, SectionFilter, Sid, SqlQuery};
use std::collections::HashSet;
use std::path::{Path, PathBuf};

use crate::config::authentication::AuthType;
use crate::config::connection::{add_tns_admin_to_env, setup_wallet_environment};
use crate::config::defines::defaults::SECTION_SEPARATOR;
use crate::config::ora_sql::CustomInstance;
use crate::config::section::names;
use crate::ora_sql::spots::{
    make_spot_work_results, ClosedSpotWorks, OpenedSpotWorks, PostProcessing, QueryBlock,
};
use crate::platform::{get_local_instances, get_oracle_home_sids, home_key};
use anyhow::{Context, Result};
use std::sync::Mutex;

/// The alias file both the client and this module look for.
pub const TNS_NAMES_FILE: &str = "tnsnames.ora";

type ClosedSpotResults = (ClosedSpot, Vec<String>);

impl OracleConfig {
    pub async fn exec(&self, environment: &Env) -> Result<String> {
        if let Some(ora_sql) = self.ora_sql() {
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

/// Generate data as defined by config
/// Consists from two parts: instance entries + sections for every instance
pub async fn generate_data(
    ora_sql: &config::ora_sql::Config,
    environment: &Env,
) -> Result<Vec<String>> {
    if let Some(filter) = remap_filter(environment.filter(), ora_sql) {
        // we need to set TNS_ADMIN for Oracle client for the case alias is used
        add_tns_admin_to_env(ora_sql.conn());

        // TODO: detect instances
        // TODO: apply to config detected instances
        // TODO: customize instances
        // TODO: resulting in the list of endpoints

        let all_raw = calc_all_spots(vec![ora_sql.endpoint()], ora_sql.instances());
        let all_raw = filter_spots(all_raw, ora_sql.discovery());
        let local_instances = get_local_instances().unwrap_or_else(|e| {
            log::warn!("Cannot determine the local instances: {e}");
            Vec::new()
        });

        let all = filter_spots_by_oracle_home(all_raw, environment, &local_instances);

        // Set up wallet environment (creates sqlnet.ora with wallet location)
        // Only if tns_admin is NOT explicitly set in config.
        // The auth type is asked per spot: an ASM instance may use wallet auth
        // (`asm_type`) while the regular credentials are standard, and vice versa.
        let tns_admin_explicitly_set = ora_sql.conn().tns_admin().is_some();
        let uses_wallet = ora_sql.auth().auth_type() == &AuthType::Wallet
            || all
                .iter()
                .any(|spot| spot.target().connection_auth().auth_type == AuthType::Wallet);
        if uses_wallet && !tns_admin_explicitly_set {
            if let Err(e) = setup_wallet_environment(None) {
                log::error!("Failed to setup wallet environment: {}", e);
                return Err(e).context("Failed to setup wallet environment");
            }
        }

        let global = if environment.disable_caching() {
            None
        } else {
            Some(ora_sql.product().cache_age())
        };
        let sections = ora_sql
            .product()
            .sections()
            .iter()
            .filter_map(|s| {
                if s.is_allowed(filter) {
                    Some(Section::new(s, global, ora_sql.options()))
                } else {
                    log::info!("Skip section: {:?} not allowed in {:?}", s, filter);
                    None
                }
            })
            .collect::<Vec<_>>();
        let mut output: Vec<String> = sections
            .iter()
            .filter_map(|s| s.to_signaling_header())
            .collect();

        let (root_spots, root_errors) = connect_spots(all, None);
        let (work_spots, work_errors) = make_spot_work_results(
            root_spots,
            sections,
            ora_sql.instances(),
            ora_sql.excluded_sections(),
            Some(ora_sql.product().cache_age()),
            ora_sql.params(),
            ora_sql.options(),
        );
        let results = if ora_sql.options().threads() > 1 {
            process_spot_works_para(
                work_spots
                    .into_iter()
                    .map(|(s, w)| (s.close(), w))
                    .collect(),
                ora_sql.options().threads(),
            )
        } else {
            process_spot_works(work_spots)
        };
        output.extend(results.into_iter().flat_map(|(_, r)| r));

        for error in root_errors {
            output.push(header(names::INSTANCE, '|'));
            output.push(format!("{}", error));
        }
        for (_closed, error) in work_errors {
            output.push(header(names::INSTANCE, '|'));
            output.push(format!("{}", error));
        }
        Ok(output)
    } else {
        log::debug!("Filter {:?} skips all sections", environment.filter());
        Ok(vec![])
    }
}

/// Remap filter according to the following rules:
/// If filter is AsyncCustomMetrics and cache ages are equal,
///     then it is remapped to None (skipped).
/// If filter is AsyncBuiltinSections and cache ages are equal,
///     then it is remapped to Some(AsyncAll).
/// Otherwise filter is unchanged.
fn remap_filter(filter: SectionFilter, ora_sql: &config::ora_sql::Config) -> Option<SectionFilter> {
    if ora_sql.cache_age() != ora_sql.custom_metrics_cache_age() {
        return Some(filter);
    }

    match filter {
        SectionFilter::AsyncCustomMetrics => None,
        SectionFilter::AsyncBuiltinSections => Some(SectionFilter::AsyncAll),
        _ => Some(filter),
    }
}

fn wrap_for_piggyback(piggyback: Option<&Piggyback>, mut results: Vec<String>) -> Vec<String> {
    if let Some(pb) = piggyback {
        results.insert(0, piggyback_header(&pb.hostname().clone().into()));
        results.push(piggyback_footer());
    }
    results
}

fn process_spot_works(works: Vec<OpenedSpotWorks>) -> Vec<ClosedSpotResults> {
    works
        .into_iter()
        .map(|(spot, instance_works)| {
            log::debug!("Spot: {:?}", spot.target());
            let results = instance_works
                .iter()
                .flat_map(|(instance, query_blocks)| {
                    log::info!("Instance: {}", instance);
                    let session_timer =
                        PerfTimer::start("session", Label::Block(&instance.to_string()));

                    let output = query_blocks
                        .iter()
                        .filter_map(|query_block| {
                            log::info!("Executing {}", query_block.label);
                            with_container(&spot, query_block.container.as_ref(), || {
                                let mut results = vec![query_block.title.clone()];
                                results.extend(_exec_queries(
                                    &spot,
                                    instance,
                                    &query_block.queries,
                                    &query_block.post_processing,
                                    &query_block.title,
                                ));
                                results.join("\n")
                            })
                            .map_err(|e| log::warn!("Cannot switch container: {e}, skipping"))
                            .ok()
                        })
                        .collect::<Vec<String>>();

                    session_timer.stop();
                    output
                })
                .collect::<Vec<String>>();
            let results = wrap_for_piggyback(spot.piggyback(), results);
            (spot.close(), results)
        })
        .collect::<Vec<_>>()
}

fn process_spot_works_para(works: Vec<ClosedSpotWorks>, threads: usize) -> Vec<ClosedSpotResults> {
    let threads = threads.clamp(1, MAX_THREAD_COUNT);
    works
        .into_iter()
        .flat_map(|(closed, instance_works)| {
            log::debug!("Spot: {:?}", closed.target());

            instance_works
                .iter()
                .flat_map(|(instance, query_blocks)| {
                    log::info!("Instance: {}", instance);
                    // no more threads than blocks to run
                    let work_threads = threads.min(query_blocks.len());
                    if work_threads == 0 {
                        log::warn!("No queries for instance {instance}, nothing to run");
                        return vec![];
                    }
                    let session_timer =
                        PerfTimer::start("session", Label::Block(&instance.to_string()));
                    let opened_spots = open_spots(&closed, instance, work_threads);
                    if opened_spots.is_empty() {
                        log::error!("Failed to connect to instance {}", instance);
                        session_timer.stop();
                        return vec![];
                    }
                    let job_data: Vec<JobData> = make_job_data(opened_spots, query_blocks);
                    let thread_pool = build_thread_pool(work_threads);
                    let global_output = Mutex::new(Vec::new());
                    thread_pool.scope(|scope| {
                        for job in job_data {
                            let thread_output = &global_output;
                            scope.spawn(move |_| {
                                let results =
                                    job.query_blocks
                                        .iter()
                                        .flat_map(|query_block| {
                                            log::info!("Executing {}", query_block.label);
                                            with_container(
                                                &job.spot,
                                                query_block.container.as_ref(),
                                                || {
                                                    _exec_queries_on_spot(
                                                        &job.spot,
                                                        instance,
                                                        &query_block.queries,
                                                        query_block.title.as_str(),
                                                        &query_block.post_processing,
                                                    )
                                                },
                                            )
                                            .unwrap_or_else(|e| {
                                                log::warn!(
                                                    "Cannot switch container: {e}, skipping"
                                                );
                                                vec![]
                                            })
                                        })
                                        .collect::<Vec<String>>();
                                let results = wrap_for_piggyback(job.spot.piggyback(), results);

                                thread_output
                                    .lock()
                                    .unwrap()
                                    .push((job.spot.close(), results));
                            })
                        }
                    });
                    session_timer.stop();
                    global_output.into_inner().unwrap()
                })
                .collect::<Vec<_>>()
        })
        .collect::<Vec<_>>()
}

/// Keep only the spots this run is responsible for, as `LOCAL_ORACLE_HOME_TARGETS`
/// defines it.
///
/// `LOCAL_ORACLE_HOME_TARGETS` defines which half of the targets a run is responsible for:
///
/// * **`yes`**: this oracle home's own targets - the aliases of its `tnsnames.ora` and
///   its own sids with wallet.
/// * **`no`**: the targets that need no oracle home - a sid no local instance owns, a
///   sid needing no wallet, a descriptor, and an alias a global `TNS_ADMIN`
///   resolves.
/// * **absent**: nothing states how the targets are divided, so none is dropped.
///
/// `pub` only so the component tests in `tests/` can reach it: they are a
/// separate crate, so `pub(crate)` is not enough. Hidden from the documented
/// API - nothing outside this module uses it in production.
#[doc(hidden)]
pub fn filter_spots_by_oracle_home(
    spots: Vec<ClosedSpot>,
    environment: &Env,
    local_instances: &[LocalInstance],
) -> Vec<ClosedSpot> {
    let Some(local_oracle_home_targets) = environment.local_oracle_home_targets() else {
        log::info!(
            "{LOCAL_ORACLE_HOME_TARGETS_ENV_VAR} is not set: monitoring every configured target"
        );
        return spots;
    };

    let received = spots.len();
    let homes_to_sids = get_oracle_home_sids(local_instances);
    let kept: Vec<ClosedSpot> = if local_oracle_home_targets {
        // Gather wallets SID of the home and aliases from home tns_aliases
        let Some(oracle_home) = environment.oracle_home() else {
            log::warn!(
                "{LOCAL_ORACLE_HOME_TARGETS_ENV_VAR}=yes without an {ORACLE_HOME_ENV_VAR}: \
                 no target for this run"
            );
            return vec![];
        };
        let Some(local_sids) = homes_to_sids.get(&home_key(oracle_home)) else {
            log::warn!(
                "No local instance belongs to {ORACLE_HOME_ENV_VAR} '{}': no target for this run",
                oracle_home.display()
            );
            return vec![];
        };
        let local_aliases = local_tns_aliases(environment);
        spots
            .into_iter()
            .filter(|spot| is_spot_local(spot, local_sids, &local_aliases))
            .collect()
    } else {
        log::info!("{LOCAL_ORACLE_HOME_TARGETS_ENV_VAR}=no: taking the targets that need no home");
        let global_aliases = global_tns_aliases(environment);
        // Every sid: which home owns it does not matter
        let all_local_sids: HashSet<Sid> = homes_to_sids.into_values().flatten().collect();
        spots
            .into_iter()
            .filter(|spot| {
                if let Some(alias) = spot.target.alias() {
                    return global_aliases.contains(&alias.to_string().to_uppercase());
                }
                if spot.target.standalone_sid().is_some() {
                    return !(is_sid_from_list(spot, &all_local_sids) && uses_wallet_auth(spot));
                }
                // descriptors and similar need no home and will be processed here
                true
            })
            .collect()
    };

    // Unusual to have an empty kept list, but not impossible - log it
    if kept.is_empty() && received > 0 {
        log::warn!(
            "{LOCAL_ORACLE_HOME_TARGETS_ENV_VAR}={} left none of {received} configured targets: \
             the run taking the other half has to exist too",
            if local_oracle_home_targets {
                "yes"
            } else {
                "no"
            }
        );
    } else {
        log::info!("Monitoring {} of {received} configured targets", kept.len());
    }
    kept
}

/// SID is standalone and case-insensitive
fn is_sid_from_list(spot: &ClosedSpot, sids: &HashSet<Sid>) -> bool {
    spot.target
        .standalone_sid()
        .map(|sid| Sid::from(sid.to_string().to_uppercase()))
        .is_some_and(|sid| sids.contains(&sid))
}

fn is_spot_local(
    spot: &ClosedSpot,
    local_sids: &HashSet<Sid>,
    local_aliases: &HashSet<String>,
) -> bool {
    // local alias is to be processed
    if is_alias_from_list(spot, local_aliases) {
        return true;
    }

    // local sid with wallet to be processed
    if is_sid_from_list(spot, local_sids) && uses_wallet_auth(spot) {
        return true;
    }
    log::debug!(
        "Skip {}: handled by the run that owns it, not by this {ORACLE_HOME_ENV_VAR}",
        spot.target().display_name()
    );
    false
}

fn uses_wallet_auth(spot: &ClosedSpot) -> bool {
    spot.target().connection_auth().auth_type == AuthType::Wallet
}

/// The aliases of the `tnsnames.ora` of the inherited `ORACLE_HOME`, upper-cased
/// as the parser reports them. Empty when the file is absent: an alias that
/// cannot be resolved is not one this home owns.
///
/// `pub` only so the component tests in `tests/` can reach it: they are a
/// separate crate, so `pub(crate)` is not enough. Hidden from the documented
/// API - nothing outside this module uses it in production.
#[doc(hidden)]
pub fn local_tns_aliases(environment: &Env) -> HashSet<String> {
    if global_tns_file(environment).is_some_and(|file| file.is_file()) {
        return HashSet::new();
    }

    let Some(tns_admin) = environment.local_tns_admin() else {
        return HashSet::new();
    };
    let file = tns_admin.join(TNS_NAMES_FILE);
    extract_aliases(&file)
}

/// The aliases of the `tnsnames.ora` that `TNS_ADMIN` names, upper-cased as the
/// parser reports them. Empty when there is no such file.
fn global_tns_aliases(env: &Env) -> HashSet<String> {
    if let Some(file) = global_tns_file(env) {
        extract_aliases(&file)
    } else {
        log::info!("No global {TNS_ADMIN_ENV_VAR} file, no global aliases");
        HashSet::new()
    }
}

/// uppercased aliases of the `tnsnames.ora` at `file`, or empty if the file is absent/not readable
fn extract_aliases(file: &Path) -> HashSet<String> {
    match parse_tns_names_ora(file) {
        Ok(entries) => entries
            .into_iter()
            .map(|entry| entry.alias.to_string().to_uppercase())
            .collect(),
        Err(e) => {
            log::info!("No usable {}: {e}", file.display());
            HashSet::new()
        }
    }
}

fn global_tns_file(env: &Env) -> Option<PathBuf> {
    // if exists TNS_ADMIN/tnsnames.ora return empty - we can't use local tnsnames.ora in this case
    if let Some(dir) = env.global_tns_admin() {
        let external = dir.join(TNS_NAMES_FILE);
        if external.is_file() {
            log::info!(
                "'{}' resolves the aliases, not the one of {ORACLE_HOME_ENV_VAR}",
                external.display()
            );
            return Some(external);
        }
    }
    None
}

/// Whether the spot names an alias that the local `tnsnames.ora` defines.
/// Compared case-insensitively, since only a SID is upper-cased on parsing.
fn is_alias_from_list(spot: &ClosedSpot, aliases: &HashSet<String>) -> bool {
    spot.target()
        .target_id()
        .and_then(|target_id| target_id.alias())
        .is_some_and(|alias| aliases.contains(&alias.to_string().to_uppercase()))
}

fn open_spots(
    spot: &ClosedSpot,
    instance_name: &InstanceName,
    thread_count: usize,
) -> Vec<OpenedSpot> {
    std::iter::repeat_with(|| spot.clone().connect(None))
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

/// builds a table [(OpenedSpot, [QueryBlock, ...]), ...]
fn make_job_data(spots: Vec<Spot<Opened>>, query_blocks: &[QueryBlock]) -> Vec<JobData> {
    if query_blocks.is_empty() {
        return Vec::new();
    }
    let job_count = spots.len();
    let chunk_size = query_blocks.len().div_ceil(job_count);
    let chunks = query_blocks.chunks(chunk_size);
    log::debug!(
        "Job data: {} query blocks, {} jobs, chunk size {}, {} chunks",
        query_blocks.len(),
        job_count,
        chunk_size,
        chunks.len()
    );
    spots
        .into_iter()
        .zip(chunks)
        .map(|(spot, chunk)| JobData {
            spot,
            query_blocks: chunk.to_vec(),
        })
        .collect::<Vec<_>>()
}

/// Execute queries on an opened spot and return results with title headers ahead
fn _exec_queries_on_spot(
    spot: &Spot<Opened>,
    instance_name: &InstanceName,
    queries: &[SqlQuery],
    title: &str,
    post_processing: &PostProcessing,
) -> Vec<String> {
    let section_timer = PerfTimer::start("section", Label::Block(title));
    let results = queries
        .iter()
        .flat_map(|query| {
            log::debug!("Executing query: {}", query.as_str());
            let query_timer = PerfTimer::start("query", Label::Inline);
            let query_result = spot.query_table(query);
            query_timer.stop();
            let mut result = run_query(query_result, post_processing, instance_name);
            result.insert(0, title.to_string());
            result
        })
        .collect::<Vec<String>>();
    section_timer.stop();
    results
}

const MAX_THREAD_COUNT: usize = 8;

struct JobData {
    spot: Spot<Opened>,
    query_blocks: Vec<QueryBlock>,
}

fn _exec_queries(
    spot: &OpenedSpot,
    service_name: &InstanceName,
    queries: &[SqlQuery],
    post_processing: &PostProcessing,
    title: &str,
) -> Vec<String> {
    let section_timer = PerfTimer::start("section", Label::Block(title));
    let results = queries
        .iter()
        .flat_map(|query| {
            log::debug!("Executing query: {}", query.as_str());
            let query_timer = PerfTimer::start("query", Label::Inline);
            let query_result = spot.query_table(query);
            query_timer.stop();
            run_query(query_result, post_processing, service_name)
        })
        .collect::<Vec<_>>();

    section_timer.stop();
    results
}

/// Render a `QueryResult` to agent-output lines. For custom-metric sections
/// (`PostProcessing::Passthrough`) each SELECT-ed cell is emitted as-is — the
/// SQL is contracted to already produce `details:...` / `perfdata:...` /
/// `exit:...` rows. For predefined sections we join the row's columns with the
/// standard agent separator.
fn run_query(
    result: crate::ora_sql::backend::QueryResult,
    post_processing: &PostProcessing,
    instance: &InstanceName,
) -> Vec<String> {
    let outcome = match post_processing {
        PostProcessing::Passthrough => result.into_rows_passthrough(),
        PostProcessing::Standard => result.format(&SECTION_SEPARATOR.to_string()),
    };
    outcome.unwrap_or_else(|e| {
        log::error!("Failed to execute query for instance {}: {}", instance, e);
        vec![format!(
            "{}|FAILURE|{}",
            instance,
            sanitize_failure_message(&e.to_string())
        )]
    })
}

// tested only in integration tests
fn connect_spots(
    spots: Vec<ClosedSpot>,
    instance_name: Option<&InstanceName>,
) -> (Vec<OpenedSpot>, Vec<anyhow::Error>) {
    let connected = spots
        .into_iter()
        .map(|t| {
            let name = t.target().display_name();
            match t.connect(instance_name) {
                Ok(opened) => {
                    log::info!("Connected to instance: {:?}", &opened.target());
                    Ok(opened)
                }
                Err(e) => {
                    log::error!("Error connecting to instance: {}", e);
                    anyhow::bail!(
                        "{}|FAILURE|ERROR: {} ",
                        name,
                        sanitize_failure_message(&e.to_string())
                    )
                }
            }
        })
        .collect::<Vec<Result<OpenedSpot>>>();

    _split_spots(connected)
}

fn _split_spots(spots: Vec<Result<OpenedSpot>>) -> (Vec<OpenedSpot>, Vec<anyhow::Error>) {
    spots
        .into_iter()
        .fold((Vec::new(), Vec::new()), |(mut spots, mut errors), r| {
            match r {
                Ok(s) => spots.push(s),
                Err(e) => errors.push(e),
            }
            (spots, errors)
        })
}

fn calc_all_spots(
    endpoints: Vec<config::ora_sql::Endpoint>,
    instances: &[CustomInstance],
) -> Vec<ClosedSpot> {
    let mut all = calc_main_spots(endpoints);
    all.extend(calc_custom_spots(instances));
    all.into_iter()
        .filter(|spot| {
            if !spot.target.is_defined() {
                log::debug!(
                    "Endpoint has no sid, service_name or alias, skipping it: {:?}",
                    spot.target()
                );
                return false;
            }
            true
        })
        .collect::<Vec<ClosedSpot>>()
}

/// Filters spots according to discovery config.
/// Tactic:
/// Filtering depends on the TargetId enum variant.
/// If TargetId is Descriptor, instance name is taken from descriptor.instance_name.
/// If TargetId is Sid, instance name is taken from sid. If TargetId is something else, spot is included without filtering and a warning is logged.
/// It may be changed in the future.
/// Lists:
/// If include list is not empty, only spots with instance names in it are included.
/// If include list is empty and exclude list is not empty, only spots with instance names not in exclude list are included.
/// If both lists are empty, all spots are included.
/// The spots which have no defined target id are excluded
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
            let target = spot.target();
            if target.alias().is_some() {
                return true;
            }
            let check_name = if let Some(sid) = target.standalone_sid() {
                // sid need to be filtrated
                Some(sid.to_string().to_uppercase())
            } else if let Some(instance_name) = target.instance_name() {
                // instance name need to be filtrated
                Some(instance_name.to_string().to_uppercase())
            } else if target.service_name().is_some() {
                // Targets with only service name can't be filtrated thus we will include them always
                return true;
            } else {
                log::info!("Spot has no TargetId and will be dropped immediately");
                None
            };
            if let Some(uppercased_name) = check_name {
                if !include.is_empty() {
                    include.contains(&uppercased_name)
                } else if !exclude.is_empty() {
                    !exclude.contains(&uppercased_name)
                } else {
                    true
                }
            } else {
                false
            }
        })
        .collect()
}

fn calc_main_spots(endpoints: Vec<config::ora_sql::Endpoint>) -> Vec<ClosedSpot> {
    log::debug!("ENDPOINTS: {:?}", endpoints);
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

/// `pub` only so the component tests in `tests/` can reach it: they are a
/// separate crate, so `pub(crate)` is not enough. Hidden from the documented
/// API - nothing outside this module uses it in production.
#[doc(hidden)]
pub fn calc_custom_spots(instances: &[CustomInstance]) -> Vec<ClosedSpot> {
    log::debug!("CUSTOM INSTANCES: {:?}", instances);
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
    use crate::config::connection::Connection;
    use crate::config::ora_sql::Discovery;
    use crate::config::target::TargetIdBuilder;
    use crate::config::yaml::test_tools::create_yaml;
    use crate::types::ServiceName;

    #[test]
    fn test_make_job_data_no_query_blocks() {
        assert!(make_job_data(vec![], &[]).is_empty());
    }

    #[test]
    fn test_run_query_error_becomes_failure_row() {
        let result = crate::ora_sql::backend::QueryResult(Err(anyhow::anyhow!(
            "OCI Error: ORA-00942: table or view does not exist"
        )));
        assert_eq!(
            run_query(
                result,
                &PostProcessing::Standard,
                &InstanceName::from("free")
            ),
            vec!["FREE|FAILURE|ORA-00942: table or view does not exist".to_string()]
        );
    }

    #[test]
    fn test_run_query_error_stays_a_single_failure_row() {
        // if the row splits, the server drops it and the error is hidden
        let result = crate::ora_sql::backend::QueryResult(Err(anyhow::anyhow!(
            "OCI Error: ORA-00600: [foo|bar]\nORA-12514: continued"
        )));
        assert_eq!(
            run_query(
                result,
                &PostProcessing::Standard,
                &InstanceName::from("free")
            ),
            vec!["FREE|FAILURE|ORA-00600: [foo bar] ORA-12514: continued".to_string()]
        );
    }

    #[test]
    fn test_calc_spots() {
        assert!(calc_main_spots(vec![]).is_empty());
        let all = calc_main_spots(vec![
            config::ora_sql::Endpoint::default(),
            config::ora_sql::Endpoint::default(),
        ]);
        assert_eq!(all.len(), 2);
    }
    fn make_instance(instance_name: &str) -> CustomInstance {
        CustomInstance::new(
            config::authentication::Authentication::default(),
            Connection::default(),
            TargetIdBuilder::new()
                .service_name(Some(&ServiceName::from("XXX")))
                .instance_name(Some(&InstanceName::from(instance_name)))
                .build(),
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
            all[0].target().instance_name().unwrap(),
            &InstanceName::from("A")
        );
        assert_eq!(
            all[1].target().instance_name().unwrap(),
            &InstanceName::from("B")
        );
    }

    fn make_instance_with_custom_conn(service_name: &str) -> config::ora_sql::CustomInstance {
        let base_connection =
            Connection::from_yaml(&create_yaml("connection:\n    service_name: X"))
                .unwrap()
                .unwrap();
        CustomInstance::new(
            config::authentication::Authentication::default(),
            base_connection,
            TargetIdBuilder::new()
                .service_name(Some(&ServiceName::from(service_name)))
                .build(),
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
            all[0].target().service_name().unwrap(),
            &ServiceName::from("A")
        );
        assert_eq!(
            all[1].target().service_name().unwrap(),
            &ServiceName::from("B")
        );
    }
    #[test]
    fn test_wrap_for_piggyback_without_config_returns_output_unchanged() {
        let results = vec![
            "<<<oracle_instance:sep(124)>>>".to_string(),
            "ORCLPDB1|OPEN|OPEN|...".to_string(),
        ];
        assert_eq!(
            wrap_for_piggyback(None, results.clone()),
            results,
            "no piggyback configured must not add any markers"
        );
    }

    #[test]
    fn test_wrap_for_piggyback_with_config_adds_markers() {
        use crate::config::section::Sections;

        let piggyback = Piggyback::from_yaml(
            &create_yaml("piggyback:\n  hostname: oracle-prod-db01\n"),
            &Sections::default(),
        )
        .unwrap()
        .unwrap();

        let wrapped = wrap_for_piggyback(
            Some(&piggyback),
            vec![
                "<<<oracle_instance:sep(124)>>>".to_string(),
                "ORCLPDB1|OPEN|OPEN|...".to_string(),
            ],
        );

        assert_eq!(
            wrapped,
            vec![
                "<<<<oracle-prod-db01>>>>".to_string(),
                "<<<oracle_instance:sep(124)>>>".to_string(),
                "ORCLPDB1|OPEN|OPEN|...".to_string(),
                "<<<<>>>>".to_string(),
            ]
        );
    }

    /// One instance per target shape the filter distinguishes.
    fn instance_for_home(
        target: Option<crate::config::target::TargetId>,
        wallet: bool,
    ) -> CustomInstance {
        let auth = if wallet {
            config::authentication::Authentication::from_yaml(&create_yaml(
                "authentication:\n  username: u\n  password: p\n  type: wallet",
            ))
            .unwrap()
            .unwrap()
        } else {
            config::authentication::Authentication::default()
        };
        CustomInstance::new(auth, Connection::default(), target, None, None)
    }

    fn sid_target(sid: &str) -> Option<crate::config::target::TargetId> {
        TargetIdBuilder::new().sid(Some(sid)).build()
    }

    fn alias_target(alias: &str) -> Option<crate::config::target::TargetId> {
        TargetIdBuilder::new()
            .alias(Some(&crate::types::InstanceAlias::from(alias.to_string())))
            .build()
    }

    /// One spot of the given shape.
    fn one_spot(target: Option<crate::config::target::TargetId>, wallet: bool) -> ClosedSpot {
        calc_custom_spots(&[instance_for_home(target, wallet)])
            .pop()
            .expect("a defined target yields a spot")
    }

    fn local_instance(name: &str, home: &str) -> LocalInstance {
        LocalInstance {
            name: InstanceName::from(name),
            home: std::path::PathBuf::from(home),
            base: None,
        }
    }

    #[test]
    fn test_global_tns_without_tns_admin() {
        // Hermetic: the empty Env carries no global TNS_ADMIN, regardless of what
        // the process environment holds.
        let env = Env::default();
        assert!(global_tns_file(&env).is_none());
        assert!(global_tns_aliases(&env).is_empty());
    }

    #[test]
    fn test_local_tns_admin_without_tns_admin_and_oracle_home() {
        if std::env::var_os(TNS_ADMIN_ENV_VAR).is_some()
            || std::env::var_os(ORACLE_HOME_ENV_VAR).is_some()
        {
            return;
        }

        let inherited = Env::new(&crate::args::Args::default());
        assert!(inherited.oracle_home().is_none());
        assert!(inherited.local_tns_admin().is_none());
        assert!(local_tns_aliases(&inherited).is_empty());

        // An empty value names no home, so it arrives as none at all.
        let empty = Env::with_oracle_home(Some(""), None);
        assert!(empty.oracle_home().is_none());
        assert!(empty.local_tns_admin().is_none());
        assert!(local_tns_aliases(&empty).is_empty());

        let set = Env::with_oracle_home(Some("/opt/oracle"), None);
        assert!(set.oracle_home().is_some());
        assert_eq!(
            set.local_tns_admin(),
            Some(std::path::PathBuf::from("/opt/oracle/network/admin"))
        );
    }

    #[test]
    fn test_is_sid_from_list() {
        // As `get_oracle_home_sids` builds it: upper-cased.
        let known = get_oracle_home_sids(&[local_instance("xe", "/opt/oracle")]);
        let known = &known[&std::path::PathBuf::from("/opt/oracle")];

        // Matched ignoring case, in both directions.
        assert!(is_sid_from_list(&one_spot(sid_target("xe"), false), known));
        assert!(is_sid_from_list(&one_spot(sid_target("XE"), false), known));
        assert!(!is_sid_from_list(
            &one_spot(sid_target("other"), false),
            known
        ));
        // An alias target names no sid.
        assert!(!is_sid_from_list(
            &one_spot(alias_target("xe"), false),
            known
        ));
        assert!(!is_sid_from_list(
            &one_spot(sid_target("xe"), false),
            &HashSet::new()
        ));
    }

    #[test]
    fn test_is_alias_from_list() {
        let known: HashSet<String> = ["XE".to_string()].into_iter().collect();

        assert!(is_alias_from_list(
            &one_spot(alias_target("xe"), false),
            &known
        ));
        assert!(!is_alias_from_list(
            &one_spot(alias_target("other"), false),
            &known
        ));
        // A sid target names no alias.
        assert!(!is_alias_from_list(
            &one_spot(sid_target("xe"), false),
            &known
        ));
    }

    #[test]
    fn test_is_spot_local() {
        let sids: HashSet<Sid> = [Sid::from("XE")].into_iter().collect();
        let aliases: HashSet<String> = ["KNOWN".to_string()].into_iter().collect();

        // A local alias counts, whatever the authentication.
        assert!(is_spot_local(
            &one_spot(alias_target("known"), false),
            &sids,
            &aliases
        ));
        // A local sid counts only with wallet authentication.
        assert!(is_spot_local(
            &one_spot(sid_target("xe"), true),
            &sids,
            &aliases
        ));
        assert!(!is_spot_local(
            &one_spot(sid_target("xe"), false),
            &sids,
            &aliases
        ));
        // A sid of another home never counts.
        assert!(!is_spot_local(
            &one_spot(sid_target("other"), true),
            &sids,
            &aliases
        ));
    }

    #[test]
    fn test_filter_spots() {
        let all = calc_all_spots(
            vec![config::ora_sql::Endpoint::default()],
            &[make_instance("A"), make_instance("B")],
        );
        assert_eq!(all.len(), 2);
        let d = Discovery::default();
        assert_eq!(filter_spots(all.clone(), &d).len(), 2);
        let d = Discovery::new(false, vec!["".to_string()], vec![]);
        assert_eq!(filter_spots(all.clone(), &d).len(), 0);
        let d = Discovery::new(
            false,
            vec!["".to_string(), "A".to_string(), "x".to_string()], // 2 left
            vec!["".to_string(), "A".to_string(), "B".to_string()], // ignored
        );
        assert_eq!(filter_spots(all.clone(), &d).len(), 1);
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
        assert_eq!(filter_spots(all.clone(), &d).len(), 0);
    }

    fn config_with_same_cache_age() -> config::ora_sql::Config {
        config::ora_sql::Config::default()
    }

    fn config_with_different_cache_age() -> config::ora_sql::Config {
        let yaml = r#"
---
oracle:
  main:
    authentication:
      username: "foo"
      password: "bar"
      type: "standard"
    cache_age: 600
    custom_metrics_cache_age: 120
"#;
        config::ora_sql::Config::from_string(yaml).unwrap().unwrap()
    }

    #[test]
    fn test_remap_filter_same_cache_age_skips_custom_metrics() {
        let cfg = config_with_same_cache_age();
        assert_eq!(remap_filter(SectionFilter::AsyncCustomMetrics, &cfg), None);
    }

    #[test]
    fn test_remap_filter_same_cache_age_promotes_builtin_to_all() {
        let cfg = config_with_same_cache_age();
        assert_eq!(
            remap_filter(SectionFilter::AsyncBuiltinSections, &cfg),
            Some(SectionFilter::AsyncAll)
        );
    }

    #[test]
    fn test_remap_filter_same_cache_age_passes_others() {
        let cfg = config_with_same_cache_age();
        assert_eq!(
            remap_filter(SectionFilter::All, &cfg),
            Some(SectionFilter::All)
        );
        assert_eq!(
            remap_filter(SectionFilter::Sync, &cfg),
            Some(SectionFilter::Sync)
        );
        assert_eq!(
            remap_filter(SectionFilter::AsyncAll, &cfg),
            Some(SectionFilter::AsyncAll)
        );
    }

    #[test]
    fn test_remap_filter_different_cache_age_no_remapping() {
        let cfg = config_with_different_cache_age();
        assert_eq!(
            remap_filter(SectionFilter::AsyncCustomMetrics, &cfg),
            Some(SectionFilter::AsyncCustomMetrics)
        );
        assert_eq!(
            remap_filter(SectionFilter::AsyncBuiltinSections, &cfg),
            Some(SectionFilter::AsyncBuiltinSections)
        );
        assert_eq!(
            remap_filter(SectionFilter::All, &cfg),
            Some(SectionFilter::All)
        );
        assert_eq!(
            remap_filter(SectionFilter::Sync, &cfg),
            Some(SectionFilter::Sync)
        );
        assert_eq!(
            remap_filter(SectionFilter::AsyncAll, &cfg),
            Some(SectionFilter::AsyncAll)
        );
    }
}

#[cfg(test)]
mod yaml_to_output_tests {
    //! Config YAML -> emitted agent lines, DB faked via `MiniOra`.
    //! Single-threaded path only, so output order is deterministic.
    use super::*;
    use crate::config::options::Options;
    use crate::config::ora_sql::Config;
    use crate::ora_sql::backend::test_support::{instance_row, open_spot, MiniOra};

    fn config_from(yaml: &str) -> Config {
        Config::from_string(yaml).unwrap().unwrap()
    }

    /// Runtime sections for the global `custom_metrics:` entries only.
    fn custom_sections(config: &Config, cache_age: u32) -> Vec<Section> {
        config
            .product()
            .sections()
            .iter()
            .filter(|s| s.is_custom_metric())
            .map(|s| Section::new(s, Some(cache_age), config.options()))
            .collect()
    }

    /// A `sections:` list replaces the predefined set, so this yields exactly
    /// the sections the test asked for.
    fn builtin_sections(config: &Config) -> Vec<Section> {
        config
            .product()
            .sections()
            .iter()
            .filter(|s| !s.is_custom_metric())
            .map(|s| Section::new(s, Some(0), config.options()))
            .collect()
    }

    /// Synchronous, so the header carries no `cached(...)` marker.
    fn one_builtin_section_yaml(name: &str) -> String {
        format!(
            r#"
oracle:
  main:
    authentication:
      username: u
      password: p
      type: standard
    connection:
      hostname: localhost
    sections:
      - {name}:
          is_async: false
"#
        )
    }

    /// `MiniOra` answers every section query alike, so only the selected SQL
    /// text shows which variant dispatch produced.
    fn selected_statements(yaml: &str, name: &str, version: &str, cdb: &str) -> Vec<String> {
        let config = config_from(yaml);
        let db = MiniOra {
            default_rows: vec![vec!["r1".to_string()]],
            ..MiniOra::at_version(name, version, cdb)
        };
        let (works, errors) = make_spot_work_results(
            vec![open_spot(db, None)],
            builtin_sections(&config),
            &[],
            &[],
            Some(0),
            config.params(),
            config.options(),
        );
        let error_msgs: Vec<String> = errors.iter().map(|(_, e)| e.to_string()).collect();
        assert!(
            error_msgs.is_empty(),
            "unexpected spot errors: {error_msgs:?}"
        );
        let (_spot, instance_works) = &works[0];
        let (instance, blocks) = &instance_works[0];
        assert_eq!(instance.to_string(), name.to_uppercase());
        // Without this, every "must not contain" assertion below is vacuous.
        assert_eq!(blocks.len(), 1, "the section must yield exactly one block");
        blocks[0]
            .queries
            .iter()
            .map(|q| q.as_str().to_owned())
            .collect()
    }

    /// Run the pipeline over `spots`, returning the joined output lines.
    fn emit(
        spots: Vec<OpenedSpot>,
        sections: Vec<Section>,
        instances: &[CustomInstance],
        cache_age: u32,
    ) -> String {
        let (works, errors) = make_spot_work_results(
            spots,
            sections,
            instances,
            &[],
            Some(cache_age),
            &[],
            &Options::default(),
        );
        let error_msgs: Vec<String> = errors.iter().map(|(_, e)| e.to_string()).collect();
        assert!(
            error_msgs.is_empty(),
            "unexpected spot errors: {error_msgs:?}"
        );
        process_spot_works(works)
            .into_iter()
            .flat_map(|(_, lines)| lines)
            .collect::<Vec<_>>()
            .join("\n")
    }

    // TC-ORA-101 (sync, single-tenant): inline SQL -> oracle_sql subsection, rows verbatim.
    #[test]
    fn test_inline_custom_sql_emits_oracle_sql_subsection() {
        let config = config_from(
            r#"
oracle:
  main:
    authentication:
      username: u
      password: p
      type: standard
    connection:
      hostname: localhost
    custom_metrics:
      - product_price:
          sql: "select payload from custom_metrics_view"
"#,
        );
        let db = MiniOra {
            instance_rows: vec![instance_row("ORCL", "19.1.0.0", "NO")],
            version_rows: vec![vec!["19.1.0.0".to_string()]],
            pdb_rows: vec![],
            default_rows: vec![
                vec!["details:price=5; still ok".to_string()],
                vec!["perfdata:price=5;10;20;;".to_string()],
                vec!["long:extended detail".to_string()],
                vec!["exit:0".to_string()],
            ],
            ..Default::default()
        };

        let out = emit(
            vec![open_spot(db, None)],
            custom_sections(&config, 600),
            &[],
            600,
        );

        assert_eq!(
            out,
            concat!(
                "<<<oracle_sql:sep(58)>>>\n",
                "[[[ORCL|product_price]]]\n",
                "details:price=5; still ok\n",
                "perfdata:price=5;10;20;;\n",
                "long:extended detail\n",
                "exit:0",
            )
        );
    }

    // TC-ORA-101 (Param: async): section header stays plain; cached marker on the subsection.
    #[test]
    fn test_async_custom_metric_keeps_plain_section_header() {
        let config = config_from(
            r#"
oracle:
  main:
    authentication:
      username: u
      password: p
      type: standard
    connection:
      hostname: localhost
    custom_metrics:
      - last_sessions:
          is_async: true
          sql: "select payload from v"
"#,
        );
        let out = emit(
            vec![open_spot(MiniOra::single("ORCL"), None)],
            custom_sections(&config, 600),
            &[],
            600,
        );

        let lines: Vec<&str> = out.lines().collect();
        assert_eq!(
            lines[0], "<<<oracle_sql:sep(58)>>>",
            "section header must stay plain for async metrics"
        );
        assert!(
            lines[1].starts_with("[[[ORCL|last_sessions|cached("),
            "subsection must carry the cached marker: {}",
            lines[1]
        );
        assert!(lines[1].ends_with(",600)]]]"), "cached age: {}", lines[1]);
        assert_eq!(lines[2], "details:ok");
    }

    // TC-ORA-101 (Param: PDB instance type): `pdbs:` pattern -> [[[<SID>_<PDB>|item]]] via container switch.
    #[test]
    fn test_custom_metric_targets_pdb() {
        let config = config_from(
            r#"
oracle:
  main:
    authentication:
      username: u
      password: p
      type: standard
    connection:
      hostname: localhost
    custom_metrics:
      - product_price:
          sql: "select payload from v"
          pdbs:
            - PDB1
"#,
        );
        let db = MiniOra {
            instance_rows: vec![instance_row("ORCL", "19.1.0.0", "YES")],
            version_rows: vec![vec!["19.1.0.0".to_string()]],
            pdb_rows: vec![
                vec!["CDB$ROOT".to_string()],
                vec!["PDB$SEED".to_string()],
                vec!["PDB1".to_string()],
            ],
            default_rows: vec![vec!["details:ok".to_string()]],
            ..Default::default()
        };

        let out = emit(
            vec![open_spot(db, None)],
            custom_sections(&config, 600),
            &[],
            600,
        );

        assert_eq!(
            out,
            "<<<oracle_sql:sep(58)>>>\n[[[ORCL_PDB1|product_price]]]\ndetails:ok"
        );
    }

    // TC-ORA-102: one global query -> one subsection per instance (ORACLE_ID = SID).
    #[test]
    fn test_global_custom_metric_emitted_per_instance() {
        let config = config_from(
            r#"
oracle:
  main:
    authentication:
      username: u
      password: p
      type: standard
    connection:
      hostname: localhost
    custom_metrics:
      - product_price:
          sql: "select payload from v"
"#,
        );
        let spots = vec![
            open_spot(MiniOra::single("ORCL1"), None),
            open_spot(MiniOra::single("ORCL2"), None),
        ];

        let out = emit(spots, custom_sections(&config, 600), &[], 600);

        assert_eq!(
            out,
            concat!(
                "<<<oracle_sql:sep(58)>>>\n[[[ORCL1|product_price]]]\ndetails:ok\n",
                "<<<oracle_sql:sep(58)>>>\n[[[ORCL2|product_price]]]\ndetails:ok",
            )
        );
    }

    // TC-ORA-102: per-instance custom_metrics add to (don't replace) the global set.
    #[test]
    fn test_per_instance_custom_metric_adds_to_global() {
        let config = config_from(
            r#"
oracle:
  main:
    authentication:
      username: u
      password: p
      type: standard
    connection:
      hostname: localhost
    custom_metrics:
      - global_metric:
          sql: "select g from v"
    instances:
      - service_name: ORCL2
        custom_metrics:
          - instance_metric:
              sql: "select i from v"
"#,
        );
        let instances = config.instances().clone();
        let spot = open_spot(MiniOra::single("ORCL2"), Some(&instances[0]));

        let out = emit(vec![spot], custom_sections(&config, 600), &instances, 600);

        assert_eq!(
            out,
            concat!(
                "<<<oracle_sql:sep(58)>>>\n[[[ORCL2|global_metric]]]\ndetails:ok\n",
                "<<<oracle_sql:sep(58)>>>\n[[[ORCL2|instance_metric]]]\ndetails:ok",
            )
        );
    }

    // CMK-37363: derivation (v$database.cdb -> Tenant) + plumbing + selection.
    // Four numeric components, or the version parses to None and this is vacuous.
    #[test]
    fn test_jobs_non_cdb_selects_ten_field_query() {
        let yaml = one_builtin_section_yaml("jobs");
        let statements = selected_statements(&yaml, "TESTDB", "19.28.0.0.0", "NO");

        assert_eq!(statements.len(), 1);
        assert!(
            statements[0].contains("dba_scheduler_jobs"),
            "{}",
            statements[0]
        );
        assert!(
            !statements[0].contains("container_name"),
            "{}",
            statements[0]
        );
    }

    #[test]
    fn test_jobs_cdb_keeps_container_column() {
        let yaml = one_builtin_section_yaml("jobs");
        let statements = selected_statements(&yaml, "TESTCDB", "19.28.0.0.0", "YES");

        assert_eq!(statements.len(), 1);
        assert!(
            statements[0].contains("cdb_scheduler_jobs"),
            "{}",
            statements[0]
        );
        assert!(
            statements[0].contains("container_name"),
            "{}",
            statements[0]
        );
    }

    // CMK-37361: the item expression must branch on d.cdb, otherwise a non-CDB
    // (con_id 0) gets the item `TESTDB.TESTDB` instead of `TESTDB`.
    #[test]
    fn test_tablespaces_nocdb_query_is_cdb_flag_aware() {
        let yaml = one_builtin_section_yaml("tablespaces");
        let statements = selected_statements(&yaml, "TESTDB", "19.28.0.0.0", "NO");

        assert_eq!(statements.len(), 1);
        // One occurrence per UNION arm, so fixing only one arm still fails.
        assert_eq!(
            statements[0].matches("DECODE(d.cdb, 'NO', d.name").count(),
            2,
            "{}",
            statements[0]
        );
    }
}
