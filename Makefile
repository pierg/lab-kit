.DEFAULT_GOAL := help
.PHONY: help check selftest e2e

help:
	@echo "Targets:"
	@echo "  check     selftests + an end-to-end install into a scratch lab"
	@echo "  selftest  the ladder lint's planted fixtures only"

selftest:
	@python3 tools/ladder_lint.py --selftest
	@python3 tools/chronicle_lab.py --selftest
	@python3 tools/layer_findings.py --selftest

e2e:
	@bash tests/e2e.sh

check: selftest e2e
	@echo "kit check ok"
