test:
	pytest -vv
coverage:
	coverage run -m pytest -vv \
	&& coverage report --fail-under 100 --show-missing