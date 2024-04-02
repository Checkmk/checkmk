#!groovy

/// file: test-cmc.groovy

def main() {
    def test_jenkins_helper = load("${checkout_dir}/buildscripts/scripts/utils/test_helper.groovy");

    dir("${checkout_dir}") {
        docker_reference_image().inside() {
            test_jenkins_helper.execute_test([
                name: "test-cmc",
                cmd: "GCC_TOOLCHAIN=/opt/gcc-13.2.0 packages/cmc/run --clean --all",
                output_file: "cmc.txt",
            ]);

            test_jenkins_helper.analyse_issues("GCC", "cmc.txt");
        }
    }
}

return this;
