#!groovy

/// file: test-package-livestatus.groovy

def main() {
    def test_jenkins_helper = load("${checkout_dir}/buildscripts/scripts/utils/test_helper.groovy");

    dir("${checkout_dir}") {
        docker_image_from_alias("IMAGE_TESTING").inside() {
            test_jenkins_helper.execute_test([
                name: "test-livestatus",
                cmd: "GCC_TOOLCHAIN=/opt/gcc-14.2.0 packages/livestatus/run --clean --all",
                output_file: "livestatus.txt",
            ]);

            test_jenkins_helper.analyse_issues("GCC", "livestatus.txt");
        }
    }
}

return this;
