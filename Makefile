PIPENV=./pipenv
VENV_BIN := $(dir $(shell $(PIPENV) --py))

.PHONY: install
install:
	$(PIPENV) install
	$(VENV_BIN)python setup.py develop --script-dir=bin/

.PHONY: test-dependencies
test-dependencies:
	$(PIPENV) install --dev

.PHONY: format
format: test-dependencies
	$(VENV_BIN)isort -sl -rc --atomic --quiet -- tests/ extbackup/

.PHONY: test
test: test-dependencies
	$(VENV_BIN)pytest
	$(VENV_BIN)flake8 --exclude='./.*' -- .
	$(VENV_BIN)isort -sl -rc --atomic --quiet --check-only -- tests/ extbackup/
	$(VENV_BIN)vulture extbackup/
