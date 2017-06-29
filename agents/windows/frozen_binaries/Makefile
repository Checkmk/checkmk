.PHONY: clean

build: mk_logwatch.exe

include pyinstaller-deps.make

mk_logwatch.exe: src/python-$(PYTHON_VERSION).msi $(PYTHON_PACKAGES) src/vcredist_x86.exe $(PLUGINS_DIR)/mk_logwatch
	mkdir $(BUILD_DIR) ; \
		cd $(BUILD_DIR) ; \
		cp -pr $(CURDIR)/src/* . ; \
	cd $(BUILD_DIR) ; cabextract vcredist_x86.exe
	cd $(BUILD_DIR) ; cabextract vc_red.cab
	cd $(BUILD_DIR) ; export WINEPREFIX=$(BUILD_DIR) ; \
		wine vcredist_x86.exe /qb ; \
		wine msiexec /qn /i python-$(PYTHON_VERSION).msi ; \
		mv msvcr90.dll*VC90_CRT_x86* drive_c/Python27/msvcr90.dll ; \
		mv msvcp90.dll*VC90_CRT_x86* drive_c/Python27/msvcp90.dll ; \
		mv msvcm90.dll*VC90_CRT_x86* drive_c/Python27/msvcm90.dll ; \
		mv manifest*VC90_CRT_x86* drive_c/Python27/Microsoft.VC90.CRT.manifest ; \
		cp -r pip drive_c ; \
		cd drive_c/pip ; \
		wine c:\\Python27\\python.exe -m pip install --no-index --find-links="c:\\pip" * ; \
		mkdir $(BUILD_DIR)/drive_c/compile ; \
		cp $(PLUGINS_DIR)/mk_logwatch $(BUILD_DIR)/drive_c/compile/mk_logwatch.py ; \
		cd $(BUILD_DIR)/drive_c/compile ; \
		wine c:\\Python27\\Scripts\\pyinstaller.exe \
			--clean \
			--onefile \
			--upx-dir="C:\\upx" \
			--log-level=INFO \
			mk_logwatch.py ; \
		if [ ! -e dist/mk_logwatch.exe ] ; \
		then \
			echo "ERROR: Failed to create venv_wine/drive_c/compile/dist/mk_logwatch.exe" ; \
			exit 1 ; \
		fi ;
	cp $(BUILD_DIR)/drive_c/compile/dist/mk_logwatch.exe ../plugins
	rm -rf $(BUILD_DIR)

mk_jolokia.exe: src/python-$(PYTHON_VERSION).msi $(PYTHON_PACKAGES) src/vcredist_x86.exe $(PLUGINS_DIR)/mk_jolokia
	mkdir $(BUILD_DIR) ; \
		cd $(BUILD_DIR) ; \
		cp -pr $(CURDIR)/src/* . ; \
	cd $(BUILD_DIR) ; cabextract vcredist_x86.exe
	cd $(BUILD_DIR) ; cabextract vc_red.cab
	cd $(BUILD_DIR) ; export WINEPREFIX=$(BUILD_DIR) ; \
		wine vcredist_x86.exe /qb ; \
		wine msiexec /qn /i python-$(PYTHON_VERSION).msi ; \
		mv msvcr90.dll*VC90_CRT_x86* drive_c/Python27/msvcr90.dll ; \
		mv msvcp90.dll*VC90_CRT_x86* drive_c/Python27/msvcp90.dll ; \
		mv msvcm90.dll*VC90_CRT_x86* drive_c/Python27/msvcm90.dll ; \
		mv manifest*VC90_CRT_x86* drive_c/Python27/Microsoft.VC90.CRT.manifest ; \
		cp -r pip drive_c ; \
		cd drive_c/pip ; \
		wine c:\\Python27\\python.exe -m pip install --no-index --find-links="c:\\pip" * ; \
		mkdir $(BUILD_DIR)/drive_c/compile ; \
		cp $(PLUGINS_DIR)/mk_jolokia $(BUILD_DIR)/drive_c/compile/mk_jolokia.py ; \
		cd $(BUILD_DIR)/drive_c/compile ; \
		wine c:\\Python27\\Scripts\\pyinstaller.exe \
			--clean \
			--onefile \
			--upx-dir="C:\\upx" \
			--log-level=INFO \
			--hidden-import=cffi \
			mk_jolokia.py ; \
		if [ ! -e dist/mk_jolokia.exe ] ; \
		then \
			echo "ERROR: Failed to create venv_wine/drive_c/compile/dist/mk_jolokia.exe" ; \
			exit 1 ; \
		fi ;
	cp $(BUILD_DIR)/drive_c/compile/dist/mk_jolokia.exe ../plugins
	rm -rf $(BUILD_DIR)

clean:
	[ ! -d $(BUILD_DIR) ] || rm -rf $(BUILD_DIR)
