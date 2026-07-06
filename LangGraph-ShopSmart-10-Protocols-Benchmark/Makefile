.PHONY: setup smoke test run mcp app metrics diagram clean cleanup protocols-up protocols-down benchmark brokers-up brokers-down responders-up responders-down

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
	streamlit run apps/streamlit_app.py

metrics:
	python -m shopsmart.metrics

diagram:
	python -c "from shopsmart.graph import build_system; build_system()" 2>/dev/null | grep -E "\[Diagram\]|System ready"

protocols-up:
	@mkdir -p .run
	@echo "Starting REST (8001), GraphQL (8002), gRPC (8003), Webhook (8004), WebSocket (8005), SOAP (8006) protocol servers..."
	@python -m shopsmart.protocols.rest_server > .run/rest.log 2>&1 & echo $$! > .run/rest.pid
	@python -m shopsmart.protocols.graphql_server > .run/graphql.log 2>&1 & echo $$! > .run/graphql.pid
	@python -m shopsmart.protocols.grpc_pricing_server > .run/grpc.log 2>&1 & echo $$! > .run/grpc.pid
	@python -m shopsmart.protocols.webhook_server > .run/webhook.log 2>&1 & echo $$! > .run/webhook.pid
	@python -m shopsmart.protocols.websocket_server > .run/websocket.log 2>&1 & echo $$! > .run/websocket.pid
	@python -m shopsmart.protocols.soap_server > .run/soap.log 2>&1 & echo $$! > .run/soap.pid
	@sleep 2
	@echo "Protocol servers started. PIDs in .run/*.pid, logs in .run/*.log"

responders-up:
	@mkdir -p .run
	@echo "Starting MQTT and AMQP responders (requires make brokers-up first)..."
	@python -m shopsmart.protocols.mqtt_responder > .run/mqtt_responder.log 2>&1 & echo $$! > .run/mqtt_responder.pid
	@python -m shopsmart.protocols.amqp_responder > .run/amqp_responder.log 2>&1 & echo $$! > .run/amqp_responder.pid
	@sleep 2
	@echo "Responders started."

responders-down:
	@for f in .run/mqtt_responder.pid .run/amqp_responder.pid; do \
		if [ -f $$f ]; then kill $$(cat $$f) 2>/dev/null || true; rm -f $$f; fi; \
	done
	@echo "Responders stopped."

protocols-down:
	@for f in .run/rest.pid .run/graphql.pid .run/grpc.pid .run/webhook.pid .run/websocket.pid .run/soap.pid; do \
		if [ -f $$f ]; then kill $$(cat $$f) 2>/dev/null || true; rm -f $$f; fi; \
	done
	@echo "Protocol servers stopped."

brokers-up:
	docker compose up -d mosquitto rabbitmq
	@echo "Waiting for brokers to become healthy..."
	@sleep 5
	@echo "Mosquitto (1883) and RabbitMQ (5672, mgmt 15672) started."

brokers-down:
	docker compose down

benchmark:
	python apps/benchmark_runner.py

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .pytest_cache
	rm -rf src/shopsmart_support.egg-info
	rm -rf output/
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
