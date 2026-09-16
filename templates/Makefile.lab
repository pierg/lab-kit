# Lab Makefile — the kit's targets; add whatever is local below.
.DEFAULT_GOAL := help
.PHONY: help check docs serve down status ladder kit-verify kit-sync figures-check

KIT := kit
HOST ?=
PORT ?=

help:
	@echo "Targets:"
	@echo "  check       The gate: content gate (ckit check) + ladder lint + figures-check (+ local checks)"
	@echo "  docs        Serve this lab's pages on its own port (background); ✎ Annotate appears bottom-right"
	@echo "  down        Stop the server"
	@echo "  status      Is the server up?"
	@echo "  ladder      The record gate alone"
	@echo "  figures-check  Every figure generator's --check alone (a no-op until the lab has any)"
	@echo "  kit-verify  Confirm the vendored kit matches its pin"
	@echo "  kit-sync    Re-vendor the kit from its pinned sources (deliberate)"

check: kit-verify figures-check
	@ckit check
	@python3 $(KIT)/tools/ladder_lint.py

# The figure gate. Each generator's --check re-reads every number it draws out of the finding
# row that licenses it and exits non-zero on drift — a figure with a number is generated, never
# hand-drawn. Drawing the figures is NOT part of the gate (that needs rsvg and fonts); only the
# checks run here. A lab with no generators yet is not a failure — it is a lab with no figures.
figures-check:
	@if [ -d assets/figures/generators ] && ls assets/figures/generators/gen_fig_*.py >/dev/null 2>&1; then \
		cd assets/figures/generators && for g in gen_fig_*.py; do \
			echo "figures-check: $$g"; \
			grep -q -- '--check' "$$g" || { echo "figures-check: $$g has no --check mode — every figure generator must verify its drawn data against the record" >&2; exit 1; }; \
			python3 "$$g" --check || exit 1; \
		done; \
	else \
		echo "figures-check: no generators under assets/figures/generators/ — nothing to check"; \
	fi

docs:
	@HOST=$(HOST) PORT=$(PORT) ckit up

serve: docs

down:
	@ckit down

status:
	@ckit status || true

ladder:
	@python3 $(KIT)/tools/ladder_lint.py

kit-verify:
	@bash $(KIT)/verify.sh

kit-sync:
	@bash $(KIT)/verify.sh --sync
