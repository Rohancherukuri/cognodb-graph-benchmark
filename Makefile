.PHONY: setup infra-up infra-down dataset bench report test clean

setup:
	pip install -e ".[dev]"
	cp -n .env.example .env || true

infra-up:
	bash scripts/start_infra.sh

infra-down:
	bash scripts/stop_infra.sh

dataset:
	benchmark dataset prepare --source snap --target-edges $${DATASET_TARGET_EDGES:-300000}

bench:
	benchmark bench run --platform all

report:
	benchmark report

test:
	pytest -q

clean:
	rm -rf data/raw/* data/processed/* results/*.json results/REPORT.md
