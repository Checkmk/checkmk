#!groovy

/// file: test-javascript-format.groovy

def main() {
    def test_jenkins_helper = load("${checkout_dir}/buildscripts/scripts/utils/test_helper.groovy");

    dir("${checkout_dir}/packages/cmk-frontend") {
        test_jenkins_helper.execute_test([
            name: "test-javascript-format",
            cmd: "./scripts/run-in-docker.sh ./packages/cmk-frontend/run check-prettie --js",
            output_file: "js-prettier.txt",
        ]);

        test_jenkins_helper.analyse_issues("PRETTIER", "js-prettier.txt");
    }
}

return this;
