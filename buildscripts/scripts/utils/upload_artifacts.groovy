#!groovy

/// file: upload_artifacts.groovy

// library for uploading packages
package lib

hashfile_extension = ".hash"
downloads_path = "/var/downloads/checkmk/"
versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");

def download_deb(DOWNLOAD_SOURCE, PORT, CMK_VERSION, DOWNLOAD_DEST, EDITION, DISTRO) {
    CMK_VERSION_RC_LESS = versioning.strip_rc_number_from_version(CMK_VERSION);
    def FILE_PATTERN = "check-mk-${EDITION}-${CMK_VERSION_RC_LESS}_0.${DISTRO}_amd64.deb"
    download_version_dir(DOWNLOAD_SOURCE, PORT, CMK_VERSION, DOWNLOAD_DEST, FILE_PATTERN, DISTRO)
}

def download_source_tar(DOWNLOAD_SOURCE, PORT, CMK_VERSION, DOWNLOAD_DEST, EDITION) {
    CMK_VERSION_RC_LESS = versioning.strip_rc_number_from_version(CMK_VERSION);
    def FILE_PATTERN = "check-mk-${EDITION}-${CMK_VERSION_RC_LESS}.*.tar.gz"
    download_version_dir(DOWNLOAD_SOURCE, PORT, CMK_VERSION, DOWNLOAD_DEST, FILE_PATTERN, 'source tar')
}

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
        withCredentials([file(credentialsId: 'Release_Key', variable: 'RELEASE_KEY')]) {
            sh("mkdir -p ${DOWNLOAD_DEST}")
            sh """
                rsync --recursive --links --perms --times --verbose \
                    --exclude=${EXCLUDE_PATTERN} \
                    -e "ssh -o StrictHostKeyChecking=no -i ${RELEASE_KEY} -p ${PORT}" \
                    ${DOWNLOAD_SOURCE}/${CMK_VERSION}/${PATTERN} \
                    ${DOWNLOAD_DEST}/
            """
        }
    }
}

def upload_version_dir(SOURCE_PATH, UPLOAD_DEST, PORT, EXCLUDE_PATTERN="") {
    println("""
        ||== upload_version_dir ================================================================
        || SOURCE_PATH      = |${SOURCE_PATH}|
        || UPLOAD_DEST      = |${UPLOAD_DEST}|
        || PORT             = |${PORT}|
        || EXCLUDE_PATTERN  = |${EXCLUDE_PATTERN}|
        ||==========================================================================================
        """.stripMargin());
    stage('Upload to download server') {
        withCredentials([file(credentialsId: 'Release_Key', variable: 'RELEASE_KEY')]) {
            sh """
                rsync -av \
                    -e "ssh -o StrictHostKeyChecking=no -i ${RELEASE_KEY} -p ${PORT}" \
                    --exclude=${EXCLUDE_PATTERN} \
                    ${SOURCE_PATH} \
                    ${UPLOAD_DEST}
            """
        }
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

    create_hash(archive_base + "/" + cmk_version + "/" + filename)
    withCredentials([file(credentialsId: 'Release_Key', variable: 'RELEASE_KEY')]) {
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

def create_hash(FILE_PATH) {
    stage("Create file hash") {
        sh("""
            cd \$(dirname ${FILE_PATH});
            sha256sum -- \$(basename ${FILE_PATH}) > "\$(basename ${FILE_PATH})${hashfile_extension}";
        """);
    }
}

def execute_cmd_on_archive_server(cmd) {
    withCredentials([file(credentialsId: 'Release_Key', variable: 'RELEASE_KEY')]) {
        sh """
           ssh -o StrictHostKeyChecking=no -i ${RELEASE_KEY} -p ${WEB_DEPLOY_PORT} ${WEB_DEPLOY_URL} "${cmd}"
        """
    }
}

def deploy_to_website(CMK_VERS) {
    stage("Deploy to Website") {
        // CMK_VERS can contain a rc information like v2.1.0p6-rc1.
        // On the website, we only want to have official releases.
        def TARGET_VERSION = versioning.strip_rc_number_from_version(CMK_VERS)
        def SYMLINK_PATH = "/smb-share-customer/checkmk/" + TARGET_VERSION

        // We also do not want to keep rc versions on the archive.
        // So rename the folder in case we have a rc
        if (TARGET_VERSION != CMK_VERS) {
            execute_cmd_on_archive_server("mv ${downloads_path}${CMK_VERS} ${downloads_path}${TARGET_VERSION};")
        }
        execute_cmd_on_archive_server("ln -sf --no-dereference ${downloads_path}${TARGET_VERSION} ${SYMLINK_PATH};");
    }
}

def cleanup_rc_candidates_of_version(CMK_VERS) {
    def TARGET_VERSION = versioning.strip_rc_number_from_version(CMK_VERS)
    execute_cmd_on_archive_server("rm -rf ${downloads_path}${TARGET_VERSION}-rc*;")
}

return this
