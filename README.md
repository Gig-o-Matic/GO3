# gig-o-matic

## Local development

This project is targeted at Python 3.8.  The required packages can be installed with [poetry](python-poetry.org)

```shellsession
$ poetry install
Installing dependencies from lock file
```

By default, a SQLite database will be used.  To change this, or other settings, create a file `go/settings_local.py`.  Any settings here will override the defaults.  Note that other databases may need additional packages; `poetry install --with=mysql` has the requirements for MySQL.

To create the database, run

```shellsession
$ poetry run python manage.py migrate
Operations to perform:
  Apply all migrations: admin, auth, band, contenttypes, django_q, gig, member, motd, sessions, stats
Running migrations:
  Applying contenttypes.0001_initial... OK
  Applying contenttypes.0002_remove_content_type_name... OK
  Applying auth.0001_initial... OK
  Applying auth.0002_alter_permission_name_max_length... OK
  Applying auth.0003_alter_user_email_max_length... OK
  Applying auth.0004_alter_user_username_opts... OK
```

To seed the database with test data, run

```shellsession
$ poetry run python manage.py loaddata fixtures/testdata.json
Installed 1025 object(s) from 1 fixture(s)
```

Then, to create an administrative user, run

```shellsession
$ poetry run python manage.py createsuperuser
Email address: ...
Password:
Password (again):
Superuser created successfully.
```

At this point, you should be able to run the project locally:

```shellsession
$ poetry run python manage.py runserver
# ...
Performing system checks...

System check identified no issues (0 silenced).
February 25, 2024 - 12:52:11
Django version 3.2.6, using settings 'go3.settings'
Starting development server at http://127.0.0.1:8000/
Quit the server with CONTROL-C.
```

You can log in with the user created above.

## Testing

```shellsession
poetry run python manage.py collectstatic
```

```shellsession
poetry run python manage.py test
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
