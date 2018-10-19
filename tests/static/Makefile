FILES_TO_CHECK := $(realpath $(addprefix ../../cmk/ec/,defaults.py export.py main.py settings.py)) \
		  $(realpath $(addprefix ../../cmk/,daemon.py i18n.py paths.py regex.py render.py structured_data.py)) \
		  $(realpath $(addprefix ../../cmk/gui/,dashboard.py exceptions.py globals.py htmllib.py http_status.py \
																						i18n.py sidebar.py sites.py table.py visuals.py)) \
		  $(realpath $(addprefix ../../cmk/gui/plugins/userdb/,htpasswd.py utils.py)) \
		  $(realpath $(addprefix ../../cmk/gui/plugins/wato/utils/,base_modes.py)) \
		  $(realpath $(addprefix ../../cmk/notification_plugins/,pagerduty.py slack.py utils.py victorops.py)) \
			$(realpath $(addprefix ../../cmk_base/,check_api.py)) \
			$(realpath $(addprefix ../../agents/special/,agent_kubernetes))
MYPYPATH       := $(realpath typeshed)
PIPENV         := PIPENV_NO_INHERIT=true PIPENV_VENV_IN_PROJECT=true pipenv

.PHONY: test-mypy

test-mypy: .venv
	MYPYPATH="$(MYPYPATH)" $(PIPENV) run mypy --py2 --follow-imports=silent --strict-optional $(FILES_TO_CHECK)

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
