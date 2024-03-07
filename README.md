# gig-o-matic

[![Testing](https://github.com/Gig-o-Matic/GO3/actions/workflows/testing.yml/badge.svg)](https://github.com/Gig-o-Matic/GO3/actions/workflows/testing.yml)

## Local development

This project is targeted at Python 3.8.  The development environment uses [Docker](https://www.docker.com/products/docker-desktop/) to make installing Postgres easier. Install Docker Desktop before continuing.

1. Install required Python packages and activate the local virtualenv:

  ```shellsession
  $ poetry install 
  Installing dependencies from lock file
  $ poetry shell
  Spawning shell within /Users/gigdude/src/Gig-o-Matic/GO3/.venv
  (go3-py3.10) $
  ```

 1. Use the default environment

 ```shellsession
 ln -s go3/.env.example go3/.env # Optional: copy instead and edit the file to taste
 ```

1. Start the DB engine

 ```shellsession
 docker compose up -d db
 sleep 30 # wait for DB to finish initializing
 ```

1. Run the migrations

 ```shellsession
 python manage.py migrate
 ```

1. OPTIONAL: Fill database with sample data

 ```shellsession
 python manage.py loaddata fixtures/testdata.json
 ```

1. Create an administrative user

 ```shellsession
 python manage.py createsuperuser
 ```

1. Launch Gig-O!
 At this point, you should be able to run the project locally:

 ```shellsession
 python manage.py runserver
 ```

 You can log in with the user created above.

1. OPTIONAL: Start the task queue
 Certain actions kick off activities that run in the background, using DjangoQ to manage the queue.
 This runs concurrently, so kick it off in a separate shell. You should see the tasks come and go
 in the DjangoQ section of the admin pages.

 ```shellsession
 python manage.py qcluster
 ```

1. OPTIONAL: set up the scheduled tasks
 Some tasks - like updating calendar feeds, archiving gigs, send snooze reminders - require repeating
 events to be scheduled in DjangoQ. This should only be done once - check the DjangoQ "scheduled tasks"
 page to see the events that have been set up.

 ```shellsession
 python manage.py schedule_tasks
 ```

## Testing

```shellsession
python manage.py collectstatic
DATABASE_URL="sqlite:///gig-o-matic-test.sqlite" poetry run python manage.py test
```

## GraphQL API

To test the GraphQL endpoint, run the project locally and navigate to `http://127.0.0.1:8000/graphql` in your browser.

Queries in the GUI are formatted as such:

```shellsession
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

```shellsession
poetry run python manage.py qcluster
```

You can cause tests to run synchronously by setting `'sync': True` in the `Q_CLUSTER` settings.
