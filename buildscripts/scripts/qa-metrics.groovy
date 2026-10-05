#!groovy

/// file: qa-metrics.groovy

void main() {
    def test_jenkins_helper = load("${checkout_dir}/buildscripts/scripts/utils/test_helper.groovy");
    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");

    def safe_branch_name = versioning.safe_branch_name();
    def container_safe_branch_name = safe_branch_name.replace(".", "-");

    def generate_full_metrics = params.GENERATE_FULL_METRICS ? "--full" : ""

    dir("${checkout_dir}") {
        // The change-quality metric walks HEAD's commit history: werk-add commits
        // (walk.py) and a rename map (components.py). The CI checkout is a shallow
        // `--depth=10` clone, too shallow for either. Deepen to 1000 commits so
        // incremental runs (which only walk commits newer than the DB watermark)
        // have ample history. Note: this bounds the rename map to the last 1000
        // commits, and a `--full` backfill will not reach older werks.
        stage("Extend git history") {
            withGerritSshKey {
                withEnv(["GIT_SSH_COMMAND=ssh -o 'StrictHostKeyChecking no' -i ${GERRIT_SSH_KEY} -l jenkins"]) {
                    sh("git fetch --depth=1000 origin master");
                }
            }
        }

        withCredentials([
            usernamePassword(
                credentialsId: 'qa-kpi-metabase-postgres',
                usernameVariable: 'QA_POSTGRES_USER',
                passwordVariable: 'QA_POSTGRES_PASSWORD'
            ),
        ]) {
            test_jenkins_helper.execute_test([
                name: "Change Quality",
                cmd: """\
export POSTGRES_HOST="dev-kpi.lan.checkmk.net"
export POSTGRES_PORT=5432
export POSTGRES_DB=metabase
bazel run //tests/qa_metrics/change_quality:push -- --repo ${checkout_dir} ${generate_full_metrics}""",
                container_name: "ubuntu-2404-${container_safe_branch_name}-latest",
                disable_hot_cache: true,
            ]);
        }
    }
}

return this;
