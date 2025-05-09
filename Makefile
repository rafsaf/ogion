# to run tests with arm64 see https://docs.docker.com/build/building/multi-platform/
export OGION_ARCH ?= amd64

ifdef CI
BUILD := 
else
BUILD := "--build"
endif

.PHONY: docker_setup_up
docker_setup_up:
	docker compose -f docker/docker-compose.yml pull
	docker compose -f docker/docker-compose.yml up -d gcs minio azurite
	docker compose -f docker/docker-compose.dbs.yml up -d

.PHONY: docker_setup_down
docker_setup_down:
	docker compose -f docker/docker-compose.yml down
	docker compose -f docker/docker-compose.dbs.yml down

.PHONY: unit_tests
unit_tests:
	$(MAKE) docker_setup_up
	docker compose -f docker/docker-compose.yml run --rm $(BUILD) ogion_unit_tests

.PHONY: acceptance_tests
acceptance_tests:
	$(MAKE) docker_setup_up
	docker compose -f docker/docker-compose.yml run --rm --build ogion_acceptance_tests

.PHONY: update_compose_db_file
update_compose_db_file:
	poetry run python ogion/tools/compose_file_generator.py > docker/docker-compose.dbs.yml

.PHONY: benchmark-mem-massif-main
benchmark-mem-massif-main:
	valgrind --massif-out-file=massif.benchmark-main.out --tool=massif python -m ogion.main -s
	massif-visualizer massif.benchmark-main.out

.PHONY: benchmark-time-encrypt-2gb
benchmark-time-encrypt-2gb:
	$(MAKE) benchmark_files/test_file_2gb
	time -f "User: %U seconds, System: %S seconds, Real: %e seconds" python -c "import pathlib;import ogion.core;ogion.core.run_create_age_archive(pathlib.Path('./benchmark_files/test.tar2'))"

benchmark_files/test_file_2gb:
	mkdir -p benchmark_files
	dd if=/dev/urandom of=benchmark_files/test_file_2gb bs=2G count=1 iflag=fullblock
