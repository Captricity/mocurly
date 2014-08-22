import unittest
import datetime
import iso8601
import recurly
recurly.API_KEY = 'blah'

import mocurly.core
import mocurly.endpoints
import mocurly.backend

class TestSubscriptions(unittest.TestCase):
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
        self.base_backed_plan_data = self.base_plan_data.copy()
        self.base_backed_plan_data['uuid'] = self.base_plan_data['plan_code']
        self.base_backed_plan_data['unit_amount_in_cents'] = {u'USD': u'1000', u'EUR': u'800'}
        self.base_backed_plan_data['display_quantity'] = False
        self.base_backed_plan_data['trial_interval_length'] = 0
        self.base_backed_plan_data['plan_interval_unit'] = 'months'
        self.base_backed_plan_data['created_at'] = '2014-08-20'
        self.base_backed_plan_data['tax_exempt'] = False
        self.base_backed_plan_data['trial_interval_unit'] = 'months'
        self.base_backed_plan_data['plan_interval_length'] = 1

        self.base_subscription_data = {
                'plan_code': 'gold',
                'account': recurly.Account(account_code=self.base_account_data['account_code']),
                'currency': 'USD'
            }

        self.base_add_on_backed_data = [
                {
                    'add_on_code': 'foo',
                    'name': 'Foo',
                    'plan': self.base_backed_plan_data['plan_code'],
                    'accounting_code': 'foo',
                    'unit_amount_in_cents': {'USD': 1000},
                    'created_at': '2014-08-20',
                },
                {
                    'add_on_code': 'bar',
                    'name': 'Bar',
                    'plan': self.base_backed_plan_data['plan_code'],
                    'accounting_code': 'bar',
                    'unit_amount_in_cents': {'USD': 80},
                    'created_at': '2014-08-20',
                }
            ]
        self.base_add_on_data = [
                {
                    'add_on_code': 'foo',
                    'unit_amount_in_cents': {'USD': 1000}
                },
                {
                    'add_on_code': 'bar',
                    'unit_amount_in_cents': {'USD': 80}
                }
            ]

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
                self.assertEqual(new_plan_backed[k], dict((curr, str(amt)) for curr, amt in v.currencies.items()))
            else:
                self.assertEqual(new_plan_backed[k], v)

    def test_simple_subscription_creation(self):
        # add a sample plan to the plans backend
        mocurly.backend.plans_backend.add_object(self.base_backed_plan_data['plan_code'], self.base_backed_plan_data)

        self.assertEqual(len(mocurly.backend.subscriptions_backend.datastore), 0)

        new_subscription = recurly.Subscription(**self.base_subscription_data)
        new_subscription.save()

        self.assertEqual(len(mocurly.backend.subscriptions_backend.datastore), 1)

        # Make sure a new transaction and invoice was created with it
        invoice = new_subscription.invoice()
        self.assertTrue(invoice is not None)
        transactions = invoice.transactions
        self.assertEqual(len(transactions), 1)
        self.assertEqual(transactions[0].subscription().uuid, new_subscription.uuid)

    def test_subscriptions_with_addons(self):
        # add a sample plan to the plans backend
        mocurly.backend.plans_backend.add_object(self.base_backed_plan_data['plan_code'], self.base_backed_plan_data)
        # add some add ons to the backend
        for add_on in self.base_add_on_backed_data:
            uuid = mocurly.endpoints.PlansEndpoint().generate_plan_add_on_uuid(self.base_backed_plan_data['plan_code'], add_on['add_on_code'])
            mocurly.backend.plan_add_ons_backend.add_object(uuid, add_on)

        self.assertEqual(len(mocurly.backend.subscriptions_backend.datastore), 0)

        self.base_subscription_data['subscription_add_ons'] = [recurly.SubscriptionAddOn(add_on_code=addon['add_on_code'], quantity=1) for addon in self.base_add_on_data]
        new_subscription = recurly.Subscription(**self.base_subscription_data)
        new_subscription.save()

        self.assertEqual(len(mocurly.backend.subscriptions_backend.datastore), 1)
