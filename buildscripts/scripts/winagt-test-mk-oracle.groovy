#!groovy

/// file: winagt-test-mk-oracle.groovy

void main() {
    dir("${checkout_dir}/packages/mk-oracle") {
        withCredentials([
            string(
                credentialsId: "CI_ORA2_DB_TEST_PASSWORD",
                variable: "CI_ORA2_DB_TEST_PASSWORD"),
            string(
                credentialsId: "CI_ORA_TEST_PASSWORD",
                variable: "CI_ORA_TEST_PASSWORD"),
        ]) {
            stage("Run mk-oracle component tests") {
                bat("call run.cmd --component-tests");
            }
        }
    }
}

return this;
