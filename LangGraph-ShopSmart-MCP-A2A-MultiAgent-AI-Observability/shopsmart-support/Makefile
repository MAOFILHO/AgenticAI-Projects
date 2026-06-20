.PHONY: setup smoke test run mcp app metrics diagram clean cleanup

setup:
	@bash scripts/setup.sh

smoke:
	@bash scripts/smoke_test.sh

test:
	python -m pytest tests/ -v --tb=short

test-offline:
	python -m pytest tests/test_smoke.py tests/test_pii.py tests/test_tools.py -v

run:
	python -m shopsmart.graph

mcp:
	python -m shopsmart.mcp_server

app:
	streamlit run streamlit_app.py

metrics:
	python -m shopsmart.metrics

diagram:
	python -c "from shopsmart.graph import build_system; build_system()" 2>/dev/null | grep -E "\[Diagram\]|System ready"

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .pytest_cache
	rm -rf src/shopsmart_support.egg-info
	rm -f observability_report.png routing_distribution.png tool_usage.png
	@echo "Caches and build artifacts removed."

cleanup: clean
	rm -rf .venv
	@echo "Virtual environment removed."
	@echo ""
	@echo "To reinstall from scratch:"
	@echo "  make setup"
	@echo "  # edit .env with your API keys"
	@echo "  make smoke"
	@echo "  make test"
