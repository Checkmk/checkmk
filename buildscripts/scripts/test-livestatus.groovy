#!groovy

/// file: test-livestatus.groovy

def main() {
    def test_jenkins_helper = load("${checkout_dir}/buildscripts/scripts/utils/test_helper.groovy");

    dir("${checkout_dir}") {
        test_jenkins_helper.execute_test([
            name: "Compile & Test Livestatus",
            cmd: "packages/livestatus/run --clean --all",
        ]);

        test_jenkins_helper.analyse_issues("GCC", "");
    }
}

return this;
