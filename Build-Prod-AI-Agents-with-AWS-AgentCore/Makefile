.PHONY: prereq run test smoke clean verify

prereq:
	python main.py --prereq

run:
	python main.py --step all

test:
	pytest tests/test_step1_tools.py -v

smoke:
	pytest tests/smoke_test.py -v

clean:
	python main.py --cleanup

verify:
	bash scripts/verify_cleanup.sh
