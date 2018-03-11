PIPENV=./pipenv
VENV_BIN := $(dir $(shell $(PIPENV) --py))

.PHONY: install
install:
	$(PIPENV) install
	$(VENV_BIN)python setup.py develop --script-dir=bin/

.PHONY: test
test:
	$(PIPENV) install --dev
	$(VENV_BIN)pytest
	$(VENV_BIN)flake8 --exclude='./.*' -- .
