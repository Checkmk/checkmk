// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

mod common;
use std::collections::HashSet;

use check_sql::{
    config::yaml::trace_tools,
    ms_sql::{
        client::{self, Client},
        instance::{self, SqlInstance, SqlInstanceBuilder},
        query,
        section::Section,
        sqls,
    },
};

use check_sql::setup::Env;

use check_sql::config::{
    ms_sql::{Config, Endpoint},
    section::names,
    section::SectionBuilder,
    CheckConfig,
};
use common::tools::{self, SqlDbEndpoint};
use tempfile::TempDir;

fn expected_instances() -> Vec<String> {
    const EXPECTED_INSTANCES: [&str; 3] = ["MSSQLSERVER", "SQLEXPRESS_NAME", "SQLEXPRESS_WOW"];

    EXPECTED_INSTANCES
        .iter()
        .map(|&s| str::to_string(s))
        .collect()
}

#[cfg(windows)]
#[tokio::test(flavor = "multi_thread")]
async fn test_local_connection() {
    let mut client = client::create_local(None, check_sql::ms_sql::defaults::STANDARD_PORT)
        .await
        .unwrap();
    let properties = instance::SqlInstanceProperties::obtain_by_query(&mut client)
        .await
        .unwrap();
    assert_eq!(properties.name, "MSSQLSERVER");
}

fn is_instance_good(i: &SqlInstance) -> bool {
    !i.name.is_empty()
        && i.id.contains(&i.name[..4])
        && i.id.contains("MSSQL")
        && i.version.chars().filter(|&c| c == '.').count() == 3
        && i.port().is_some()
        && i.cluster.is_none()
}

#[cfg(windows)]
#[tokio::test(flavor = "multi_thread")]
async fn test_obtain_all_instances_from_registry_local() {
    let builders = instance::obtain_instance_builders_from_registry(&Endpoint::default())
        .await
        .unwrap();
    let all: Vec<SqlInstance> = to_instances([&builders.0[..], &builders.1[..]].concat());
    assert!(all.iter().all(is_instance_good), "{:?}", all);
    let mut names: Vec<String> = all.into_iter().map(|i| i.name).collect();
    names.sort();

    assert_eq!(names, expected_instances(), "During connecting to `local`");
}

#[cfg(windows)]
#[tokio::test(flavor = "multi_thread")]
async fn test_validate_all_instances_local() {
    let builders = instance::obtain_instance_builders_from_registry(&Endpoint::default())
        .await
        .unwrap();
    let names: Vec<String> = [&builders.0[..], &builders.1[..]]
        .concat()
        .into_iter()
        .map(|i| i.get_name())
        .collect();

    for name in names {
        let c = client::create_instance_local(&name, None, None).await;
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
        let mut client = client::create_on_endpoint(&endpoint.make_ep())
            .await
            .unwrap();
        let properties = instance::SqlInstanceProperties::obtain_by_query(&mut client)
            .await
            .unwrap();
        assert_eq!(properties.name, "MSSQLSERVER");
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
        let builders = instance::obtain_instance_builders_from_registry(&endpoint.make_ep())
            .await
            .unwrap();
        let all = to_instances([&builders.0[..], &builders.1[..]].concat());
        assert!(all.iter().all(is_instance_good));
        let mut names: Vec<String> = all.into_iter().map(|i| i.name).collect();
        names.sort();

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
        let instances = instance::obtain_instance_builders_from_registry(&endpoint.make_ep())
            .await
            .unwrap();
        let is = to_instances([&instances.0[..], &instances.1[..]].concat());

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
    Section::new(&config_section, 100)
}

async fn validate_all(i: &SqlInstance, c: &mut Client, e: &Endpoint) {
    validate_database_names(i, c).await;
    assert!(
        tools::run_get_version(c).await.is_some()
            && query::get_computer_name(c, sqls::QUERY_COMPUTER_NAME)
                .await
                .unwrap()
                .unwrap()
                .to_lowercase()
                .starts_with("agentbuild")
    );
    validate_counters(i, c).await;
    validate_blocked_sessions(i, c).await;
    validate_all_sessions_to_check_format(i, c).await;
    assert!(i
        .generate_blocking_sessions_section(c, sqls::BAD_QUERY, '|',)
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

async fn validate_database_names(instance: &SqlInstance, client: &mut Client) {
    let databases = instance.generate_databases(client).await;
    let expected = expected_databases();
    // O^2, but good enough for testing
    assert!(expected.iter().all(|item| databases.contains(item)),);
}

async fn validate_counters(instance: &SqlInstance, client: &mut Client) {
    let counters = instance.generate_counters_entry(client, '|').await;
    assert!(
        counters.split('\n').collect::<Vec<&str>>().len() > 100,
        "{:?}",
        counters
    );
    assert!(!counters.contains(' '));
    assert!(!counters.contains('$'));
}

async fn validate_blocked_sessions(instance: &SqlInstance, client: &mut Client) {
    let blocked_sessions = &instance
        .generate_blocking_sessions_section(client, &sqls::get_blocking_sessions_query(), '|')
        .await;
    assert_eq!(
        blocked_sessions,
        &format!("{}|No blocking sessions\n", instance.name)
    );
}

async fn validate_all_sessions_to_check_format(instance: &SqlInstance, client: &mut Client) {
    let all_sessions = &instance
        .generate_blocking_sessions_section(client, sqls::QUERY_WAITING_TASKS, '|')
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

async fn validate_table_spaces(instance: &SqlInstance, client: &mut Client, endpoint: &Endpoint) {
    let databases = instance.generate_databases(client).await;
    let expected = expected_databases();

    let result = instance
        .generate_table_spaces_section(endpoint, &databases, ' ')
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

async fn validate_backup(instance: &SqlInstance, client: &mut Client) {
    let mut to_be_found: HashSet<&str> = ["master", "model", "msdb"].iter().cloned().collect();

    let result = instance.generate_backup_section(client, '|').await;
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
        format!("{}|tempdb|-|-|-|No backup found", instance.mssql_name())
    );
    assert!(to_be_found.is_empty());
}

async fn validate_transaction_logs(
    instance: &SqlInstance,
    client: &mut Client,
    endpoint: &Endpoint,
) {
    let expected: HashSet<String> = expected_databases();

    let databases = instance.generate_databases(client).await;
    let result = instance
        .generate_transaction_logs_section(endpoint, &databases, '|')
        .await;

    let lines: Vec<&str> = result.split('\n').collect();
    assert!(lines.len() >= expected.len(), "{:?}", lines);
    assert!(lines.last().unwrap().is_empty());
    let mut found: HashSet<String> = HashSet::new();
    for l in lines[..lines.len() - 1].iter() {
        let values = l.split('|').collect::<Vec<&str>>();
        assert_eq!(values[0], instance.name, "wrong: {l}");
        if expected.contains(&values[1].to_string()) {
            found.insert(values[1].to_string());
        }
        assert!(values[2].to_lowercase().ends_with("log"), "wrong: {l}");
        assert!(values[3].starts_with("C:\\Program"), "wrong: {l}");
        assert!(values[4].parse::<u64>().is_ok(), "wrong: {l}");
        assert!(values[5].parse::<u64>().is_ok(), "wrong: {l}");
        assert!(values[6].parse::<u64>().is_ok(), "wrong: {l}");
        assert!(values[7].parse::<u64>().is_ok(), "wrong: {l}");
    }
    assert_eq!(found, expected);
}

async fn validate_datafiles(instance: &SqlInstance, client: &mut Client, endpoint: &Endpoint) {
    let expected: HashSet<String> = expected_databases();
    let databases = instance.generate_databases(client).await;

    let result = instance
        .generate_transaction_logs_section(endpoint, &databases, '|')
        .await;

    let lines: Vec<&str> = result.split('\n').collect();
    assert!(lines.len() >= expected.len(), "{:?}", lines);
    assert!(lines.last().unwrap().is_empty());
    let mut found: HashSet<String> = HashSet::new();
    for l in lines[..lines.len() - 1].iter() {
        let values = l.split('|').collect::<Vec<&str>>();
        assert_eq!(values.len(), 8);
        assert_eq!(values[0], instance.name, "wrong: {l}");
        if expected.contains(&values[1].to_string()) {
            found.insert(values[1].to_string());
        }
        assert!(values[2].to_lowercase().ends_with("log"), "wrong: {l}");
        assert!(values[3].starts_with("C:\\Program"), "wrong: {l}");
        assert!(values[4].parse::<u64>().is_ok(), "wrong: {l}");
        assert!(values[5].parse::<u64>().is_ok(), "wrong: {l}");
        assert!(values[6].parse::<u64>().is_ok(), "wrong: {l}");
        assert!(values[7].parse::<u64>().is_ok(), "wrong: {l}");
    }
    assert_eq!(found, expected);
}

async fn validate_databases(instance: &SqlInstance, client: &mut Client) {
    let expected: HashSet<String> = expected_databases();

    let result = instance
        .generate_databases_section(client, sqls::QUERY_DATABASES, '|')
        .await;

    let lines: Vec<&str> = result.split('\n').collect();
    assert!(lines.len() >= expected.len(), "{:?}", lines);
    assert!(lines.last().unwrap().is_empty());
    let mut found: HashSet<String> = HashSet::new();
    for l in lines[..lines.len() - 1].iter() {
        let values = l.split('|').collect::<Vec<&str>>();
        assert_eq!(values.len(), 6);
        assert_eq!(values[0], instance.name, "wrong: {l}");
        if expected.contains(&values[1].to_string()) {
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

async fn validate_databases_error(instance: &SqlInstance, client: &mut Client) {
    let expected: HashSet<String> = expected_databases();

    let result = instance
        .generate_databases_section(client, sqls::BAD_QUERY, '|')
        .await;

    let lines: Vec<&str> = result.split('\n').collect();
    assert!(lines.len() >= expected.len(), "{:?}", lines);
    assert!(lines.last().unwrap().is_empty());
    let mut found: HashSet<String> = HashSet::new();
    for l in lines[..lines.len() - 1].iter() {
        let values = l.split('|').collect::<Vec<&str>>();
        assert_eq!(values.len(), 6);
        assert_eq!(values[0], instance.name, "wrong: {l}");
        if expected.contains(&values[1].to_string()) {
            found.insert(values[1].to_string());
        }
        assert!(values[2].contains(" error: "), "wrong: {l}");
        assert_eq!(values[3..6], ["-", "-", "-"], "wrong: {l}");
    }
    assert_eq!(found, expected);
}

async fn validate_connections(instance: &SqlInstance, client: &mut Client) {
    let expected: HashSet<String> = expected_databases();

    let result = instance
        .generate_connections_section(client, sqls::QUERY_CONNECTIONS, ' ')
        .await;

    let lines: Vec<&str> = result.split('\n').collect();
    assert!(lines.len() >= expected.len(), "{:?}", lines);
    assert!(lines.last().unwrap().is_empty());

    let mut found: HashSet<String> = HashSet::new();
    for l in lines[..lines.len() - 1].iter() {
        let values = l.split(' ').collect::<Vec<&str>>();
        assert_eq!(values.len(), 3);
        assert_eq!(values[0], instance.name, "wrong: {l}");
        if expected.contains(&values[1].to_string()) {
            found.insert(values[1].to_string());
        }
        assert!(values[2].parse::<u32>().is_ok(), "wrong: {l}");
    }
    assert_eq!(found, expected);
}

async fn validate_connections_error(instance: &SqlInstance, client: &mut Client) {
    let result = instance
        .generate_connections_section(client, sqls::BAD_QUERY, ' ')
        .await;

    let lines: Vec<&str> = result.split('\n').collect();
    assert!(lines.len() == 2, "{:?}", lines);
    assert!(lines.last().unwrap().is_empty());
    assert!(lines[0].starts_with(&format!("{} ", instance.name)));
    assert!(lines[0].contains(" error: "));
}

async fn validate_clusters(_instance: &SqlInstance, _client: &mut Client, _endpoint: &Endpoint) {
    // TODO(sk): implement it on arriving config
}

async fn validate_jobs(instance: &SqlInstance, endpoint: &Endpoint) {
    let result = instance
        .generate_query_section(endpoint, &make_section(names::JOBS), None)
        .await;
    let lines: Vec<&str> = result.split('\n').collect();
    assert_eq!(lines.len(), 3, "{:?}", lines);
    assert_eq!(lines[0], instance.name);
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
        .generate_query_section(endpoint, section, Some(sqls::BAD_QUERY))
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
        .generate_query_section(endpoint, &section, None)
        .await
        .split('\n')
        .map(|l| l.to_string())
        .collect();
    assert_eq!(lines.len(), 2, "{:?} at {}", lines, section.name());
    assert_eq!(lines[0], instance.name);
    assert!(lines[1].is_empty(), "bad line {}", lines[1]);
}

async fn validate_availability_groups_section(instance: &SqlInstance, endpoint: &Endpoint) {
    let section = make_section(names::AVAILABILITY_GROUPS);
    let lines: Vec<String> = instance
        .generate_query_section(endpoint, &section, None)
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
        let instances = instance::obtain_instance_builders_from_registry(&endpoint.make_ep())
            .await
            .unwrap();
        let is = to_instances([&instances.0[..], &instances.1[..]].clone().concat());
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
                        && query::get_computer_name(&mut c, sqls::QUERY_COMPUTER_NAME)
                            .await
                            .unwrap()
                            .unwrap()
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
        let mut client = client::create_on_endpoint(&endpoint.make_ep())
            .await
            .unwrap();
        let name = query::get_computer_name(&mut client, sqls::QUERY_COMPUTER_NAME)
            .await
            .unwrap();
        assert!(name
            .clone()
            .unwrap()
            .to_lowercase()
            .starts_with("agentbuild"),);
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
    discovery:
      detect: {}
{instances}
"#,
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
fn make_local_custom_instances_config_sub_string() -> String {
    r#"
    instances:
      - sid: MSSQLSERVER
        authentication:
          username: user
          type: integrated
        connection:
          hostname: localhost
          port: 1433
      - sid: WEIRD
        authentication:
          username: user
          type: integrated
        connection:
          hostname: localhost
        port: 1433
"#
    .to_string()
}

#[cfg(windows)]
#[tokio::test(flavor = "multi_thread")]
async fn test_find_no_detect_local() {
    // no detect - no instances
    let mssql =
        check_sql::config::ms_sql::Config::from_string(&make_local_config_string("", false))
            .unwrap()
            .unwrap();
    let instances = instance::find_all_instance_builders(&mssql).await.unwrap();
    assert_eq!(instances.len(), 0);
}

// no detect plus two custom instances
#[cfg(windows)]
#[tokio::test(flavor = "multi_thread")]
async fn test_find_no_detect_two_custom_instances_local() {
    let mssql = check_sql::config::ms_sql::Config::from_string(&make_local_config_string(
        &make_local_custom_instances_config_sub_string(),
        false,
    ))
    .unwrap()
    .unwrap();
    let instances = to_instances(instance::find_all_instance_builders(&mssql).await.unwrap());
    assert_eq!(instances.len(), 1);
    assert_eq!(instances[0].name, "MSSQLSERVER");
    assert!(instances[0].edition.contains(" Edition"));
    assert!(instances[0].version.contains('.'));
    assert_eq!(instances[0].port(), Some(1433));
    let pc = instances[0].computer_name().as_ref().unwrap().clone();
    assert!(!pc.is_empty(), "{:?}", instances[0].computer_name());
}

#[tokio::test(flavor = "multi_thread")]
async fn test_find_no_detect_remote() {
    // no detect - no instances
    if let Some(endpoint) = tools::get_remote_sql_from_env_var() {
        let mssql = check_sql::config::ms_sql::Config::from_string(&make_remote_config_string(
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
    if let Some(endpoint) = tools::get_remote_sql_from_env_var() {
        let mssql = check_sql::config::ms_sql::Config::from_string(&make_remote_config_string(
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
        assert_eq!(instances[0].name, "MSSQLSERVER");
        assert!(instances[0].edition.contains(" Edition"));
        assert!(instances[0].version.contains('.'));
        assert_eq!(instances[0].port(), Some(1433));
        let pc = instances[0].computer_name().as_ref().unwrap().clone();
        assert!(
            pc.to_uppercase().contains("AGENTBUILD"),
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
        .arg(&file.path().to_string_lossy().into_owned())
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
        .arg(&file.path().to_string_lossy().into_owned())
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
        .arg(&file.path().to_string_lossy().into_owned())
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
        .arg(&file.path().to_string_lossy().into_owned())
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
    let _ = tools::run_bin()
        .env("MK_CONFDIR", ".")
        .env("MK_LOGDIR", log_dir_path)
        .unwrap_err()
        .as_output()
        .unwrap();
    assert!(log_dir_path.join("check-sql_rCURRENT.log").exists());
}

const EXPECTED_START: &str = r"<<<mssql_instance:sep(124)>>>
<<<mssql_databases:sep(124)>>>
<<<mssql_counters:sep(124)>>>
<<<mssql_blocked_sessions:sep(124)>>>
<<<mssql_transactionlogs:sep(124)>>>
<<<mssql_clusters:sep(124)>>>
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
    assert_eq!(stderr, "Error: No Config\n");
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
    assert_eq!(
        contains(&lines, "|RTM|Express Edition"),
        2,
        "{}\n{}",
        &label,
        stdout
    );
    assert_eq!(
        contains(&lines, "|RTM|Express Edition (64-bit)"),
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
        let content_local = r#"
---
mssql:
  main:
    authentication:
       username: "user"
       type: "integrated"
    connection:
       hostname: "localhost"
"#;
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
    tools::create_file_with_content(dir.path(), "check-sql.yml", &content);
    let check_config = CheckConfig::load_file(&dir.path().join("check-sql.yml")).unwrap();
    let output = check_config.exec(&Env::default()).await.unwrap();
    trace_tools::write_stderr(&output);
    assert!(!output.is_empty());
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
    tools::create_file_with_content(dir.path(), "check-sql.yml", content);
}

fn expected_databases() -> HashSet<String> {
    ["master", "tempdb", "model", "msdb"]
        .iter()
        .map(|&s| s.to_string())
        .collect()
}
