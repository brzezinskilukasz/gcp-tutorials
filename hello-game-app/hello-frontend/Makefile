install-dev:
	pip install -r requirements-dev.txt

install:
	pip install -r requirements.txt

run:
	gunicorn -b 0.0.0.0:8080 --worker-class gthread --threads 4 --timeout 60 --log-level info --access-logfile - --error-logfile - src.main:app

lint:
	python3 -m pylint src/**/*.py