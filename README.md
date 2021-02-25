Porting www.gig-o-matic.com to Django

## Local development

This project is targeted at Python 3.8.  The required packages can be installed with
```
pip install -r requirements.txt
```
By default, a SQLite database will be used.  To change this, or other settings, create a file `go/settings_local.py`.  Any settings here will override the defaults.  Note that other databases may need additional packages; `requirements.mysql.txt` has the requirements for MySQL.

To create the database, run
```
python manage.py migrate
```
To seed the database with test data, run
```
python manage.py loaddata fixtures/testdata.json
```
Then, to create an administrative user, run
```
python manage.py createsuperuser
```
At this point, you should be able to run the project locally:
```
python manage.py runserver
```
You can log in with the user created above.

## Testing

```
python manage.py collectstatic
```
```
python manage.py test
```

## Task queue

Django-Q is used as a task queue, and the default setting uses the standard database as a broker.  Tasks can be serialized into the database without any additional configuration.  However, a separate process is used to run these items in the queue.  This can be launched with
```
python manage.py qcluster
```
You can cause tests to run synchronously by setting `'sync': True` in the `Q_CLUSTER` settings.
