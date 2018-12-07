FILES_TO_CHECK := $(realpath $(addprefix ../../cmk/ec/,defaults.py export.py main.py settings.py)) \
		  $(realpath $(addprefix ../../cmk/cee/dcd/,main.py Config.py Manager.py CommandManager.py)) \
		  $(realpath $(addprefix ../../cmk/cee/dcd/connectors,piggyback.py utils.py)) \
		  $(realpath $(wildcard ../../cmk/*.py)) \
		  $(realpath $(wildcard ../../cmk/notification_plugins/*.py)) \
		  $(realpath $(wildcard ../../cmk_base/*.py)) \
		  $(realpath $(addprefix ../../cmk/gui/,dashboard.py exceptions.py globals.py htmllib.py http_status.py \
		                                        i18n.py sidebar.py sites.py table.py visuals.py permissions.py)) \
		  $(realpath $(addprefix ../../cmk/gui/plugins/userdb/,htpasswd.py utils.py)) \
		  $(realpath $(wildcard ../../cmk/gui/plugins/wato/utils/*.py)) \
		  $(realpath $(addprefix ../../agents/special/,agent_kubernetes))
MYPYPATH       := $(realpath typeshed)
PIPENV         := PIPENV_NO_INHERIT=true PIPENV_VENV_IN_PROJECT=true pipenv

.PHONY: test-mypy

test-mypy: .venv
	./run_mypy --config-file=$(realpath ../../mypy.ini) $(FILES_TO_CHECK)

Pipfile.lock: Pipfile
	$(PIPENV) lock
# TODO: pipenv and make don't really cooperate nicely: Locking alone already
# creates a virtual environment with setuptools/pip/wheel. This could lead to a
# wrong up-to-date status of it later, so let's remove it here. What we really
# want is a check if the contents of .venv match the contents of Pipfile.lock.
# We should do this via some move-if-change Kung Fu, but for now rm suffices.
	rm -rf .venv

.venv: Pipfile.lock
	$(PIPENV) install --dev
	$(PIPENV) clean
# TODO: Part 2 of the hack for the Pipfile.lock target.
	touch .venv

clean:
	rm -rf .mypy_cache .venv
