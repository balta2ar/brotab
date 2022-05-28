unit-test:
	pytest -v

smoke-build:
	rm -rf ./dist && \
	python setup.py sdist bdist_wheel && \
	docker build -t brotab-smoke -f smoke.Dockerfile .

smoke-test:
	docker run -it brotab-smoke

integration-build:
	docker build -t brotab-integration -f jess.Dockerfile .

integration-run-container:
	docker run -v "$(pwd):/brotab" -p 19222:9222 -p 14625:4625 -it --rm --cpuset-cpus 0 --memory 512mb -v /tmp/.X11-unix:/tmp/.X11-unix -e DISPLAY=unix$DISPLAY -v /dev/shm:/dev/shm brotab-integration

integration-test: export INTEGRATION_TEST = 1

integration-test:
	xhost +local:docker
	pytest -v -k test_integration -s

test-all: unit-test smoke-build smoke-test integration-build integration-test
	@echo Testing all

all:
	echo ALL

reset:
	pkill python3; pkill xvfb-run; pkill node; pkill Xvfb; pkill firefox

switch_to_dev:
	echo "Switching to DEV"

switch_to_prod:
	echo "Switching to PROD"

.PHONY: reset switch_to_dev switch_to_prod
