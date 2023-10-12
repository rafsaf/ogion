# to run tests with arm64 see https://docs.docker.com/build/building/multi-platform/
docker_dbs_setup:
	docker compose -f docker/docker-compose.dbs.yml up -d 

tests_amd64:
	docker compose -f docker/docker-compose.tests.yml run --rm backuper_tests_amd64

tests_arm64:
	docker compose -f docker/docker-compose.tests.yml run --rm backuper_tests_arm64

acceptance_tests_amd64:
	docker compose -f docker/docker-compose.tests.yml run --rm backuper_acceptance_test_amd64

acceptance_tests_arm64:
	docker compose -f docker/docker-compose.tests.yml run --rm backuper_acceptance_test_arm64