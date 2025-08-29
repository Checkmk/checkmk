# In the absence of a better tool, we use 'make' to download and unpack the Oracle Instant Client libraries for Solaris and AIX.
# Please make sure to call with GNU Make ('gmake' on Solaris, 'make' from Open Source Toolbox on AIX - Make sure that the tools are installed).
# Terminology:
#   OCI = Oracle Call Interface, the C API to Oracle databases - This is what we need.
#   Instant Client = Oracle's name for the set of libraries that provide OCI, OCCI, JDBC, etc.
# Note that we download the "Basic Lite" package, which is sufficient for our needs and smaller than the "Basic" package.

INSTANTCLIENT_EXTRACT_DIR = instantclient_19_28

SOLARIS_LIBDIR = solaris_x86-64
SOLARIS_OCI_LIB_FILES = libccme_base.so libclntsh.so.12.1 libmql1.so libocci.so.11.1 liboramysql19.so BASIC_LITE_LICENSE libccme_ecc_non_fips.so libclntsh.so.18.1 libnnz19.so libocci.so.12.1
 libccme_ecc.so libclntsh.so.19.1 libocci_cpp11.so.19.1 libocci.so.18.1 libclntsh.so libclntshcore.so.19.1 libocci_stlport4.so.19.1 libocci.so.19.1 libccme_asym.so libclntsh.so.10.1 libcrypt
ocme.so libocci.so libociicus.so libccme_base_non_fips.so libclntsh.so.11.1 libipc1.so libocci.so.10.1 libocijdbc19.so
SOLARIS_OCI_LIBS = $(addprefix $(SOLARIS_LIBDIR)/$(INSTANTCLIENT_EXTRACT_DIR)/,$(SOLARIS_OCI_LIB_FILES))
SOLARIS_INSTANTCLIENT_DOWNLOAD_LINK = "https://download.oracle.com/otn_software/solaris/instantclient/1928000/instantclient-basiclite-solaris.x64-19.28.0.0.0dbru.zip"
SOLARIS_INSTANTCLIENT_ZIP = solaris.x86-64.instantclient_19_28.zip

AIX_LIBDIR = aix_ppc64
AIX_OCI_LIB_FILES = BASIC_LITE_LICENSE libccme_asym.so libccme_ecc_non_fips.so libclntshcore.so libnnz19.so libocijdbc19.so libccme_base.so libclntsh.a libcryptocme.so libocci.a libons.so li
bccme_base_non_fips.so libclntsh.so libipc1.so libocci.so libttsh19.so libccme_ecc.so libclntshcore.a libmql1.so libociicus.so
AIX_OCI_LIBS = $(addprefix $(AIX_LIBDIR)/$(INSTANTCLIENT_EXTRACT_DIR)/,$(AIX_OCI_LIB_FILES))
AIX_INSTANTCLIENT_DOWNLOAD_LINK = "https://download.oracle.com/otn_software/aix/instantclient/1928000/instantclient-basiclite-aix.ppc64-19.28.0.0.0dbru.zip"
AIX_INSTANTCLIENT_ZIP = aix.ppc64.instantclient_19_28.zip

DOWNLOAD_TOOL = $(shell command -v wget >/dev/null 2>&1 && echo "wget -O" || (command -v curl >/dev/null 2>&1 && echo "curl -o"))

$(SOLARIS_INSTANT_CLIENT_ZIP):
        $(DOWNLOAD_TOOL) $(SOLARIS_INSTANTCLIENT_ZIP) $(SOLARIS_INSTANTCLIENT_DOWNLOAD_LINK)

$(AIX_INSTANTCLIENT_ZIP):
        $(DOWNLOAD_TOOL) $(AIX_INSTANTCLIENT_ZIP) $(AIX_INSTANTCLIENT_DOWNLOAD_LINK)

$(SOLARIS_OCI_LIBS): $(SOLARIS_INSTANTCLIENT_ZIP)
        mkdir -p $(SOLARIS_LIBDIR)
        unzip -uo $(SOLARIS_INSTANTCLIENT_ZIP) -d $(SOLARIS_LIBDIR)
        rm $(SOLARIS_INSTANTCLIENT_ZIP) # Otherwise, the timestamps of the extracted files will be older than the zip file, causing 'make' to try to extract again next time.

$(AIX_OCI_LIBS): $(AIX_INSTANTCLIENT_ZIP)
        mkdir -p $(AIX_LIBDIR)
        unzip -uo $(AIX_INSTANTCLIENT_ZIP) -d $(AIX_LIBDIR)
        rm $(AIX_INSTANTCLIENT_ZIP) # Otherwise, the timestamps of the extracted files will be older than the zip file, causing 'make' to try to extract again next time.

solaris_libs: $(SOLARIS_OCI_LIBS)

aix_libs: $(AIX_OCI_LIBS)

.PHONY: solaris_libs aix_libs all
.SECONDARY: $(SOLARIS_INSTANTCLIENT_ZIP) $(AIX_INSTANTCLIENT_ZIP) # We don't want to download again as long as all lib files are present.
