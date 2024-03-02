Porting www.gig-o-matic.com to Django

## Local development

This project is targeted at Python 3.8.  The development environment uses [Docker](https://www.docker.com/products/docker-desktop/) to make installing Postgres easier. Install Docker Desktop before continuing.

1. Create Python sandbox
	```
        cd GO3 # the place you checked out the source for Gig-O-Matic 3
	python3 -mvenv .venv
	source .venv/bin/activate
	```
 
1. Install required Python packages:
	```
	pip install -r requirements.txt
	```
 
1. Start the DB engine
	```
	docker compose up -d db
	sleep 30 # wait for DB to finish initializing
	```
 
1. Use the default environment
	```
	ln -s go3/.env.example go3/.env # Optional: copy instead and edit the file to taste
	```
 
1. Run the migrations
	```
	python manage.py migrate
	```
 
1. OPTIONAL: Fill database with sample data
	```
	python manage.py loaddata fixtures/testdata.json
	```
 
1. Create an administrative user
	```
	python manage.py createsuperuser
	```
 
1. Launch Gig-O!
	At this point, you should be able to run the project locally:
	```
	python manage.py runserver
	```
	You can log in with the user created above.

## Testing
We use sqlite3 for the test suite for now
```
python manage.py collectstatic
DATABASE_URL="sqlite:///gig-o-matic-test.sqlite" python manage.py test
```

## GraphQL API

To test the GraphQL endpoint, run the project locally and navigate to `http://127.0.0.1:8000/graphql` in your browser. 

Queries in the GUI are formatted as such:
```
query {
	allBands {
		band {
      		name,
		  	hometown,
		  	creation_date
		}
	}
}
```

## Formatting standards

We are converting the project to `autopep8`.

## Task queue

Django-Q is used as a task queue, and the default setting uses the standard database as a broker.  Tasks can be serialized into the database without any additional configuration.  However, a separate process is used to run these items in the queue.  This can be launched with
```
python manage.py qcluster
```
You can cause tests to run synchronously by setting `'sync': True` in the `Q_CLUSTER` settings.
