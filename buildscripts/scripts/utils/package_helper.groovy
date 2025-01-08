#!groovy

/// file: package_helper.groovy

/// distro-package as well as source-package jobs need agent updater binaries
/// built the same way.
/// This file gathers the magic to accomplish this, in orde to make it re-usable
///
/// Please note that the content in here badly written and full of hard-coded
/// values which should not be here. If that gets on `master`, it should be gotten
/// rid of as soon as possible

/// Returns the Jenkins 'branch folder' of the currently running job, either with or without
/// the 'Testing/..' prefix
/// So "Testing/bla.blubb/checkmk/2.4.0/some_job" will result in
/// "Testing/bla.blubb/checkmk/2.4.0" or "checkmk/2.4.0"
def branch_base_folder(with_testing_prefix) {
    def project_name_components = currentBuild.fullProjectName.split("/").toList();
    def checkmk_index = project_name_components.indexOf('checkmk');
    if (with_testing_prefix) {
        return project_name_components[0..checkmk_index + 1].join('/');
    }
    return project_name_components[checkmk_index..checkmk_index + 1].join('/');
}

return this;
