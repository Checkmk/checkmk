#!groovy

/// file: test-javascript-build.groovy

def main() {
    def test_jenkins_helper = load("${checkout_dir}/buildscripts/scripts/utils/test_helper.groovy");

    dir("${checkout_dir}/packages/cmk-frontend") {
        test_jenkins_helper.execute_test([
            name: "test-javascript-build",
            cmd: "./scripts/run-in-docker.sh ./packages/cmk-frontend/run build",
            output_file: "js-build.txt",
        ]);

        test_jenkins_helper.analyse_issues("TSJSBUILD", "js-build.txt");
    }
}

return this;
