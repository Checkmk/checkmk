// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

#[cfg(not(feature = "build_system_bazel"))]
mod common;

#[cfg(feature = "build_system_bazel")]
extern crate common;

use mk_sql::config::ms_sql::Discovery;
use mk_sql::ms_sql::client::ManageEdition;
use mk_sql::platform;
#[cfg(windows)]
use mk_sql::platform::odbc;
use mk_sql::types::{Edition, InstanceName};

use std::path::PathBuf;
use std::{collections::HashSet, fs::create_dir_all};

use mk_sql::ms_sql::{
    client::{self, UniClient},
    instance::{self, SqlInstance, SqlInstanceBuilder},
    query,
    section::Section,
    sqls::{self, find_known_query},
};

#[cfg(windows)]
use mk_sql::ms_sql::instance::{create_odbc_client, obtain_properties};

use mk_sql::setup::Env;

use common::tools::{self, SqlDbEndpoint, TempDir};
use mk_sql::config::{
    ms_sql::{Config, Endpoint},
    section::names,
    section::SectionBuilder,
    CheckConfig,
};

fn expected_instances() -> HashSet<InstanceName> {
    const EXPECTED_INSTANCES: [&str; 3] = ["MSSQLSERVER", "SQLEXPRESS_NAME", "SQLEXPRESS_WOW"];

    EXPECTED_INSTANCES
        .iter()
        .map(|&s| InstanceName::from(str::to_string(s)))
        .collect()
}

fn main_instance_name() -> InstanceName {
    InstanceName::from("MSSQLSERVER")
}

#[cfg(windows)]
#[test]
fn test_environment() {
    // it seems we need this flag to properly link openssl on Windows
    let env_value = std::env::var("CFLAGS")
        .map_err(|e| anyhow::anyhow!("{e}"))
        .unwrap();
    assert_eq!(env_value, "-DNDEBUG");
}

#[test]
fn test_section_select_query() {
    let work_dir = tools::create_temp_process_dir();
    let custom_sql_path = work_dir.path().join("mssql");
    std::fs::create_dir_all(&custom_sql_path).unwrap();
    for name in [
        names::JOBS,
        names::AVAILABILITY_GROUPS,
        names::MIRRORING,
        "buzz",
    ] {
        tools::create_file_with_content(&custom_sql_path, &(name.to_owned() + ".sql"), "Bu!");
    }
    let make_section = |name: &str| Section::new(&SectionBuilder::new(name).build(), Some(100));
    for name in [
        names::JOBS,
        names::AVAILABILITY_GROUPS,
        names::MIRRORING,
        "buzz",
    ] {
        assert_eq!(
            make_section(name)
                .select_query(Some(custom_sql_path.to_owned()), 0, &Edition::Normal)
                .unwrap(),
            "Bu!"
        );
    }
}

#[cfg(windows)]
#[tokio::test(flavor = "multi_thread")]
async fn test_local_connection() {
    use mk_sql::ms_sql::defaults;

    let mut client = client::ClientBuilder::new()
        .local_by_port(Some(defaults::STANDARD_PORT.into()), None)
        .certificate(std::env::var(tools::MS_SQL_DB_CERT).ok())
        .build()
        .await
        .unwrap();
    let properties = instance::SqlInstanceProperties::obtain_by_query(&mut client)
        .await
        .unwrap();
    assert_eq!(properties.name, main_instance_name());
}

fn is_instance_good(i: &SqlInstance) -> bool {
    !i.name.to_string().is_empty()
        && i.id.to_string().contains(&i.name.to_string()[..4])
        && i.id.to_string().contains("MSSQL")
        && i.version.to_string().chars().filter(|&c| c == '.').count() == 3
        && i.port().is_some()
        && i.cluster.is_none()
        && i.version_major() >= 12
        && i.version_build() > 0
}

#[cfg(windows)]
fn make_default_endpoint() -> Endpoint {
    let ms_sql = Config::from_string(&format!(
        r#"---
mssql:
  main:
    authentication:
      username: u
      type: integrated
    connection:
      hostname: ''
      {}
"#,
        tools::make_tls_block()
    ))
    .unwrap()
    .unwrap();
    Endpoint::new(ms_sql.auth(), ms_sql.conn())
}

#[cfg(windows)]
#[tokio::test(flavor = "multi_thread")]
async fn test_obtain_all_instances_from_registry_local() {
    let endpoint = make_default_endpoint();
    let builders = instance::obtain_instance_builders(&endpoint, &[], &Discovery::default())
        .await
        .unwrap();
    let all: Vec<SqlInstance> = to_instances(builders)
        .into_iter()
        .filter(|i| expected_instances().contains(&i.name))
        .collect::<Vec<_>>();
    assert!(all.iter().all(is_instance_good), "{:?}", all);
    assert_eq!(all.len(), expected_instances().len());
    let names: HashSet<InstanceName> = all.into_iter().map(|i| i.name).collect();
    assert_eq!(names, expected_instances(), "During connecting to `local`");
}

#[cfg(windows)]
#[tokio::test(flavor = "multi_thread")]
async fn test_obtain_all_instances_from_registry_local_include() {
    use yaml_rust2::YamlLoader;
    const SOURCE: &str = r#"
    discovery:
      detect: true
      include: [MSSQLSERVER]
    "#;
    let endpoint = make_default_endpoint();
    let discovery = Discovery::from_yaml(&YamlLoader::load_from_str(SOURCE).unwrap()[0])
        .unwrap()
        .unwrap();
    assert_eq!(discovery.include().len(), 1usize, "Discovery is wrong");
    let builders = instance::obtain_instance_builders(&endpoint, &[], &discovery)
        .await
        .unwrap();
    let all: Vec<SqlInstance> = to_instances(builders);
    let names: Vec<InstanceName> = all.into_iter().map(|i| i.name).collect();
    assert_eq!(
        names,
        vec![InstanceName::from("MSSQLSERVER")],
        "During connecting to `local`"
    );
}

#[cfg(windows)]
#[tokio::test(flavor = "multi_thread")]
async fn test_obtain_all_instances_from_registry_local_exclude() {
    use yaml_rust2::YamlLoader;
    const SOURCE: &str = r#"
    discovery:
      detect: true
      exclude: [SQLEXPRESS_OLD, SQLBAD, SQLEXPRESS_AW, SQLEXPRESS_WOW]
    "#;
    let endpoint = make_default_endpoint();
    let discovery = Discovery::from_yaml(&YamlLoader::load_from_str(SOURCE).unwrap()[0])
        .unwrap()
        .unwrap();
    assert_eq!(discovery.exclude().len(), 4usize, "Discovery is wrong");
    let builders = instance::obtain_instance_builders(&endpoint, &[], &discovery)
        .await
        .unwrap();
    let all: Vec<SqlInstance> = to_instances(builders);
    let names: Vec<InstanceName> = all.into_iter().map(|i| i.name).collect();
    assert_eq!(
        names,
        vec![
            InstanceName::from("MSSQLSERVER"),
            InstanceName::from("SQLEXPRESS_NAME")
        ],
        "During connecting to `local`"
    );
}

#[cfg(windows)]
#[tokio::test(flavor = "multi_thread")]
async fn test_validate_all_instances_local() {
    use mk_sql::constants;

    let l = tools::LogMe::new("test_validate_all_instances_local").start(log::Level::Debug);
    log::info!("{:#?}", l.dir());
    let endpoint = make_default_endpoint();
    let builders = instance::obtain_instance_builders(&endpoint, &[], &Discovery::default())
        .await
        .unwrap()
        .into_iter()
        .filter(|i| expected_instances().contains(&i.get_name()))
        .collect::<Vec<_>>();
    let names: Vec<InstanceName> = builders.into_iter().map(|i| i.get_name()).collect();

    for name in names {
        let c = client::ClientBuilder::new()
            .browse(&constants::LOCAL_HOST, &name, None::<u16>)
            .build()
            .await;
        match c {
            Ok(mut c) => {
                assert!(tools::run_get_version(&mut c).await.is_some());
                let properties = instance::SqlInstanceProperties::obtain_by_query(&mut c)
                    .await
                    .unwrap();
                assert!(
                    expected_instances().contains(&properties.name),
                    "{:?}",
                    properties
                );
            }
            Err(e) if e.to_string().starts_with(instance::SQL_LOGIN_ERROR_TAG) => {
                // we may not have valid credentials to connect - it's normal
            }
            Err(e) if e.to_string().starts_with(instance::SQL_TCP_ERROR_TAG) => {
                panic!("Unexpected CONNECTION error: `{:?}`", e);
            }
            Err(e) => {
                panic!("Unexpected error: `{:?}`", e);
            }
        }
    }
}

#[tokio::test(flavor = "multi_thread")]
async fn test_remote_connection() {
    if let Some(endpoint) = tools::get_remote_sql_from_env_var() {
        let mut client = client::connect_main_endpoint(&endpoint.make_ep())
            .await
            .unwrap();
        let properties = instance::SqlInstanceProperties::obtain_by_query(&mut client)
            .await
            .unwrap();
        assert_eq!(properties.name, main_instance_name());
    } else {
        panic!(
            "Skipping remote connection test: environment variable {} not set",
            tools::SQL_DB_ENDPOINT
        );
    }
}

fn to_instances(builders: Vec<SqlInstanceBuilder>) -> Vec<SqlInstance> {
    builders
        .into_iter()
        .map(|i| i.build())
        .collect::<Vec<SqlInstance>>()
}

#[tokio::test(flavor = "multi_thread")]
async fn test_find_all_instances_remote() {
    if let Some(endpoint) = tools::get_remote_sql_from_env_var() {
        let builders =
            instance::obtain_instance_builders(&endpoint.make_ep(), &[], &Discovery::default())
                .await
                .unwrap();
        let all = to_instances(builders);
        assert!(all.iter().all(is_instance_good));
        assert_eq!(all.len(), expected_instances().len());

        let names: HashSet<InstanceName> = all.into_iter().map(|i| i.name).collect();

        assert_eq!(
            names,
            expected_instances(),
            "During connecting to `{} with `{}`. {}",
            endpoint.host,
            endpoint.user,
            "Check, please, the database is accessible and use has sysadmin rights"
        );
    } else {
        tools::skip_on_lack_of_ms_sql_endpoint();
    }
}

/// Todo(sk): split this test on per section basis.
#[tokio::test(flavor = "multi_thread")]
async fn test_validate_all_instances_remote() {
    if let Some(endpoint) = tools::get_remote_sql_from_env_var() {
        let builders =
            instance::obtain_instance_builders(&endpoint.make_ep(), &[], &Discovery::default())
                .await
                .unwrap();
        let is = to_instances(builders);

        let cfg = Config::from_string(&create_remote_config(endpoint))
            .unwrap()
            .unwrap();
        assert!(is.len() >= 3, "we need at least 3 instances to check");
        for i in is {
            match i.create_client(&cfg.endpoint(), None).await {
                Ok(mut c) => {
                    validate_all(&i, &mut c, &cfg.endpoint()).await;
                }
                Err(e) => {
                    panic!("Unexpected error: `{:?}`", e);
                }
            }
        }
    } else {
        tools::skip_on_lack_of_ms_sql_endpoint();
    }
}

fn make_section<S: Into<String>>(name: S) -> Section {
    let config_section = SectionBuilder::new(name).build();
    Section::new(&config_section, Some(100))
}

async fn validate_all(i: &SqlInstance, c: &mut UniClient, e: &Endpoint) {
    assert_eq!(c.get_edition(), Edition::Normal);
    validate_database_names(i, c).await;
    assert!(
        tools::run_get_version(c).await.is_some()
            && query::obtain_computer_name(c)
                .await
                .unwrap()
                .unwrap()
                .to_string()
                .to_lowercase()
                .starts_with("agentbuild")
    );
    validate_counters(i, c).await;
    validate_blocked_sessions(i, c).await;
    validate_all_sessions_to_check_format(i, c).await;
    assert!(i
        .generate_sessions_section(c, "SELEC * FROM sys.dm_exec_sessions", '|',)
        .await
        .contains(" error: "),);
    validate_table_spaces(i, c, e).await;
    validate_backup(i, c).await;
    validate_transaction_logs(i, c, e).await;
    validate_datafiles(i, c, e).await;
    validate_databases(i, c).await;
    validate_databases_error(i, c).await;
    validate_clusters(i, c, e).await;
    validate_connections(i, c).await;
    validate_connections_error(i, c).await;
    validate_jobs(i, e).await;
    for name in [names::JOBS, names::MIRRORING, names::AVAILABILITY_GROUPS] {
        validate_query_error(i, e, &make_section(name)).await;
    }
    validate_mirroring_section(i, e).await;
    validate_availability_groups_section(i, e).await;
}

async fn validate_database_names(instance: &SqlInstance, client: &mut UniClient) {
    let databases = instance.generate_databases(client).await;
    let expected = expected_databases();
    // O^2, but good enough for testing
    assert!(expected.iter().all(|item| databases.contains(item)),);
}

async fn validate_counters(instance: &SqlInstance, client: &mut UniClient) {
    let counters = instance
        .generate_counters_section(
            client,
            find_known_query(sqls::Id::Counters, &Edition::Normal).unwrap(),
            '|',
        )
        .await;
    let result = counters.split('\n').collect::<Vec<&str>>();
    assert!(result[0].starts_with("None|utc_time|None|"));
    assert!(result.len() > 100, "{:?}", counters);
    assert!(!counters.contains('$'));
    assert!(!counters[result[0].len()..].contains(' '));
}

async fn validate_blocked_sessions(instance: &SqlInstance, client: &mut UniClient) {
    let blocked_sessions = &instance
        .generate_sessions_section(
            client,
            find_known_query(sqls::Id::BlockedSessions, &Edition::Normal).unwrap(),
            '|',
        )
        .await;
    assert_eq!(
        blocked_sessions,
        &format!("{}|No blocking sessions\n", instance.name)
    );
}

async fn validate_all_sessions_to_check_format(instance: &SqlInstance, client: &mut UniClient) {
    let all_sessions = &instance
        .generate_sessions_section(
            client,
            find_known_query(sqls::Id::WaitingTasks, &Edition::Normal).unwrap(),
            '|',
        )
        .await;

    let lines: Vec<&str> = all_sessions.split('\n').collect::<Vec<&str>>();
    assert!(lines.last().unwrap().is_empty());
    for l in lines[..lines.len() - 1].iter() {
        assert!(
            l.starts_with(&format!("{}|", instance.name)),
            "bad line: {}",
            l
        );
        let values = l.split('|').collect::<Vec<&str>>();
        assert!(values[2].parse::<u64>().is_ok(), "wrong: {l}");
        assert!(
            values[1].is_empty() || values[1].parse::<u64>().is_ok(),
            "bad line: {}",
            l
        );
        assert!(!values[3].is_empty(), "wrong: {l}");
    }
}

async fn validate_table_spaces(
    instance: &SqlInstance,
    client: &mut UniClient,
    endpoint: &Endpoint,
) {
    let databases = instance.generate_databases(client).await;
    let expected = expected_databases();

    let result = instance
        .generate_table_spaces_section(
            endpoint,
            &databases,
            find_known_query(sqls::Id::TableSpaces, &Edition::Normal).unwrap(),
            ' ',
        )
        .await;
    let lines: Vec<&str> = result.split('\n').collect();
    assert!(lines.len() >= expected.len(), "{:?}", lines);
    assert!(lines.last().unwrap().is_empty());
    for l in lines[..lines.len() - 1].iter() {
        let values = l.split(' ').collect::<Vec<&str>>();
        assert_eq!(values[0], instance.mssql_name(), "wrong: {l}");
        assert!(values[2].parse::<f64>().is_ok(), "wrong: {l}");
        assert!(values[4].parse::<f64>().is_ok(), "wrong: {l}");
        assert!(values[6].parse::<u32>().is_ok(), "wrong: {l}");
        assert!(values[8].parse::<u32>().is_ok(), "wrong: {l}");
        assert!(values[10].parse::<u32>().is_ok(), "wrong: {l}");
        assert!(values[12].parse::<u32>().is_ok(), "wrong: {l}");
    }
}

async fn validate_backup(instance: &SqlInstance, client: &mut UniClient) {
    let mut to_be_found: HashSet<&str> = ["master", "model", "msdb"].iter().cloned().collect();

    let result = instance
        .generate_backup_section(
            client,
            find_known_query(sqls::Id::Backup, &Edition::Normal).unwrap(),
            '|',
        )
        .await;
    let lines: Vec<&str> = result.split('\n').collect();
    assert!(lines.len() >= (to_be_found.len() + 1), "{:?}", lines);

    assert!(lines.last().unwrap().is_empty());
    for l in lines[..lines.len() - 2].iter() {
        let values = l.split('|').collect::<Vec<&str>>();
        assert_eq!(values.len(), 5, "wrong: {l}");
        assert_eq!(values[0], instance.mssql_name(), "wrong: {l}");
        if to_be_found.contains(values[1]) {
            to_be_found.remove(values[1]);
        }
    }
    assert_eq!(
        lines[lines.len() - 2],
        format!("{}|tempdb|-|-|-|no backup found", instance.mssql_name())
    );
    assert!(to_be_found.is_empty());
}

async fn validate_transaction_logs(
    instance: &SqlInstance,
    client: &mut UniClient,
    endpoint: &Endpoint,
) {
    let expected: HashSet<String> = expected_databases();

    let databases = instance.generate_databases(client).await;
    let result = instance
        .generate_transaction_logs_section(
            endpoint,
            &databases,
            find_known_query(sqls::Id::TransactionLogs, &Edition::Normal).unwrap(),
            '|',
        )
        .await;

    let lines: Vec<&str> = result.split('\n').collect();
    assert!(lines.len() >= expected.len(), "{:?}", lines);
    assert!(lines.last().unwrap().is_empty());
    let mut found: HashSet<String> = HashSet::new();
    for l in lines[..lines.len() - 1].iter() {
        let values = l.split('|').collect::<Vec<&str>>();
        assert_eq!(values[0], instance.name.to_string(), "wrong: {l}");
        if expected.contains(values[1]) {
            found.insert(values[1].to_string());
        }
        assert!(values[2].to_lowercase().ends_with("log"), "wrong: {l}");
        assert!(values[3].starts_with("C:\\Program"), "wrong: {l}");
        assert!(values[3].ends_with(".ldf"), "wrong: {l}");
        assert!(values[4].parse::<u64>().is_ok(), "wrong: {l}");
        assert!(values[5].parse::<u64>().is_ok(), "wrong: {l}");
        assert!(values[6].parse::<u64>().is_ok(), "wrong: {l}");
        assert!(values[7].parse::<u64>().is_ok(), "wrong: {l}");
    }
    assert_eq!(found, expected);
}

async fn validate_datafiles(instance: &SqlInstance, client: &mut UniClient, endpoint: &Endpoint) {
    let expected: HashSet<String> = expected_databases();
    let databases = instance.generate_databases(client).await;

    let result = instance
        .generate_datafiles_section(
            endpoint,
            &databases,
            find_known_query(sqls::Id::Datafiles, &Edition::Normal).unwrap(),
            '|',
        )
        .await;

    let lines: Vec<&str> = result.split('\n').collect();
    assert!(lines.len() >= expected.len(), "{:?}", lines);
    assert!(lines.last().unwrap().is_empty());
    let mut found: HashSet<String> = HashSet::new();
    for l in lines[..lines.len() - 1].iter() {
        let values = l.split('|').collect::<Vec<&str>>();
        assert_eq!(values.len(), 8);
        assert_eq!(values[0], instance.name.to_string(), "wrong: {l}");
        if expected.contains(values[1]) {
            found.insert(values[1].to_string());
        }
        assert!(!values[2].to_lowercase().ends_with("log"), "wrong: {l}");
        assert!(values[3].starts_with("C:\\Program"), "wrong: {l}");
        assert!(
            values[3].ends_with(".mdf") || values[3].ends_with(".ndf"),
            "wrong: {l}"
        );
        assert!(values[4].parse::<u64>().is_ok(), "wrong: {l}");
        assert!(values[5].parse::<u64>().is_ok(), "wrong: {l}");
        assert!(values[6].parse::<u64>().is_ok(), "wrong: {l}");
        assert!(values[7].parse::<u64>().is_ok(), "wrong: {l}");
    }
    assert_eq!(found, expected);
}

async fn validate_databases(instance: &SqlInstance, client: &mut UniClient) {
    let expected: HashSet<String> = expected_databases();

    let databases = instance.generate_databases(client).await;
    let result = instance
        .generate_databases_section(
            client,
            &databases,
            find_known_query(sqls::Id::Databases, &Edition::Normal).unwrap(),
            '|',
        )
        .await;

    let lines: Vec<&str> = result.split('\n').collect();
    assert!(lines.len() >= expected.len(), "{:?}", lines);
    assert!(lines.last().unwrap().is_empty());
    let mut found: HashSet<String> = HashSet::new();
    for l in lines[..lines.len() - 1].iter() {
        let values = l.split('|').collect::<Vec<&str>>();
        assert_eq!(values.len(), 6);
        assert_eq!(values[0], instance.name.to_string(), "wrong: {l}");
        if expected.contains(values[1]) {
            found.insert(values[1].to_string());
        }
        assert_eq!(values[2], "ONLINE", "wrong: {l}");
        assert!(["SIMPLE", "FULL"].contains(&values[3]), "wrong: {l}");
        assert!(
            [0, 1].contains(&values[4].parse::<i32>().unwrap()),
            "wrong: {l}",
        );
        assert!(
            [0, 1].contains(&values[5].parse::<i32>().unwrap()),
            "wrong: {l}",
        );
    }
    assert_eq!(found, expected);
}

async fn validate_databases_error(instance: &SqlInstance, client: &mut UniClient) {
    let expected: HashSet<String> = expected_databases();

    let databases = instance.generate_databases(client).await;
    let result = instance
        .generate_databases_section(
            client,
            &databases,
            find_known_query(sqls::Id::BadQuery, &Edition::Normal).unwrap(),
            '|',
        )
        .await;

    let lines: Vec<&str> = result.split('\n').collect();
    assert!(lines.len() >= expected.len(), "{:?}", lines);
    assert!(lines.last().unwrap().is_empty());
    let mut found: HashSet<String> = HashSet::new();
    for l in lines[..lines.len() - 1].iter() {
        let values = l.split('|').collect::<Vec<&str>>();
        assert_eq!(values.len(), 6, "wrong: {l}");
        assert_eq!(values[0], instance.name.to_string(), "wrong: {l}");
        if expected.contains(values[1]) {
            found.insert(values[1].to_string());
        }
        assert!(values[2].contains(" error: "), "wrong: {l}");
        assert!(values[2].starts_with("ERROR: "), "wrong: {l}");
        assert_eq!(values[3..6], ["-", "-", "-"], "wrong: {l}");
    }
    assert_eq!(found, expected);
}

async fn validate_connections(instance: &SqlInstance, client: &mut UniClient) {
    let expected: HashSet<String> = expected_databases();

    let result = instance
        .generate_connections_section(
            client,
            find_known_query(sqls::Id::Connections, &Edition::Normal).unwrap(),
            ' ',
        )
        .await;

    let lines: Vec<&str> = result.split('\n').collect();
    assert!(lines.len() >= expected.len(), "{:?}", lines);
    assert!(lines.last().unwrap().is_empty());

    let mut found: HashSet<String> = HashSet::new();
    for l in lines[..lines.len() - 1].iter() {
        let values = l.split(' ').collect::<Vec<&str>>();
        assert_eq!(values.len(), 3);
        assert_eq!(values[0], instance.name.to_string(), "wrong: {l}");
        if expected.contains(values[1]) {
            found.insert(values[1].to_string());
        }
        assert!(values[2].parse::<u32>().is_ok(), "wrong: {l}");
    }
    assert_eq!(found, expected);
}

async fn validate_connections_error(instance: &SqlInstance, client: &mut UniClient) {
    let result = instance
        .generate_connections_section(
            client,
            find_known_query(sqls::Id::BadQuery, &Edition::Normal).unwrap(),
            ' ',
        )
        .await;

    let lines: Vec<&str> = result.split('\n').collect();
    assert!(lines.len() == 2, "{:?}", lines);
    assert!(lines.last().unwrap().is_empty());
    assert!(lines[0].starts_with(&format!("{} ", instance.name)));
    assert!(lines[0].contains(" error: "));
}

async fn validate_clusters(_instance: &SqlInstance, _client: &mut UniClient, _endpoint: &Endpoint) {
    // TODO(sk): implement it on arriving config
}

async fn validate_jobs(instance: &SqlInstance, endpoint: &Endpoint) {
    let result = instance
        .generate_unified_section(endpoint, &make_section(names::JOBS), None, &Edition::Normal)
        .await;
    let lines: Vec<&str> = result.split('\n').collect();
    assert_eq!(lines.len(), 3, "{:?}", lines);
    assert_eq!(lines[0], instance.name.to_string());
    assert!(lines[2].is_empty());
    let values = lines[1].split('\t').collect::<Vec<&str>>();
    assert!(
        tiberius::Uuid::parse_str(values[0]).is_ok(),
        "{:?}",
        values[0]
    );
    for column in [2, 3, 4, 5, 7, 8, 9, 10] {
        assert!(
            values[column].parse::<u32>().is_ok(),
            "{values:?} at {column} '{}'",
            values[column]
        );
    }
    assert!(values[11].len() > 10, "{values:?}");
}

async fn validate_query_error(instance: &SqlInstance, endpoint: &Endpoint, section: &Section) {
    let result = instance
        .generate_unified_section(
            endpoint,
            section,
            sqls::find_known_query(sqls::Id::BadQuery, &Edition::Normal).ok(),
            &Edition::Normal,
        )
        .await;

    let lines: Vec<&str> = result.split('\n').collect();
    assert!(lines.len() == 2, "{:?}", lines);
    assert!(lines.last().unwrap().is_empty());
    assert!(lines[0].starts_with(&format!("{} ", instance.name)));
    assert!(lines[0].contains(" error: "));
}

async fn validate_mirroring_section(instance: &SqlInstance, endpoint: &Endpoint) {
    let section = make_section(names::MIRRORING);
    let lines: Vec<String> = instance
        .generate_unified_section(endpoint, &section, None, &Edition::Normal)
        .await
        .split('\n')
        .map(|l| l.to_string())
        .collect();
    assert_eq!(lines.len(), 2, "{:?} at {}", lines, section.name());
    assert_eq!(lines[0], instance.name.to_string(), "bad line {}", lines[0]);
    assert!(lines[1].is_empty(), "bad line {}", lines[1]);
}

async fn validate_availability_groups_section(instance: &SqlInstance, endpoint: &Endpoint) {
    let section = make_section(names::AVAILABILITY_GROUPS);
    let lines: Vec<String> = instance
        .generate_unified_section(endpoint, &section, None, &Edition::Normal)
        .await
        .split('\n')
        .map(|l| l.to_string())
        .collect();
    assert_eq!(lines.len(), 1, "{:?} at {}", lines, section.name());
    assert!(lines[0].is_empty(), "bad line {}", lines[1]);
}

/// This test is ignored because it requires real credentials and real server
/// Intended to be used manually by dev to check whether all instances are accessible.
/// TODO(sk): remove on branching
#[ignore]
#[tokio::test(flavor = "multi_thread")]
async fn test_validate_all_instances_remote_extra() {
    if let Some(endpoint) = tools::get_remote_sql_from_env_var() {
        let builders =
            instance::obtain_instance_builders(&endpoint.make_ep(), &[], &Discovery::default())
                .await
                .unwrap();
        let is = to_instances(builders);
        let ms_sql = Config::from_string(
            r"---
mssql:
  main:
    authentication:
      username: your_user
      password: your_password
      type: sql_server
    connection:
      hostname: your_host
",
        )
        .unwrap()
        .unwrap();

        for i in is {
            let c = i.create_client(&ms_sql.endpoint(), None).await;
            match c {
                Ok(mut c) => assert!(
                    tools::run_get_version(&mut c).await.is_some()
                        && query::obtain_computer_name(&mut c)
                            .await
                            .unwrap()
                            .unwrap()
                            .to_string()
                            .to_lowercase()
                            .starts_with("agentbuild")
                ),
                Err(e) => {
                    panic!("Unexpected error: `{:?}`", e);
                }
            }
        }
    } else {
        tools::skip_on_lack_of_ms_sql_endpoint();
    }
}

#[tokio::test(flavor = "multi_thread")]
async fn test_get_computer_name() {
    if let Some(endpoint) = tools::get_remote_sql_from_env_var() {
        let mut client = client::connect_main_endpoint(&endpoint.make_ep())
            .await
            .unwrap();
        let name = query::obtain_computer_name(&mut client).await.unwrap();
        assert!(name
            .unwrap()
            .to_string()
            .to_lowercase()
            .starts_with("agentbuild"),);
    } else {
        tools::skip_on_lack_of_ms_sql_endpoint();
    }
}

#[tokio::test(flavor = "multi_thread")]
async fn test_get_user_name() {
    if let Some(endpoint) = tools::get_remote_sql_from_env_var() {
        let mut client = client::connect_main_endpoint(&endpoint.make_ep())
            .await
            .unwrap();
        let name = query::obtain_system_user(&mut client).await.unwrap();
        assert_eq!(name.unwrap().to_lowercase(), endpoint.user.to_lowercase());
    } else {
        tools::skip_on_lack_of_ms_sql_endpoint();
    }
}

fn make_remote_config_string(
    user: &str,
    pwd: &str,
    host: &str,
    custom_instances: bool,
    detect: bool,
) -> String {
    format!(
        r#"
mssql:
  main:
    authentication:
      username: {user}
      password: {pwd}
      type: sql_server
    connection:
      hostname: {host}
    discovery:
      detect: {}
{}
"#,
        if detect { "yes" } else { "false" },
        if custom_instances {
            make_remote_instances_config_sub_string(user, pwd, host)
        } else {
            "".to_string()
        }
    )
}

#[cfg(windows)]
fn make_local_config_string(instances: &str, detect: bool) -> String {
    format!(
        r#"
mssql:
  main:
    authentication:
      username: you
      type: integrated
    connection:
      hostname: localhost
      {}
    discovery:
      detect: {}
{instances}
"#,
        tools::make_tls_block(),
        if detect { "yes" } else { "no" }
    )
}

fn make_remote_instances_config_sub_string(user: &str, pwd: &str, host: &str) -> String {
    format!(
        r#"
    instances:
      - sid: MSSQLSERVER
        authentication:
          username: {user}
          password: {pwd}
          type: sql_server
        connection:
          hostname: {host}
          port: 1433
      - sid: WEIRD
        authentication:
          username: {user}
          password: {pwd}
          type: sql_server
        connection:
          hostname: {host}
        port: 1433
"#
    )
}

#[cfg(windows)]
fn make_tls_block_instance() -> String {
    if let Ok(certificate_path) = std::env::var(tools::MS_SQL_DB_CERT) {
        format!(
            r#"tls:
            ca: {}
            client_certificate: {}
"#,
            certificate_path, certificate_path
        )
    } else {
        String::new()
    }
}

#[cfg(windows)]
fn make_local_custom_instances_config_sub_string() -> String {
    format!(
        r#"
    instances:
      - sid: MSSQLSERVER
        authentication:
          username: user
          type: integrated
        connection:
          hostname: localhost
          port: 1433
          {}
      - sid: WEIRD
        authentication:
          username: user
          type: integrated
        connection:
          hostname: localhost
        port: 1433
"#,
        make_tls_block_instance()
    )
    .to_string()
}

#[cfg(windows)]
#[tokio::test(flavor = "multi_thread")]
async fn test_find_no_detect_local() {
    // no detect - no instances
    let mssql = mk_sql::config::ms_sql::Config::from_string(&make_local_config_string("", false))
        .unwrap()
        .unwrap();
    let instances = instance::find_all_instance_builders(&mssql).await.unwrap();
    assert_eq!(instances.len(), 0);
}

// no detect plus two custom instances
#[cfg(windows)]
#[tokio::test(flavor = "multi_thread")]
async fn test_find_no_detect_two_custom_instances_local() {
    use mk_sql::types::Port;
    let mssql = mk_sql::config::ms_sql::Config::from_string(&make_local_config_string(
        &make_local_custom_instances_config_sub_string(),
        false,
    ))
    .unwrap()
    .unwrap();
    let instances = to_instances(instance::find_all_instance_builders(&mssql).await.unwrap());
    assert_eq!(instances.len(), 1);
    assert_eq!(instances[0].name, main_instance_name());
    assert!(instances[0].edition.to_string().contains(" Edition"));
    assert!(instances[0].version.to_string().contains('.'));
    assert_eq!(instances[0].port().unwrap(), Port(1433));
    let pc = instances[0].computer_name().as_ref().unwrap().clone();
    assert!(
        !pc.to_string().is_empty(),
        "{:?}",
        instances[0].computer_name()
    );
}

#[tokio::test(flavor = "multi_thread")]
async fn test_find_no_detect_remote() {
    // no detect - no instances
    if let Some(endpoint) = tools::get_remote_sql_from_env_var() {
        let mssql = mk_sql::config::ms_sql::Config::from_string(&make_remote_config_string(
            &endpoint.user,
            &endpoint.pwd,
            &endpoint.host,
            false,
            false,
        ))
        .unwrap()
        .unwrap();
        let instances = instance::find_all_instance_builders(&mssql).await.unwrap();
        assert_eq!(instances.len(), 0);
    } else {
        tools::skip_on_lack_of_ms_sql_endpoint();
    }
}

// no detect plus two custom instances but one ok instance
#[cfg(windows)]
#[tokio::test(flavor = "multi_thread")]
async fn test_find_no_detect_two_custom_instances_remote() {
    use mk_sql::types::Port;
    if let Some(endpoint) = tools::get_remote_sql_from_env_var() {
        let mssql = mk_sql::config::ms_sql::Config::from_string(&make_remote_config_string(
            &endpoint.user,
            &endpoint.pwd,
            &endpoint.host,
            true,
            false,
        ))
        .unwrap()
        .unwrap();
        let instances = to_instances(instance::find_all_instance_builders(&mssql).await.unwrap());
        assert_eq!(instances.len(), 1);
        assert_eq!(instances[0].name, main_instance_name());
        assert!(instances[0].edition.to_string().contains(" Edition"));
        assert!(instances[0].version.to_string().contains('.'));
        assert_eq!(instances[0].port().unwrap(), Port(1433));
        let pc = instances[0].computer_name().as_ref().unwrap().clone();
        assert!(
            pc.to_string().to_uppercase().contains("AGENTBUILD"),
            "{:?}",
            instances[0].computer_name()
        );
    } else {
        tools::skip_on_lack_of_ms_sql_endpoint();
    }
}

#[tokio::test(flavor = "multi_thread")]
async fn test_check_config_exec_remote() {
    let file = tools::create_remote_config(&tools::get_remote_sql_from_env_var().unwrap());
    let check_config = CheckConfig::load_file(file.path()).unwrap();
    assert!(check_config.exec(&Env::default()).await.is_ok());
}

#[tokio::test(flavor = "multi_thread")]
async fn test_check_config_exec_local() {
    let file = tools::create_local_config();
    let res = CheckConfig::load_file(file.path());
    #[cfg(windows)]
    assert!(res.unwrap().exec(&Env::default()).await.is_ok());
    #[cfg(unix)]
    assert!(res.is_err());
}

#[test]
fn test_no_ms_sql() {
    const EXPECTED_ERROR: &str = "ERROR: Failed to gather SQL server instances";

    let file = tools::create_config_with_wrong_host();
    let r = tools::run_bin()
        .arg("-c")
        .arg(file.path().to_string_lossy().into_owned())
        .unwrap();
    let (stdout, code) = tools::get_good_results(&r).unwrap();
    assert_eq!(code, 0);
    assert!(stdout.contains(EXPECTED_ERROR), "{}", stdout);
}

#[cfg(windows)]
#[test]
fn test_run_local() {
    let file = tools::create_local_config();
    let output = tools::run_bin()
        .arg("-c")
        .arg(file.path().to_string_lossy().into_owned())
        .unwrap();
    let (stdout, code) = tools::get_good_results(&output).unwrap();
    assert_eq!(code, 0);
    assert!(stdout.contains("|state|1"), "{}", stdout);
}

#[cfg(unix)]
#[test]
fn test_run_local() {
    let file = tools::create_local_config();
    let code = tools::run_bin()
        .arg("-c")
        .arg(file.path().to_string_lossy().into_owned())
        .unwrap_err()
        .as_output()
        .unwrap()
        .status
        .code();

    assert_eq!(code, Some(1));
}

#[test]
fn test_run_remote() {
    let file = tools::create_remote_config(&tools::get_remote_sql_from_env_var().unwrap());
    assert!(tools::run_bin()
        .arg("-c")
        .arg(file.path().to_string_lossy().into_owned())
        .unwrap()
        .status
        .success());
}

#[test]
fn test_run_local_as_plugin_without_config() {
    assert!(tools::run_bin_error().status.code() == Some(1));
    assert!(
        tools::run_bin()
            .env("MK_CONFDIR", ".")
            .unwrap_err()
            .as_output()
            .unwrap()
            .status
            .code()
            == Some(1)
    );
}

#[test]
fn test_check_log_file() {
    let log_dir = tools::create_temp_process_dir();
    let log_dir_path = log_dir.path();
    let output = tools::run_bin()
        .env("MK_CONFDIR", ".")
        .env("MK_LOGDIR", log_dir_path)
        .unwrap_err();
    let (stderr, code) = tools::get_bad_results(&output).unwrap();
    assert!(
        log_dir_path.join("mk-sql_rCURRENT.log").exists(),
        "{:?}\n{:?}",
        stderr,
        code
    );
}

const EXPECTED_START: &str = r"<<<mssql_instance:sep(124)>>>
<<<mssql_databases:sep(124)>>>
<<<mssql_counters:sep(124)>>>
<<<mssql_blocked_sessions:sep(124)>>>
<<<mssql_transactionlogs:sep(124)>>>
<<<mssql_cluster:sep(124)>>>
<<<mssql_mirroring:sep(09)>>>
<<<mssql_availability_groups:sep(09)>>>
<<<mssql_connections>>>
<<<mssql_tablespaces>>>
<<<mssql_datafiles:sep(124)>>>
<<<mssql_backup:sep(124)>>>
<<<mssql_jobs:sep(09)>>>";

#[test]
fn test_run_as_plugin_with_config() {
    // Good config
    let dir = tools::create_temp_process_dir();
    for (label, content) in create_config_contents() {
        update_config_in_dir(&dir, &content);
        let exec = tools::run_bin()
            .env("MK_CONFDIR", dir.path())
            .timeout(std::time::Duration::from_secs(20))
            .unwrap();
        let (stdout, code) = tools::get_good_results(&exec).unwrap();
        assert_eq!(code, 0, "For label: {}", &label);
        assert!(
            stdout.starts_with(EXPECTED_START),
            "For label: {} \n{}\n",
            &label,
            &stdout[..EXPECTED_START.len()]
        );
        validate_stdout(&stdout, &label);
    }

    // Bad config
    update_config_in_dir(&dir, "---\n");
    let exec_err = tools::run_bin()
        .env("MK_CONFDIR", dir.path())
        .env("MK_LOGDIR", dir.path())
        .timeout(std::time::Duration::from_secs(5))
        .unwrap_err();
    let (stderr, code) = tools::get_bad_results(&exec_err).unwrap();
    assert_eq!(code, 1);
    assert!(
        stderr.starts_with("Stop on error: `No Config`\n"),
        "`{}`",
        stderr
    );
}

/// Minimally validates stdout for a given key words.
/// This is NOT real integration test. May be replaced in the future with a real testing.
fn validate_stdout(stdout: &str, label: &str) {
    let contains =
        |lines: &Vec<&str>, label: &str| lines.iter().filter(|&s| s.contains(label)).count();

    let lines: Vec<&str> = stdout.lines().collect();
    // - config entries: one per engine
    assert_eq!(contains(&lines, "|config|"), 3, "{}\n{}", &label, stdout);
    // - state entries: one per engine
    assert_eq!(contains(&lines, "|state|1"), 3, "{}\n{}", &label, stdout);
    // - details entries: one per engine
    assert_eq!(contains(&lines, "|details|"), 3, "{}\n{}", &label, stdout);

    let rtm_count = contains(&lines, "|RTM|Express Edition");
    let sp3_count = contains(&lines, "|SP3|Express Edition");
    let sp2_count = contains(&lines, "|SP2|Express Edition");
    assert_eq!(
        rtm_count + std::cmp::max(sp3_count, sp2_count),
        2,
        "{}\n{}",
        &label,
        stdout
    );

    let rtm_count = contains(&lines, "|RTM|Express Edition (64-bit)");
    let sp3_count = contains(&lines, "|SP3|Express Edition (64-bit)");
    let sp2_count = contains(&lines, "|SP2|Express Edition (64-bit)");
    assert_eq!(
        rtm_count + std::cmp::max(sp3_count, sp2_count),
        1,
        "{}\n{}",
        &label,
        stdout
    );

    assert_eq!(
        contains(&lines, "|RTM|Standard Edition"),
        1,
        "{}\n{}",
        &label,
        stdout
    );
}

/// create [local,  remote] or [local]  for Windows
/// create [remote] or []  for Linux
fn create_config_contents() -> Vec<(String, String)> {
    let mut result: Vec<(String, String)> = Vec::new();
    #[cfg(windows)]
    {
        let content_local = format!(
            r#"
---
mssql:
  main:
    authentication:
       username: "user"
       type: "integrated"
    discovery:
       detect: yes
       include: [MSSQLSERVER, SQLEXPRESS_NAME, SQLEXPRESS_WOW]
    connection:
       hostname: "localhost"
       {}
"#,
            tools::make_tls_block()
        );
        result.push(("local".to_owned(), content_local.to_string()));
    }

    if let Some(endpoint) = tools::get_remote_sql_from_env_var() {
        let content_remote = create_remote_config(endpoint);
        result.push(("remote".to_owned(), content_remote.to_string()));
    } else {
        tools::skip_on_lack_of_ms_sql_endpoint()
    }
    result
}

fn create_remote_config(endpoint: SqlDbEndpoint) -> String {
    format!(
        r#"
---
mssql:
  main:
    authentication:
       username: {}
       password: {}
       type: "sql_server"
    connection:
       hostname: {}
"#,
        endpoint.user, endpoint.pwd, endpoint.host
    )
}

#[tokio::test(flavor = "multi_thread")]
async fn test_check_config_exec_piggyback_remote() {
    let dir = tools::create_temp_process_dir();
    let content =
        create_remote_config_with_piggyback(tools::get_remote_sql_from_env_var().unwrap());
    tools::create_file_with_content(dir.path(), "mk-sql.yml", &content);
    let check_config = CheckConfig::load_file(&dir.path().join("mk-sql.yml")).unwrap();
    let output = check_config.exec(&Env::default()).await.unwrap();
    assert!(!output.is_empty());
}

#[tokio::test(flavor = "multi_thread")]
async fn test_lack_of_sql_db() {
    let dir = tools::create_temp_process_dir();
    let content = include_str!("files/test-no-ms-sql.yml");
    tools::create_file_with_content(dir.path(), "mk-sql.yml", content);
    let check_config = CheckConfig::load_file(&dir.path().join("mk-sql.yml")).unwrap();
    let output = check_config.exec(&Env::default()).await.unwrap();
    let awaited = "<<<mssql_instance:sep(124)>>>
<<<mssql_databases:sep(124)>>>
<<<mssql_counters:sep(124)>>>
<<<mssql_blocked_sessions:sep(124)>>>
<<<mssql_transactionlogs:sep(124)>>>
<<<mssql_cluster:sep(124)>>>
<<<mssql_mirroring:sep(09)>>>
<<<mssql_availability_groups:sep(09)>>>
<<<mssql_connections>>>
<<<mssql_tablespaces>>>
<<<mssql_datafiles:sep(124)>>>
<<<mssql_backup:sep(124)>>>
<<<mssql_jobs:sep(09)>>>
<<<mssql_instance:sep(124)>>>
ERROR: Failed to gather SQL server instances\n"
        .to_owned();
    assert_eq!(output.to_owned(), awaited);
}

#[cfg(windows)]
fn create_localhost_remote_config(endpoint: SqlDbEndpoint) -> String {
    format!(
        r#"
---
mssql:
  main:
    authentication:
      username: {}
      password: {}
      type: sql_server
    #connection:
    #  hostname: localhost
    #  trust_server_certificate: true
 "#,
        endpoint.user, endpoint.pwd
    )
}

#[cfg(windows)]
#[tokio::test(flavor = "multi_thread")]
async fn test_check_special() {
    let dir = tools::create_temp_process_dir();
    let content = create_localhost_remote_config(tools::get_remote_sql_from_env_var().unwrap());
    tools::create_file_with_content(dir.path(), "mk-sql.yml", &content);
    let check_config = CheckConfig::load_file(&dir.path().join("mk-sql.yml")).unwrap();
    let output = check_config.exec(&Env::default()).await.unwrap();
    assert!(!output.is_empty());
    assert!(output.contains("MSSQL_MSSQLSERVER|state|1"));
    assert!(output.contains("MSSQL_MSSQLSERVER|config|16"));
}

fn create_remote_config_with_piggyback(endpoint: SqlDbEndpoint) -> String {
    format!(
        r#"
---
mssql:
  main:
    authentication:
      username: {}
      password: {}
      type: "sql_server"
    connection:
      hostname: {}
      discovery:
      detect: yes
      include: [ "SQLEXPRESS_NAME"]
    sections:
      - instance:
      - backup:
          is_async: yes
      - counters:
          disabled: yes
    instances:
    - sid: "SQLEXPRESS_NAME"
      piggyback: # optional
        hostname: "the_host" # mandatory
        sections:
        - instance:
        - backup:
            is_async: yes
        - counters:
            disabled: yes
 "#,
        endpoint.user, endpoint.pwd, endpoint.host
    )
}

fn update_config_in_dir(dir: &TempDir, content: &str) {
    tools::create_file_with_content(dir.path(), "mk-sql.yml", content);
}

fn expected_databases() -> HashSet<String> {
    ["master", "tempdb", "model", "msdb"]
        .iter()
        .map(|&s| s.to_string())
        .collect()
}

#[tokio::test(flavor = "multi_thread")]
async fn test_check_config_custom() {
    let dir = tools::create_temp_process_dir();
    let content = create_remote_config_custom(tools::get_remote_sql_from_env_var().unwrap());
    let config = tools::create_file_with_content(dir.path(), "mk-sql.yml", &content);
    let sql_dir = dir.path().join("mssql");
    create_dir_all(&sql_dir).unwrap();
    tools::create_file_with_content(
        &sql_dir,
        "job_ext.sql",
        "select physical_name from sys.database_files",
    );

    let r = tools::run_bin()
        .env("MK_CONFDIR", dir.path())
        .arg("-c")
        .arg(config.to_string_lossy().into_owned())
        .unwrap();
    let (stdout, code) = tools::get_good_results(&r).unwrap();

    assert_eq!(code, 0);
    let sections: Vec<&str> = stdout
        .split("<<<")
        .filter(|s| !s.ends_with(">>>\n"))
        .filter(|s| s.starts_with("mssql_job_ext"))
        .map(|s| s.trim_start_matches("mssql_job_ext>>>\n"))
        .collect();
    assert_eq!(sections.len(), 3);
    let mut instances: Vec<&str> = Vec::new();
    for section in sections {
        let lines: Vec<&str> = section.split('\n').collect();
        instances.push(lines[0]);
        for line in &lines[1..lines.len() - 2] {
            assert!(line.starts_with("C:\\"), "{}", line);
            assert!(line.ends_with("df"), "{}", line);
        }
    }
    instances.sort();
    assert_eq!(
        instances,
        ["MSSQLSERVER", "SQLEXPRESS_NAME", "SQLEXPRESS_WOW"]
    );
}

fn create_remote_config_custom(endpoint: SqlDbEndpoint) -> String {
    format!(
        r#"
---
mssql:
  main:
    authentication:
      username: {}
      password: {}
      type: "sql_server"
    connection:
      hostname: {}
    sections:
      - instance:
      - job_ext:
 "#,
        endpoint.user, endpoint.pwd, endpoint.host
    )
}

#[test]
fn test_find_provided_query() {
    let s_a = make_section("A");
    let s_a2 = make_section("A2");
    let s_jobs = make_section("jobs");

    // Phase 1. None for Nothing
    assert!(s_a
        .find_provided_query(Some(PathBuf::from("aswcededcececece")), 0)
        .is_none());
    let dir = tools::create_temp_process_dir();
    let dir_to_check = || Some(dir.path().to_owned());

    // Phase 2. None for Empty Dir
    assert!(s_a.find_provided_query(dir_to_check(), 0).is_none());

    let _ = tools::create_file_with_content(dir.path(), "a.sql", "a.sql");
    let _ = tools::create_file_with_content(dir.path(), "a@20.sql", "a@20.sql");
    let _ = tools::create_file_with_content(dir.path(), "a@4.sql", "a@4.sql");
    let _ = tools::create_file_with_content(dir.path(), "jobs@100.sql", "jobs@100.sql");

    // Phase 3. section a
    assert!(s_a2.find_provided_query(dir_to_check(), 0).is_none());
    assert_eq!(s_a.find_provided_query(dir_to_check(), 0).unwrap(), "a.sql");
    assert_eq!(
        s_a.find_provided_query(dir_to_check(), 13).unwrap(),
        "a@4.sql"
    );
    assert_eq!(
        s_a.find_provided_query(dir_to_check(), 30).unwrap(),
        "a@20.sql"
    );

    assert!(s_jobs.find_provided_query(dir_to_check(), 30).is_none());
    assert_eq!(
        s_jobs.find_provided_query(dir_to_check(), 100).unwrap(),
        "jobs@100.sql"
    );
}

#[test]
fn test_get_instances() {
    let instances = platform::registry::get_instances(None);
    #[cfg(windows)]
    {
        let instances = instances
            .into_iter()
            .filter(|i| expected_instances().contains(&i.name))
            .collect::<Vec<_>>();
        assert!(!instances.is_empty());
        for instance in instances {
            assert!(instance.is_shared_memory());
            assert!(!instance.is_pipe());
            assert!(instance.is_tcp());
            assert!(instance.final_port().unwrap().value() >= 1433u16);
            assert!(!instance.is_odbc_only());
        }
    }

    #[cfg(unix)]
    assert!(instances.is_empty());
}

#[cfg(windows)]
#[test]
fn test_odbc() {
    use mk_sql::types::HostName;

    let s = odbc::make_connection_string(
        Some(&HostName::from("127.0.0.1".to_string())),
        &InstanceName::from("SQLEXPRESS_NAME"),
        Some("master"),
        None,
    );
    let r = odbc::execute(
        &s,
        sqls::find_known_query(sqls::Id::TableSpaces, &Edition::Normal).unwrap(),
        None,
    )
    .unwrap();
    assert_eq!(r.len(), 2);
    assert_eq!(r[0].headline.len(), 3);
    assert_eq!(r[1].headline.len(), 4);

    let r = odbc::execute(
        &s,
        sqls::find_known_query(sqls::Id::ComputerName, &Edition::Normal).unwrap(),
        None,
    )
    .unwrap();
    assert_eq!(r.len(), 1);
    assert_eq!(r[0].headline[0], "MachineName");
    assert!(!r[0].rows[0][0].is_empty());
}

#[cfg(windows)]
#[test]
fn test_odbc_timeout() {
    let s = odbc::make_connection_string(
        None,
        &InstanceName::from("SQLEXPRESS_XX"),
        Some("master"),
        None,
    );
    let start = std::time::Instant::now();
    let r = odbc::execute(
        &s,
        sqls::find_known_query(sqls::Id::TableSpaces, &Edition::Normal).unwrap(),
        Some(1),
    );
    assert!(r.is_err());
    let end = std::time::Instant::now();
    assert!(end - start < std::time::Duration::from_secs(2));
}

#[cfg(windows)]
#[tokio::test(flavor = "multi_thread")]
async fn test_odbc_high_level() {
    use mk_sql::{
        ms_sql::{client::ManageEdition, instance::SqlInstanceProperties},
        types::HostName,
    };

    async fn create_client(name: &str) -> UniClient {
        let instance_name = InstanceName::from(name);
        create_odbc_client(
            &HostName::from("localhost".to_string()),
            &instance_name,
            None,
        )
        .await
        .unwrap()
    }

    async fn get(name: &str) -> Option<SqlInstanceProperties> {
        let instance_name = InstanceName::from(name);
        let mut client = create_client(name).await;
        obtain_properties(&mut client, &instance_name).await
    }

    let odbc_name = get("SQLEXPRESS_NAME").await;
    assert!(odbc_name.is_some());
    let odbc_wow = get("SQLEXPRESS_WOW").await;
    assert!(odbc_wow.is_some());
    let odbc_main = get("MSSQLSERVER").await;
    assert!(odbc_main.is_some());

    assert_eq!(
        create_client("MSSQLSERVER").await.get_edition(),
        Edition::Normal
    );
}
