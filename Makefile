# SPDX-License-Identifier: Apache-2.0
PYTHON ?= python3

.PHONY: check test validate demo firmware-test wheel-smoke

check:
	$(PYTHON) tools/check_all.py

test:
	PYTHONPATH=src $(PYTHON) -m unittest discover -s tests -v

validate:
	PYTHONPATH=src $(PYTHON) -m open_construction_equipment validate

demo:
	PYTHONPATH=src $(PYTHON) -m open_construction_equipment simulate

firmware-test:
	$(PYTHON) firmware/ctl01/run_host_tests.py

wheel-smoke:
	$(PYTHON) tools/wheel_smoke.py --require-build-tools
