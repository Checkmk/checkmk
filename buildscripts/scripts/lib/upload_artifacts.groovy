// library for uploading packages
package lib

versioning = load 'buildscripts/scripts/lib/versioning.groovy'
downloads_path = "/var/downloads/checkmk/"
hashfile_extension = ".hash"

def upload(Map args) {
    // needed args + desc:
    // NAME: Name of the artifact to display
    // FILE_PATH: Path where the File is stored
    // FILE_NAME: Name of the File to be uploaded
    // CMK_VERS: Version that should be uploaded
    // UPLOAD_DEST: Where should the packages be uploaded to
    // PORT: Port fo upload dest
    def FILE_BASE = get_file_base(args.FILE_PATH)
    def ARCHIVE_BASE = get_archive_base(FILE_BASE)

    create_hash(args.FILE_PATH)

    stage(args.FILE_NAME + ' upload package and hash file') {
        via_rsync(ARCHIVE_BASE, args.CMK_VERS, args.FILE_NAME, args.UPLOAD_DEST, args.PORT)
        via_rsync(ARCHIVE_BASE, args.CMK_VERS, args.FILE_NAME + hashfile_extension, args.UPLOAD_DEST, args.PORT)
    }
}

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

def download_docker_tar(DOWNLOAD_SOURCE, PORT, CMK_VERSION, DOWNLOAD_DEST, EDITION) {
    def FILE_PATTERN = versioning.get_docker_artifact_name(EDITION, CMK_VERSION)
    download_version_dir(DOWNLOAD_SOURCE, PORT, CMK_VERSION, DOWNLOAD_DEST, FILE_PATTERN, 'docker tar')
}

def download_version_dir(DOWNLOAD_SOURCE, PORT, CMK_VERSION, DOWNLOAD_DEST, PATTERN = "*", INFO = 'all packages') {
    stage("Download from shared storage (${INFO})") {
        withCredentials([file(credentialsId: 'Release_Key', variable: 'RELEASE_KEY')]) {
            sh("mkdir -p ${DOWNLOAD_DEST}")
            sh """
                rsync --recursive --links --perms --times --verbose \
                    -e "ssh -o StrictHostKeyChecking=no -i ${RELEASE_KEY} -p ${PORT}" \
                    ${DOWNLOAD_SOURCE}/${CMK_VERSION}/${PATTERN} \
                    ${DOWNLOAD_DEST}/
            """
        }
    }
}

def upload_version_dir(SOURCE_PATH, UPLOAD_DEST, PORT)
{
    stage('Upload to download server') {
        withCredentials([file(credentialsId: 'Release_Key', variable: 'RELEASE_KEY')]) {
            sh """
                rsync -av \
                    -e "ssh -o StrictHostKeyChecking=no -i ${RELEASE_KEY} -p ${PORT}" \
                    ${SOURCE_PATH} \
                    ${UPLOAD_DEST}
            """
        }
    }
}

def get_file_base(FILE_PATH) {
    return sh(script: "dirname ${FILE_PATH}", returnStdout: true).toString().trim()
}

def get_archive_base(FILE_BASE) {
    return sh(script: "dirname ${FILE_BASE}", returnStdout: true).toString().trim()
}

def get_file_name(FILE_PATH) {
    return sh(script: "basename ${FILE_PATH}", returnStdout: true).toString().trim()
}

def via_rsync(ARCHIVE_BASE, CMK_VERS, FILE_NAME, UPLOAD_DEST, PORT) {
    withCredentials([file(credentialsId: 'Release_Key', variable: 'RELEASE_KEY')]) {
        sh """
            rsync -av --relative \
                --exclude '*dbgsym*.deb' \
                -e "ssh -o StrictHostKeyChecking=no -i ${RELEASE_KEY} -p ${PORT}" \
                ${ARCHIVE_BASE}/./${CMK_VERS}/${FILE_NAME} \
                ${UPLOAD_DEST}
        """
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

        // We also do not want to keep rc versions on the archive.
        // So rename the folder in case we have a rc
        if (TARGET_VERSION != CMK_VERS) {
            execute_cmd_on_archive_server("mv ${downloads_path}${CMK_VERS} ${downloads_path}${TARGET_VERSION};")
        }
        execute_cmd_on_archive_server("ln -sf " +
            "${downloads_path}${TARGET_VERSION} /smb-share-customer/checkmk/${TARGET_VERSION};");
    }
}

def cleanup_rc_candidates_of_version(CMK_VERS) {
    def TARGET_VERSION = versioning.strip_rc_number_from_version(CMK_VERS)
    execute_cmd_on_archive_server("rm -rf ${downloads_path}${TARGET_VERSION}-rc*;")
}

return this
