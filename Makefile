# to run tests with arm64 see https://docs.docker.com/build/building/multi-platform/
export OGION_ARCH ?= amd64

ogion/bin/7zip/amd64/7zzs:
	rm -rf ogion/bin/7zip/amd64
	mkdir -p ogion/bin/7zip/amd64
	cd ogion/bin/7zip/amd64 && \
	wget --quiet "https://www.7-zip.org/a/7z2301-linux-x64.tar.xz" && \
	tar -xf "7z2301-linux-x64.tar.xz" && \
	rm -f "7z2301-linux-x64.tar.xz" && \
	rm -rf MANUAL

ogion/bin/7zip/arm64/7zzs:
	rm -rf ogion/bin/7zip/arm64
	mkdir -p ogion/bin/7zip/arm64
	cd ogion/bin/7zip/arm64 && \
	wget --quiet "https://www.7-zip.org/a/7z2301-linux-arm64.tar.xz" && \
	tar -xf "7z2301-linux-arm64.tar.xz" && \
	rm -f "7z2301-linux-arm64.tar.xz" && \
	rm -rf MANUAL

.PHONY: docker_dbs_setup_up
docker_dbs_setup_up:
	docker compose -f docker/docker-compose.dbs.yml up -d 

.PHONY: docker_dbs_setup_down
docker_dbs_setup_down:
	docker compose -f docker/docker-compose.dbs.yml down

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