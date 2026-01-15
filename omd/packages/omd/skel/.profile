export OMD_SITE=###SITE###
export OMD_ROOT=###ROOT###

PATH=$OMD_ROOT/local/bin:$OMD_ROOT/bin:$OMD_ROOT/local/lib/perl5/bin:$PATH
export LD_LIBRARY_PATH=$OMD_ROOT/local/lib:$OMD_ROOT/lib

# export special agent / active check environment
export PASSWORD_STORE_SECRET_FILE="${OMD_ROOT}/etc/password_store.secret"
export SERVER_SIDE_PROGRAM_STORAGE_PATH="${OMD_ROOT}/var/check_mk/server_side_program_storage"
export SERVER_SIDE_PROGRAM_CRASHES_PATH="${OMD_ROOT}/var/check_mk/crashes"

# Create files and directories not accessible for "world" and "group" by default
umask 0077

# enable local perl env
export PERL5LIB="$OMD_ROOT/local/lib/perl5/lib/perl5:$OMD_ROOT/lib/perl5/lib/perl5:$PERL5LIB"
export PATH="$OMD_ROOT/lib/perl5/bin:$PATH"
export MODULEBUILDRC="$OMD_ROOT/.modulebuildrc"
export PERL_MM_OPT=INSTALL_BASE="$OMD_ROOT/local/lib/perl5/"
export MANPATH="$OMD_ROOT/share/man:$MANPATH"
export MAILRC="$OMD_ROOT/etc/mail.rc"
# rabbitmq will search for its configuration under $RABBITMQ_HOME/etc, see also
# https://www.rabbitmq.com/docs/install-generic-unix#file-locations
export RABBITMQ_HOME="${OMD_ROOT}"
if [ -f "${RABBITMQ_HOME}/.erlang.cookie" ]; then
    # Early in the site initialization the file does not exist yet
    export RABBITMQ_ERLANG_COOKIE="$(cat "${RABBITMQ_HOME}/.erlang.cookie")"
fi
export RABBITMQ_NODENAME="rabbit-${OMD_SITE}@localhost"
export PATH="$OMD_ROOT/lib/rabbitmq/sbin:$PATH"

# Make the python requests module trust the CAs configured in Check_MK
export REQUESTS_CA_BUNDLE=$OMD_ROOT/var/ssl/ca-certificates.crt
# Make the openssl trust the CAs configured in Check_MK
export SSL_CERT_FILE=$OMD_ROOT/var/ssl/ca-certificates.crt

# SQLite should put the temporary DB created during VACUUM (plus some other
# temporary files) into the site, not into some global temporary directory.
# This will restrict any potential disk space issues to the site only.
export SQLITE_TMPDIR="${OMD_ROOT}/tmp"

# Enforce a non localized environment. The reason for this configuration is
# that the parameters and outputs of the monitoring plug-ins are localized. If
# they are called from the core, they are always language-neutral. During
# manual testing, the plugins may behave differently depending on the
# localization of the user's environment variables. This can lead to confusion
# during tests.
unset LC_CTYPE LC_NUMERIC LC_TIME LC_COLLATE LC_MONETARY LC_MESSAGES LC_PAPER LC_NAME LC_ADDRESS LC_TELEPHONE LC_MEASUREMENT LC_IDENTIFICATION
INSTALLED_LOCALES=$(locale -a)
for i in "C.UTF-8" "C.utf8" "en_US.utf8" "C"; do
    if echo $INSTALLED_LOCALES | grep -q -w -F "$i"; then
        export LANG="$i" LC_ALL="$i"
        break
    fi
done

# Set environment for the monitoring plugins that use state retention (like check_snmp).
export NAGIOS_PLUGIN_STATE_DIRECTORY="$OMD_ROOT/var/monitoring-plugins"
export MP_STATE_DIRECTORY=$NAGIOS_PLUGIN_STATE_DIRECTORY

if [ -f $OMD_ROOT/etc/environment ]; then
    eval $(grep -E -v '^[[:space:]]*(#|$)' <$OMD_ROOT/etc/environment | sed 's/^/export /')
fi

# Only load bashrc when in a bash shell and not loaded yet.
# The load once is ensured by the variable $BASHRC.
if [ "$BASH" -a -s $OMD_ROOT/.bashrc -a -z "$BASHRC" ]; then
    . $OMD_ROOT/.bashrc
fi
