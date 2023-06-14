#!groovy

/// file: test-javascript-build.groovy

def main() {
    def test_jenkins_helper = load("${checkout_dir}/buildscripts/scripts/utils/test_helper.groovy");

    dir("${checkout_dir}") {
        test_jenkins_helper.execute_test([
            name: "test-javascript-build",
            cmd: "make -C tests test-build-js-docker",
            output_file: "js-build.txt"
        ]);

        test_jenkins_helper.analyse_issues("TSJSBUILD", "js-build.txt");
    }
}

return this;
