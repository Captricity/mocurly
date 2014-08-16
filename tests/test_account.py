import unittest
import datetime
import iso8601
import recurly
recurly.API_KEY = 'blah'

import mocurly.core
import mocurly.backend

class TestAccount(unittest.TestCase):
    def setUp(self):
        self.mocurly_ = mocurly.core.mocurly()
        self.mocurly_.start()

        self.base_account_data = {
                'account_code': 'blah',
                'email': 'foo@bar.com',
                'first_name': 'Foo',
                'last_name': 'Bar'
            }
        self.base_address_data = {
                'address1': '123 Jackson St.',
                'address2': 'Data City',
                'state': 'CA',
                'zip': '94105'
            }
        self.base_billing_info_data = {
                'first_name': 'Foo',
                'last_name': 'Bar'
            }

    def tearDown(self):
        self.mocurly_.stop()

    def test_simple_account_creation(self):
        self.assertFalse(mocurly.backend.accounts_backend.has_object(self.base_account_data['account_code']))

        new_account = recurly.Account(**self.base_account_data)
        new_account.save()

        # Verify account object exists in backend
        self.assertTrue(mocurly.backend.accounts_backend.has_object(self.base_account_data['account_code']))
        new_account = mocurly.backend.accounts_backend.get_object(self.base_account_data['account_code'])
        for k, v in self.base_account_data.iteritems():
            self.assertEqual(new_account[k], v)
        self.assertIn('hosted_login_token', new_account) # adds a hosted_login_token by default
        self.assertIn('created_at', new_account) # adds a created_at field by default

    def test_account_creation_with_address(self):
        self.assertFalse(mocurly.backend.accounts_backend.has_object(self.base_account_data['account_code']))

        self.base_account_data['address'] = recurly.Address(**self.base_address_data)
        new_account = recurly.Account(**self.base_account_data)
        new_account.save()

        # Verify account object exists in backend
        self.assertTrue(mocurly.backend.accounts_backend.has_object(self.base_account_data['account_code']))
        new_account = mocurly.backend.accounts_backend.get_object(self.base_account_data['account_code'])
        for k, v in self.base_account_data.iteritems():
            if k == 'address':
                address = new_account[k]
                for address_k, address_v in self.base_address_data.iteritems():
                    self.assertEqual(address[address_k], address_v)
            else:
                self.assertEqual(new_account[k], v)
        self.assertIn('hosted_login_token', new_account) # adds a hosted_login_token by default
        self.assertIn('created_at', new_account) # adds a created_at field by default

    def test_account_creation_with_billing_info(self):
        self.assertFalse(mocurly.backend.accounts_backend.has_object(self.base_account_data['account_code']))
        self.assertFalse(mocurly.backend.billing_info_backend.has_object(self.base_account_data['account_code']))

        self.base_account_data['billing_info'] = recurly.BillingInfo(**self.base_billing_info_data)
        new_account = recurly.Account(**self.base_account_data)
        new_account.save()
        del self.base_account_data['billing_info']

        # Verify account object exists in backend
        self.assertTrue(mocurly.backend.accounts_backend.has_object(self.base_account_data['account_code']))
        new_account = mocurly.backend.accounts_backend.get_object(self.base_account_data['account_code'])
        for k, v in self.base_account_data.iteritems():
            self.assertEqual(new_account[k], v)
        self.assertIn('hosted_login_token', new_account) # adds a hosted_login_token by default
        self.assertIn('created_at', new_account) # adds a created_at field by default

        # Verify billing info object exists in backend
        self.assertTrue(mocurly.backend.billing_info_backend.has_object(self.base_account_data['account_code']))
        new_billing_info = mocurly.backend.billing_info_backend.get_object(self.base_account_data['account_code'])
        for k, v in self.base_billing_info_data.iteritems():
            self.assertEqual(new_billing_info[k], v)

    def test_simple_get_account(self):
        self.base_account_data['hosted_login_token'] = 'abcd1234'
        self.base_account_data['created_at'] = '2014-08-11'
        mocurly.backend.accounts_backend.add_object(self.base_account_data['account_code'], self.base_account_data)

        account = recurly.Account.get(self.base_account_data['account_code'])
        for k, v in self.base_account_data.iteritems():
            if k in ['uuid', 'uris']:
                continue # skip
            if k == 'created_at':
                self.assertEqual(getattr(account, k), datetime.datetime(2014, 8, 11, 0, 0, tzinfo=iso8601.iso8601.Utc()))
            else:
                self.assertEqual(getattr(account, k), v)

    def test_address_get_account(self):
        self.base_account_data['hosted_login_token'] = 'abcd1234'
        self.base_account_data['created_at'] = '2014-08-11'
        self.base_account_data['address'] = self.base_address_data
        mocurly.backend.accounts_backend.add_object(self.base_account_data['account_code'], self.base_account_data)

        account = recurly.Account.get(self.base_account_data['account_code'])
        for k, v in self.base_account_data.iteritems():
            if k in ['uuid', 'uris']:
                continue # skip
            if k == 'created_at':
                self.assertEqual(getattr(account, k), datetime.datetime(2014, 8, 11, 0, 0, tzinfo=iso8601.iso8601.Utc()))
            elif k == 'address':
                address = getattr(account, k)
                self.assertEqual(type(address), recurly.Address)
                for address_k, address_v in v.iteritems():
                    self.assertEqual(getattr(address, address_k), address_v)
            else:
                self.assertEqual(getattr(account, k), v)

    def test_billing_info_get_account(self):
        self.base_account_data['hosted_login_token'] = 'abcd1234'
        self.base_account_data['created_at'] = '2014-08-11'
        mocurly.backend.accounts_backend.add_object(self.base_account_data['account_code'], self.base_account_data)
        self.base_billing_info_data['account'] = self.base_account_data['account_code']
        mocurly.backend.billing_info_backend.add_object(self.base_account_data['account_code'], self.base_billing_info_data)

        account = recurly.Account.get(self.base_account_data['account_code'])
        for k, v in self.base_account_data.iteritems():
            if k in ['uuid', 'uris']:
                continue # skip
            if k == 'created_at':
                self.assertEqual(getattr(account, k), datetime.datetime(2014, 8, 11, 0, 0, tzinfo=iso8601.iso8601.Utc()))
            else:
                self.assertEqual(getattr(account, k), v)

        billing_info = account.billing_info
        for k, v in self.base_billing_info_data.iteritems():
            if k in ['uuid', 'uris', 'account']:
                continue # skip
            self.assertEqual(getattr(billing_info, k), v)
