.DEFAULT_GOAL := help
.PHONY: help check selftest example example-site e2e

# content-kit's engine: $CONTENT_KIT's checkout if set, else the `ckit` on PATH, else a sibling
# ../content-kit checkout. Whichever it is goes first on PATH for everything below.
CONTENT_KIT ?=
CKIT_BIN := $(if $(CONTENT_KIT),$(abspath $(CONTENT_KIT))/bin,$(if $(shell command -v ckit),,$(abspath ../content-kit/bin)))
export PATH := $(if $(CKIT_BIN),$(CKIT_BIN):,)$(PATH)

help:
	@echo "Targets:"
	@echo "  check         selftests + the example lab's gate (strict) + an end-to-end install"
	@echo "  selftest      every tool's planted fixtures"
	@echo "  example       install both kits into example-lab/ and run its gate"
	@echo "  example-site  export example-lab/ as a static site to _site/ (BASE=/lab-kit/ for Pages)"
	@echo "  e2e           install into a copy of the example lab and a fresh one; serve, plant, drift, export"

selftest:
	@python3 tools/ladder_lint.py --selftest
	@python3 tools/chronicle_lab.py --selftest
	@python3 tools/layer_findings.py --selftest
	@python3 tools/checks_lab.py --selftest

example:
	@bash install.sh example-lab >/dev/null
	@cd example-lab && ckit lint >/dev/null && $(MAKE) --no-print-directory check

BASE ?= /
example-site: example
	@cd example-lab && ckit export --out ../_site --base $(BASE)

e2e:
	@bash tests/e2e.sh

check: selftest example e2e
	@echo "lab-kit check ok"
