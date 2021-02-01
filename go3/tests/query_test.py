from django.test import TestCase
from graphene.test import Client
from go3.schema import schema
from gig.tests import GigTestBase


class GraphQLTest(GigTestBase):

    # test band model
    # query the graphql endpoint and should expect to get back certain attributes

    # def __init__(self, schema):
    #     self.client = Client(schema)

    def test_allBands(self):
        client = Client(schema)

        print('testing allBands')

        executed = client.execute('''{ allBands {
            name
            } }''')

        print(executed)
        assert executed == {
            'data': {
                'allBands': [{'name': 'test band'}]
            }
        }
    # test member model

    # test assoc model
