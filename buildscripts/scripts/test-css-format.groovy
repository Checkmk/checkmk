#!groovy

/// file: test-css-format.groovy

def main() {
    def test_jenkins_helper = load("${checkout_dir}/buildscripts/scripts/utils/test_helper.groovy");

    dir("${checkout_dir}/packages/cmk-frontend") {
        test_jenkins_helper.execute_test([
            name: "test-javascript-lint",
            cmd: "./scripts/run-in-docker.sh ./packages/cmk-frontend/run prettier --css",
            output_file: "css-prettier.txt",
        ]);

        test_jenkins_helper.analyse_issues("PRETTIER", "css-prettier.txt");
    }
}

return this;
