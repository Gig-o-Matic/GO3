from rollbar.contrib.django.middleware import RollbarNotifierMiddleware

class GigORollbarNotifierMiddleware(RollbarNotifierMiddleware):
    def get_payload_data(self, request, exc):
        payload_data = dict()

        if not request.user.is_anonymous:
            # Adding info about the user affected by this event (optional)
            # The 'id' field is required, anything else is optional
            payload_data = {
                'person': {
                    'id': request.user.id,
                    'username': request.user.username,
                    'email': request.user.email,
                },
            }

        return payload_data
