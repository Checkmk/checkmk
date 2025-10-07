# In the absence of a better tool, we use 'make' to download and unpack the Oracle Instant Client libraries for Solaris and AIX.
# Please make sure to call with GNU Make ('gmake' on Solaris, 'make' from Open Source Toolbox on AIX - Make sure that the tools are installed).
# Terminology:
#   OCI = Oracle Call Interface, the C API to Oracle databases - This is what we need.
#   Instant Client = Oracle's name for the set of libraries that provide OCI, OCCI, JDBC, etc.
# Note that we download the "Basic Lite" package, which is sufficient for our needs and smaller than the "Basic" package.

ifndef INSTANTCLIENT_ARCHIVE
  $(error Need to specify INSTANTCLIENT_ARCHIVE for placing repackaged oracle instant client libs)
endif

EXTRACT_DIR = instantclient_extracted
INSTANTCLIENT_ZIP = instantclient_19_28.zip

ORACLE_PLATFORM ?= $(shell uname)

ifeq ($(ORACLE_PLATFORM),SunOS)
  OCI_LIB_FILES = libccme_base.so libclntsh.so.12.1 libmql1.so libocci.so.11.1 liboramysql19.so BASIC_LITE_LICENSE libccme_ecc_non_fips.so libclntsh.so.18.1 libnnz19.so libocci.so.12.1 libccme_ecc.so libclntsh.so.19.1 libocci_cpp11.so.19.1 libocci.so.18.1 libclntsh.so libclntshcore.so.19.1 libocci_stlport4.so.19.1 libocci.so.19.1 libccme_asym.so libclntsh.so.10.1 libcryptocme.so libocci.so libociicus.so libccme_base_non_fips.so libclntsh.so.11.1 libipc1.so libocci.so.10.1 libocijdbc19.so
  INSTANTCLIENT_DOWNLOAD_LINK = "https://download.oracle.com/otn_software/solaris/instantclient/1928000/instantclient-basiclite-solaris.x64-19.28.0.0.0dbru.zip"
else ifeq ($(ORACLE_PLATFORM),AIX)
  OCI_LIB_FILES = BASIC_LITE_LICENSE libccme_asym.so libccme_ecc_non_fips.so libclntshcore.so libnnz19.so libocijdbc19.so libccme_base.so libclntsh.a libcryptocme.so libocci.a libons.so libccme_base_non_fips.so libclntsh.so libipc1.so libocci.so libttsh19.so libccme_ecc.so libclntshcore.a libmql1.so libociicus.so
  INSTANTCLIENT_DOWNLOAD_LINK = "https://download.oracle.com/otn_software/aix/instantclient/1928000/instantclient-basiclite-aix.ppc64-19.28.0.0.0dbru.zip"
else
  $(error Unsupported ORACLE_PLATFORM '$(ORACLE_PLATFORM)'. Set ORACLE_PLATFORM=SunOS or ORACLE_PLATFORM=AIX)
endif

$(INSTANTCLIENT_ZIP):
	curl -o $(INSTANTCLIENT_ZIP) $(INSTANTCLIENT_DOWNLOAD_LINK)

$(INSTANTCLIENT_ARCHIVE): $(INSTANTCLIENT_ZIP)
	mkdir -p $(EXTRACT_DIR)
	unzip -juo $(INSTANTCLIENT_ZIP) -d $(EXTRACT_DIR)
	rm -f $(INSTANTCLIENT_ZIP) # Secondary target can be removed, no need to keep
	mkdir -p $(shell dirname $(INSTANTCLIENT_ARCHIVE))
	cd $(EXTRACT_DIR) && tar czf $(INSTANTCLIENT_ARCHIVE) $(OCI_LIB_FILES)
	rm -rf $(EXTRACT_DIR)

# Primary target for current platform
libs: $(INSTANTCLIENT_ARCHIVE)

.PHONY: libs clean

.SECONDARY: $(INSTANTCLIENT_ZIP)

clean:
	rm -rf $(EXTRACT_DIR) $(INSTANTCLIENT_ZIP)
