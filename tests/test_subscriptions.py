import unittest
import datetime
import iso8601
import recurly
recurly.API_KEY = 'blah'

import mocurly.core
import mocurly.backend

class TestTransaction(unittest.TestCase):
    def setUp(self):
        self.mocurly_ = mocurly.core.mocurly()
        self.mocurly_.start()

        self.base_address_data = {
                'address1': '123 Jackson St.',
                'address2': 'Data City',
                'state': 'CA',
                'zip': '94105'
            }
        self.base_billing_info_data = {
                'uuid': 'blah',
                'first_name': 'Foo',
                'last_name': 'Bar'
            }
        self.base_account_data = {
                'uuid': 'blah',
                'account_code': 'blah',
                'email': 'foo@bar.com',
                'first_name': 'Foo',
                'last_name': 'Bar',
                'address': self.base_address_data,
                'hosted_login_token': 'abcd1234',
                'created_at': '2014-08-11'
            }

        self.base_plan_data = {
                'plan_code': 'gold',
                'name': 'Gold Plan',
                'unit_amount_in_cents': recurly.Money(USD=1000, EUR=800)
            }

    def tearDown(self):
        self.mocurly_.stop()

    def test_simple_plan_creation(self):
        self.assertEqual(len(mocurly.backend.plans_backend.datastore), 0)

        new_plan = recurly.Plan(**self.base_plan_data)
        new_plan.save()

        self.assertEqual(len(mocurly.backend.plans_backend.datastore), 1)
        new_plan_backed = mocurly.backend.plans_backend.get_object(new_plan.plan_code)
        for k, v in self.base_plan_data.items():
            if k == 'unit_amount_in_cents':
                self.assertEqual(new_plan_backed[k], {curr:str(amt) for curr, amt in  v.currencies.items()})
            else:
                self.assertEqual(new_plan_backed[k], v)

