FILES_TO_CHECK := $(realpath $(addprefix ../../cmk/ec/,defaults.py export.py main.py settings.py)) \
		  $(realpath $(wildcard ../../cmk/cee/dcd/*.py)) \
		  $(realpath $(wildcard ../../cmk/cee/dcd/connectors/*.py)) \
		  $(realpath $(wildcard ../../cmk/*.py)) \
		  $(realpath $(wildcard ../../cmk/utils/*.py)) \
		  $(realpath $(wildcard ../../cmk/notification_plugins/*.py)) \
		  $(realpath $(wildcard ../../cmk/special_agents/*.py)) \
		  $(realpath $(wildcard ../../cmk_base/*.py)) \
		  $(wildcard $(realpath ../..)/cmk_base/cee/*.py) \
		  $(wildcard $(realpath ../..)/cmk_base/automations/*.py) \
		  $(wildcard $(realpath ../..)/cmk_base/modes/*.py) \
		  $(wildcard $(realpath ../..)/cmk_base/data_sources/*.py) \
		  $(realpath $(addprefix ../../cmk/gui/,dashboard.py exceptions.py globals.py htmllib.py \
		                                        i18n.py sidebar.py sites.py table.py visuals.py permissions.py)) \
		  $(realpath $(addprefix ../../cmk/gui/watolib/,rulespecs.py)) \
		  $(realpath $(addprefix ../../cmk/gui/plugins/userdb/,htpasswd.py utils.py)) \
		  $(realpath $(wildcard ../../cmk/gui/plugins/wato/utils/*.py))

.PHONY: test-mypy

test-mypy:
	./run_mypy --config-file=$(realpath ../../mypy.ini) $(FILES_TO_CHECK)

clean:
	rm -rf .mypy_cache
