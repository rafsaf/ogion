# to run tests with arm64 see https://docs.docker.com/build/building/multi-platform/
export OGION_ARCH ?= amd64

.PHONY: docker_dbs_setup_up
docker_dbs_setup_up:
	docker compose -f docker/docker-compose.dbs.yml up -d --remove-orphans

.PHONY: docker_dbs_setup_down
docker_dbs_setup_down:
	docker compose -f docker/docker-compose.dbs.yml down --remove-orphans

.PHONY: unit_tests
unit_tests:
	$(MAKE) docker_dbs_setup_up
	docker compose -f docker/docker-compose.yml run --rm --build ogion_unit_tests 

.PHONY: acceptance_tests
acceptance_tests:
	$(MAKE) docker_dbs_setup_up
	docker compose -f docker/docker-compose.yml run --rm --build ogion_acceptance_tests

.PHONY: update_compose_db_file
update_compose_db_file:
	poetry run python ogion/tools/compose_file_generator.py > docker/docker-compose.dbs.yml