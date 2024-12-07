.PHONY: all setup db migrate superuser runserver test qcluster schedule_tasks

all: setup db migrate superuser runserver

quickstart: activate db runserver

task: activate qcluster schedule_tasks

# Step 1: Create Python virtual environment and install dependencies
setup:
	python3 -m venv .venv
	. .venv/bin/activate && pip install -r requirements.txt
	ln -s go3/.env.example go3/.env

activate:
	. .venv/bin/activate

# Step 2: Start the database engine
db:
	docker compose up -d db
	sleep 30

# Step 3: Run database migrations
migrate:
	python manage.py migrate

# Step 4: Create a superuser
superuser:
	python manage.py createsuperuser

# Step 5: Run the Django server
runserver:
	python manage.py runserver

# Step 6: Run the test suite
test:
	python manage.py collectstatic
	DATABASE_URL="sqlite:///gig-o-matic-test.sqlite" python manage.py test

# Step 7: Run the task queue (separate window)
qcluster:
	python manage.py qcluster

# Step 8: Schedule tasks (optional)
schedule_tasks:
	python manage.py schedule_tasks
