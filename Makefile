.PHONY: install list run test clean

install:
	python3 -m pip install -e .

list:
	python3 scripts/load-datahub.py --list

run:
	python3 scripts/load-datahub.py

test:
	PYTHONPATH=src python3 -m unittest discover -s tests -v

clean:
	rm -rf .cache .pytest_cache build dist src/*.egg-info
