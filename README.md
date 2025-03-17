Gig-o-Matic
-----------

Tools to help a Honk band manage itself!

Features:
* Multiple band support - each member is associated with one or more bands
* Multiple instrument support - each member can play more than one instrument
* Calendar view & integration with popular calendar services
* Email updates

## Local development

This project is targeted at Python 3.12, and the minimum supported version is Python 3.10.  The development environment uses [Docker](https://www.docker.com/products/docker-desktop/) to make installing Postgres easier. Install Docker Desktop before continuing.

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

 1. Use the default environment
	```
	ln -s go3/.env.example go3/.env # Optional: copy instead and edit the file to taste
	```
 
1. Start the DB engine
	```
	docker compose up -d db
	sleep 30 # wait for DB to finish initializing
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


1. OPTIONAL: Start the task queue
	Certain actions kick off activities that run in the background, using DjangoQ to manage the queue.
	This runs concurrently, so kick it off in a separate shell. You should see the tasks come and go
	in the DjangoQ section of the admin pages.
	```
	python manage.py qcluster
	```

1. OPTIONAL: set up the scheduled tasks
	Some tasks - like updating calendar feeds, archiving gigs, send snooze reminders - require repeating
	events to be scheduled in DjangoQ. This should only be done once - check the DjangoQ "scheduled tasks"
	page to see the events that have been set up.
	```
	python manage.py schedule_tasks
	```

## Development

The live site uses various third party services to function correctly. In local development, these are all bypassed, though they can be enabled as needed by putting appropriate configuration into `go3/.env`.
* [SendGrid](https://www.sendgrid.com) - Used to send the various emails to users: signup confirmation, password resets, gig reminders, etc.
* [reCAPTCHA](https://www.google.com/recaptcha/about) - Reduce spammers hitting the signup and password reset URLs
* [Rollbar](https://rollbar.com) - Used to capture errors that happen in production for us to investigate

When testing emails in the local development environment, we usually do not want to actually send the email. Instead, they are written out as separate files in the `tmp/` directory within the GO3 root directory.

## Test Suite
We use sqlite3 for the test suite for now
```
python manage.py collectstatic
DATABASE_URL="sqlite:///gig-o-matic-test.sqlite" python manage.py test
```

## REST API
Run the project locally and open [http://127.0.0.1:8000/api/docs](http://127.0.0.1:8000/api/docs) to view the API documentation. 

Log in and navigate to the [member profile](http://127.0.0.1:8000/member/) page to generate a token.

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
