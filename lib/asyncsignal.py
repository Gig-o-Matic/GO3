from functools import wraps
from django.dispatch import receiver
from django_q.tasks import async_task

def async_receiver(*args, **kw):
    """Decorator to register a signal hander to run as an async_task.

    Accepts the same arguments at django.dispatch.receiver.  The decorated function
    will get all of the same arguments as it would running synchronously, except
    for the signal."""

    def decorator(func):
        @wraps(func)
        def decorated(*fargs, is_async=False, signal=None, **fkw):
            # signal cannot be pickled, so we don't pass it into the async task
            if is_async:
                return func(*fargs, **fkw)
            else:
                return async_task(decorated, *fargs, is_async=True, **fkw)
        return receiver(*args, **kw)(decorated)
    return decorator
