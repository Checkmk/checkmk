# The build process with erlang has a strange handling of DESTDIR/INSTALL_PREFIX
# That's why we're installing it with a well-defined prefix which will be later patched to $OMD_ROOT in the Makefile
PLACE_HOLDER = "/replace-me-erlang"
