#!groovy

/// file: upload_artifacts.groovy

// library for uploading packages
package lib

hashfile_extension = ".hash";
downloads_path = "/var/downloads/checkmk/";
smb_base_path = "/smb-share-customer/checkmk/"
versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");

/* groovylint-disable ParameterCount */
def download_deb(DOWNLOAD_SOURCE, PORT, CMK_VERSION, DOWNLOAD_DEST, EDITION, DISTRO) {
    CMK_VERSION_RC_LESS = versioning.strip_rc_number_from_version(CMK_VERSION);
    def FILE_PATTERN = "check-mk-${EDITION}-${CMK_VERSION_RC_LESS}_0.${DISTRO}_amd64.deb";
    download_version_dir(DOWNLOAD_SOURCE, PORT, CMK_VERSION, DOWNLOAD_DEST, FILE_PATTERN, DISTRO);
}
/* groovylint-enable ParameterCount */

def download_source_tar(DOWNLOAD_SOURCE, PORT, CMK_VERSION, DOWNLOAD_DEST, EDITION) {
    CMK_VERSION_RC_LESS = versioning.strip_rc_number_from_version(CMK_VERSION);
    def FILE_PATTERN = "check-mk-${EDITION}-${CMK_VERSION_RC_LESS}.*.tar.gz";
    download_version_dir(DOWNLOAD_SOURCE, PORT, CMK_VERSION, DOWNLOAD_DEST, FILE_PATTERN, 'source tar');
}

/* groovylint-disable ParameterCount */
def download_version_dir(DOWNLOAD_SOURCE,
                         PORT,
                         CMK_VERSION,
                         DOWNLOAD_DEST,
                         PATTERN = "*",
                         INFO = 'all packages',
                         EXCLUDE_PATTERN = ""
) {
    println("""
        ||== download_version_dir() ================================================================
        || DOWNLOAD_SOURCE = |${DOWNLOAD_SOURCE}|
        || PORT =            |${PORT}|
        || CMK_VERSION =     |${CMK_VERSION}|
        || DOWNLOAD_DEST =   |${DOWNLOAD_DEST}|
        || PATTERN =         |${PATTERN}|
        || EXCLUDE_PATTERN = |${EXCLUDE_PATTERN}|
        || INFO =            |${INFO}|
        ||==========================================================================================
        """.stripMargin());

    stage("Download from shared storage (${INFO})") {
        withCredentials([
            sshUserPrivateKey(
                // We're using here a key which is usable for the fips server AND the other build nodes in order
                // to streamline the keys.
                credentialsId: 'jenkins-fips-server',
                keyFileVariable: 'ssh_key')
            ]) {
            sh("mkdir -p ${DOWNLOAD_DEST}");
            sh("""
                rsync --recursive --links --perms --times --verbose \
                    --exclude=${EXCLUDE_PATTERN} \
                    -e "ssh -o StrictHostKeyChecking=no -i ${ssh_key} -p ${PORT}" \
                    ${DOWNLOAD_SOURCE}/${CMK_VERSION}/${PATTERN} \
                    ${DOWNLOAD_DEST}/
            """);
        }
    }
}
/* groovylint-enable ParameterCount */

def upload_version_dir(SOURCE_PATH, UPLOAD_DEST, PORT, EXCLUDE_PATTERN="", ADDITONAL_ARGS="") {
    println("""
        ||== upload_version_dir ====================================================================
        || SOURCE_PATH      = |${SOURCE_PATH}|
        || UPLOAD_DEST      = |${UPLOAD_DEST}|
        || PORT             = |${PORT}|
        || EXCLUDE_PATTERN  = |${EXCLUDE_PATTERN}|
        || ADDITONAL_ARGS   = |${ADDITONAL_ARGS}|
        ||==========================================================================================
        """.stripMargin());

    withCredentials([file(credentialsId: 'Release_Key', variable: 'RELEASE_KEY')]) {    // groovylint-disable DuplicateMapLiteral
        sh("""
            rsync -av \
                ${ADDITONAL_ARGS} \
                -e "ssh -o StrictHostKeyChecking=no -i ${RELEASE_KEY} -p ${PORT}" \
                --exclude=${EXCLUDE_PATTERN} \
                ${SOURCE_PATH} \
                ${UPLOAD_DEST}
        """);
    }
}

def upload_via_rsync(archive_base, cmk_version, filename, upload_dest, upload_port) {
    println("""
        ||== upload_via_rsync() ================================================
        || archive_base = |${archive_base}|
        || cmk_version =  |${cmk_version}|
        || filename =     |${filename}|
        || upload_dest =  |${upload_dest}|
        || upload_port =  |${upload_port}|
        ||======================================================================
        """.stripMargin());

    create_hash(archive_base + "/" + cmk_version + "/" + filename);
    withCredentials([file(credentialsId: 'Release_Key', variable: 'RELEASE_KEY')]) {    // groovylint-disable DuplicateMapLiteral
        sh("""
            rsync -av --relative \
                --exclude '*dbgsym*.deb' \
                -e "ssh -o StrictHostKeyChecking=no \
                -i ${RELEASE_KEY} -p ${upload_port}" \
                ${archive_base}/./${cmk_version}/${filename} \
                ${archive_base}/./${cmk_version}/${filename}${hashfile_extension} \
                ${upload_dest}
        """);
    }
}

def upload_files_to_nexus(SOURCE_PATTERN, UPLOAD_DEST) {
    println("""
        ||== upload_files_to_nexus() ================================================
        || SOURCE_PATTERN      = |${SOURCE_PATTERN}|
        || UPLOAD_DEST      = |${UPLOAD_DEST}|
        ||======================================================================
        """.stripMargin());

    withCredentials([usernamePassword(credentialsId: 'nexus', passwordVariable: 'NEXUS_PASSWORD', usernameVariable: 'NEXUS_USERNAME')]) {
        sh("""
            for i in ${SOURCE_PATTERN}; do
                echo "Upload \${i} to Nexus";
                curl -sSf -u "${NEXUS_USERNAME}:${NEXUS_PASSWORD}" --upload-file "\${i}" "${UPLOAD_DEST}";
            done
        """);
    }
}

def create_hash(FILE_PATH) {
    sh("""
        cd \$(dirname ${FILE_PATH});
        sha256sum -- \$(basename ${FILE_PATH}) > "\$(basename ${FILE_PATH})${hashfile_extension}";
    """);
}

def execute_cmd_on_archive_server(cmd) {
    withCredentials([file(credentialsId: 'Release_Key', variable: 'RELEASE_KEY')]) {    // groovylint-disable DuplicateMapLiteral
        sh("""
           ssh -o StrictHostKeyChecking=no -i ${RELEASE_KEY} -p ${WEB_DEPLOY_PORT} ${WEB_DEPLOY_URL} "${cmd}"
        """);
    }
}

def deploy_to_website(CMK_VERS) {
    stage("Deploy to Website") {
        // CMK_VERS can contain a rc information like v2.1.0p6-rc1.
        // On the website, we only want to have official releases.
        def TARGET_VERSION = versioning.strip_rc_number_from_version(CMK_VERS);
        def SYMLINK_PATH = smb_base_path + TARGET_VERSION;

        // We also do not want to keep rc versions on the archive.
        // So rename the folder in case we have a rc
        if (TARGET_VERSION != CMK_VERS) {
            execute_cmd_on_archive_server("mv ${downloads_path}${CMK_VERS} ${downloads_path}${TARGET_VERSION};");
        }
        execute_cmd_on_archive_server("ln -sf --no-dereference ${downloads_path}${TARGET_VERSION} ${SYMLINK_PATH};");
    }
}

def update_bom_symlinks(CMK_VERS, branch_latest=false, latest=false) {
    def TARGET_VERSION = versioning.strip_rc_number_from_version(CMK_VERS);

    inside_container(set_docker_group_id: true,
        mount_credentials: true,
        privileged: true,
    ) {
        dir("${checkout_dir}") {
            if (branch_latest) {
                def bom_mapping_branch_latest = readJSON(
                    text: sh(script: """
                        scripts/run-uvenv \
                            buildscripts/scripts/assert_build_artifacts.py \
                            --editions_file "${checkout_dir}/editions.yml" \
                            dump_meta_artifacts_mapping \
                            --version ${TARGET_VERSION} \
                        """,
                        returnStdout: true)
                );
                bom_mapping_branch_latest.each { symlink, target ->
                    execute_cmd_on_archive_server(
                        "ln -sf --no-dereference ${downloads_path}${TARGET_VERSION}/${target} ${smb_base_path}${symlink};"
                    );
                }
            }

            if (latest) {
                def mapping_latest = readJSON(
                    text: sh(script: """
                        scripts/run-uvenv \
                            buildscripts/scripts/assert_build_artifacts.py \
                            --editions_file "${checkout_dir}/editions.yml" \
                            dump_meta_artifacts_mapping \
                            --version_agnostic \
                            --version ${TARGET_VERSION} \
                        """,
                        returnStdout: true)
                );
                mapping_latest.each { symlink, target ->
                    execute_cmd_on_archive_server(
                        "ln -sf --no-dereference ${downloads_path}${TARGET_VERSION}/${target} ${smb_base_path}${symlink};"
                    );
                }
            }
        }
    }

}

def cleanup_rc_candidates_of_version(CMK_VERS) {
    def TARGET_VERSION = versioning.strip_rc_number_from_version(CMK_VERS);
    execute_cmd_on_archive_server("rm -rf ${downloads_path}${TARGET_VERSION}-rc*;");
    // cleanup of tst server would come to early as "build-cmk-container" needs the rc candiates available
    // that cleanup is and will be done by bw-release
}

return this;
