#!groovy

/// file: test-typescript-types.groovy

def main() {
    def test_jenkins_helper = load("${checkout_dir}/buildscripts/scripts/utils/test_helper.groovy");

    dir("${checkout_dir}") {
        test_jenkins_helper.execute_test([
            name: "test-typescript-types",
            cmd: "./scripts/run-in-docker.sh ./packages/cmk-frontend/run tsc",
            output_file: "js-types.txt",
        ]);

        test_jenkins_helper.analyse_issues("TSJSTYPES", "js-types.txt");
    }
}

return this;
