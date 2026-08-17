.PHONY: dev install test lint reset logs trace

install:
	pip3 install -r requirements.txt

dev:
	streamlit run src/app.py

test:
	python3 -m pytest tests/ -q

lint:
	python3 -m pyflakes src

reset:
	rm -f data/checkpoints.sqlite data/traces.jsonl
	rm -rf data/uploads

logs:
	tail -f data/traces.jsonl

trace:
	@echo "Traces are stored locally at data/traces.jsonl (JSONL, GenAI-ish span fields)."
	@echo "Open the '📊 Trace' expander under any assistant message in the app for a per-turn view."
