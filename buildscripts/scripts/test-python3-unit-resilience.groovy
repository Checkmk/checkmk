#!groovy

/// file: test-python3-unit-resilience.groovy

def main() {
    def test_jenkins_helper = load("${checkout_dir}/buildscripts/scripts/utils/test_helper.groovy");
    def relative_result_path = "results/junit-resilience.xml"
    def result_path = "${checkout_dir}/${relative_result_path}";
    inside_container(
        init: true,
        ulimit_nofile: 1024,
    ) {
        stage('run test-unit-resilience') {
            dir("${checkout_dir}") {
                try {
                    withEnv([
                        "PYTEST_ADDOPTS='--junitxml=${result_path}'",
                    ]) {
                        sh("make -C tests test-unit-resilience");
                    }
                } catch(Exception e) {
                    // We want to keep failed resilience builds in order to follow a process, see CMK-14487
                    currentBuild.setKeepLog(true);
                    throw e;
                } finally {
                    test_jenkins_helper.analyse_issues("JUNIT", relative_result_path);
                }
            }
        }
    }
}

return this;
