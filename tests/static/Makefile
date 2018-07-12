FILES_TO_CHECK := $(realpath $(addprefix ../../cmk/ec/,defaults.py export.py settings.py)) \
		  $(realpath $(addprefix ../../cmk/gui/,http_status.py exceptions.py i18n.py))
MYPYPATH       := $(realpath typeshed)
PIPENV         := PIPENV_NO_INHERIT=true PIPENV_VENV_IN_PROJECT=true pipenv

.PHONY: sanitize format format-yapf test-mypy

sanitize: format test-mypy

format: format-yapf

format-yapf: .venv
	$(PIPENV) run yapf -i $(FILES_TO_CHECK)

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
