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
        mocurly.backend.accounts_backend.add_object(self.base_account_data['uuid'], self.base_account_data)
        mocurly.backend.billing_info_backend.add_object(self.base_billing_info_data['uuid'], self.base_billing_info_data)

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

    def test_simple_plan_add_on_creation(self):
        # add a sample plan to the plans backend
        mocurly.backend.plans_backend.add_object(self.base_backed_plan_data['plan_code'], self.base_backed_plan_data)

        self.assertEqual(len(mocurly.backend.plan_add_ons_backend.datastore), 0)

        # now create some addons
        plan = recurly.Plan.get(self.base_backed_plan_data['plan_code'])
        for add_on in self.base_add_on_data:
            add_on['name'] = add_on['add_on_code'].upper()
            add_on['unit_amount_in_cents'] = recurly.Money(**add_on['unit_amount_in_cents'])
            plan.create_add_on(recurly.AddOn(**add_on))

        self.assertEqual(len(mocurly.backend.plan_add_ons_backend.datastore), 2)
        foo_add_on_backed = mocurly.backend.plan_add_ons_backend.get_object(self.base_backed_plan_data['plan_code'] + '__foo')
        foo_add_on = filter(lambda add_on: add_on['add_on_code'] == 'foo', self.base_add_on_data)[0]
        for k, v in foo_add_on.items():
            if k == 'unit_amount_in_cents':
                self.assertEqual(foo_add_on_backed[k], dict((curr, str(amt)) for curr, amt in v.currencies.items()))
            else:
                self.assertEqual(foo_add_on_backed[k], v)

        bar_add_on_backed = mocurly.backend.plan_add_ons_backend.get_object(self.base_backed_plan_data['plan_code'] + '__bar')
        bar_add_on = filter(lambda add_on: add_on['add_on_code'] == 'bar', self.base_add_on_data)[0]
        for k, v in bar_add_on.items():
            if k == 'unit_amount_in_cents':
                self.assertEqual(bar_add_on_backed[k], dict((curr, str(amt)) for curr, amt in v.currencies.items()))
            else:
                self.assertEqual(bar_add_on_backed[k], v)

        # make sure foreign keys are linked properly
        self.assertEqual(len(plan.add_ons()), 2)

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
        transactions = invoice.transactions
        self.assertEqual(len(transactions), 1)
        self.assertEqual(transactions[0].subscription().uuid, new_subscription.uuid)

        # Make sure we can reference the subscription from the account
        account = new_subscription.account()
        account_subscriptions = account.subscriptions()
        self.assertEqual(len(account_subscriptions), 1)
        self.assertEqual(account_subscriptions[0].uuid, new_subscription.uuid)

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

    def test_subscription_filtering(self):
        # add a sample plan to the plans backend
        mocurly.backend.plans_backend.add_object(self.base_backed_plan_data['plan_code'], self.base_backed_plan_data)
        # add multiple subscriptions in different states
        self.base_subscription_data['uuid'] = 'foo'
        self.base_subscription_data['account'] = self.base_account_data['account_code']
        self.base_subscription_data['state'] = 'active'
        mocurly.backend.subscriptions_backend.add_object('foo', self.base_subscription_data)
        self.base_subscription_data['uuid'] = 'bar'
        self.base_subscription_data['state'] = 'future'
        mocurly.backend.subscriptions_backend.add_object('bar', self.base_subscription_data)
        for i in range(5):
            self.base_subscription_data['uuid'] = str(i)
            self.base_subscription_data['state'] = 'expired'
            mocurly.backend.subscriptions_backend.add_object(str(i), self.base_subscription_data)

        account = recurly.Account.get(self.base_account_data['account_code'])
        active_subscriptions = account.subscriptions(state='active')
        self.assertEqual(len(active_subscriptions), 1)
        self.assertEqual(active_subscriptions[0].uuid, 'foo')

        future_subscriptions = account.subscriptions(state='future')
        self.assertEqual(len(future_subscriptions), 1)
        self.assertEqual(future_subscriptions[0].uuid, 'bar')

        live_subscriptions = account.subscriptions(state='live')
        self.assertEqual(len(live_subscriptions), 2)
        self.assertEqual(set(['foo', 'bar']), set([sub.uuid for sub in live_subscriptions]))

        expired_subscriptions = account.subscriptions(state='expired')
        self.assertEqual(len(expired_subscriptions), 5)
        self.assertEqual(set(range(5)), set([int(sub.uuid) for sub in expired_subscriptions]))

    def test_subscription_termination_full_refund(self):
        # add a sample plan to the plans backend
        mocurly.backend.plans_backend.add_object(self.base_backed_plan_data['plan_code'], self.base_backed_plan_data)
        # add an active subscription
        new_subscription = recurly.Subscription(**self.base_subscription_data)
        new_subscription.save()
        self.assertEqual(new_subscription.state, 'active')

        # Now terminate it with a full refund
        new_subscription.terminate(refund='full')
        
        self.assertEqual(new_subscription.state, 'expired')
        invoice = new_subscription.invoice()
        transactions = invoice.transactions
        self.assertEqual(len(transactions), 1)
        self.assertEqual(transactions[0].status, 'void')

    def test_subscription_cancel(self):
        # add a sample plan to the plans backend
        mocurly.backend.plans_backend.add_object(self.base_backed_plan_data['plan_code'], self.base_backed_plan_data)
        # add an active subscription
        new_subscription = recurly.Subscription(**self.base_subscription_data)
        new_subscription.save()
        self.assertEqual(new_subscription.state, 'active')

        # now cancel it and verify it was canceled
        new_subscription.cancel()
        self.assertEqual(new_subscription.state, 'canceled')
