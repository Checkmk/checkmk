export OMD_SITE=###SITE###
export OMD_ROOT=###ROOT###

PATH=$OMD_ROOT/local/bin:$OMD_ROOT/bin:$OMD_ROOT/local/lib/perl5/bin:$PATH
export LD_LIBRARY_PATH=$OMD_ROOT/local/lib:$OMD_ROOT/lib

# Create files and directories not accessible for "world" by default
umask 0007

# enable local perl env
export PERL5LIB="$OMD_ROOT/local/lib/perl5/lib/perl5:$OMD_ROOT/lib/perl5/lib/perl5:$PERL5LIB"
export PATH="$OMD_ROOT/lib/perl5/bin:$PATH"
export MODULEBUILDRC="$OMD_ROOT/.modulebuildrc"
export PERL_MM_OPT=INSTALL_BASE="$OMD_ROOT/local/lib/perl5/"
export MANPATH="$OMD_ROOT/share/man:$MANPATH"
export MAILRC="$OMD_ROOT/etc/mail.rc"

# Make the python requests module trust the CAs configured in Check_MK
export REQUESTS_CA_BUNDLE=$OMD_ROOT/var/ssl/ca-certificates.crt

# Enforce a non localized environment. The reason for this configuration is
# that the parameters and outputs of the monitoring plug-ins are localized. If
# they are called from the core, they are always language-neutral. During
# manual testing, the plugins may behave differently depending on the
# localization of the user's environment variables. This can lead to confusion
# during tests.
export LANG=C.UTF-8 LC_ALL=C.UTF-8

# Set environment for the monitoring plugins that use state retention (like check_snmp).
export NAGIOS_PLUGIN_STATE_DIRECTORY="$OMD_ROOT/var/monitoring-plugins"
export MP_STATE_DIRECTORY=$NAGIOS_PLUGIN_STATE_DIRECTORY

if [ -f $OMD_ROOT/etc/environment ]; then
    eval $(egrep -v '^[[:space:]]*(#|$)' <$OMD_ROOT/etc/environment | sed 's/^/export /')
fi

# Only load bashrc when in a bash shell and not loaded yet.
# The load once is ensured by the variable $BASHRC.
if [ "$BASH" -a -s $OMD_ROOT/.bashrc -a -z "$BASHRC" ]; then
    . $OMD_ROOT/.bashrc
fi
