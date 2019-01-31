import unittest
import datetime
import operator
import pytz
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
                'zip': '94105',
                'country': 'USA'
            }
        self.base_billing_info_data = {
                'first_name': 'Foo',
                'last_name': 'Bar'
            }

    def tearDown(self):
        self.mocurly_.stop()

    def test_no_account_retrieve(self):
        self.assertRaises(recurly.NotFoundError, recurly.Account.get, '1234')

    def test_simple_account_creation(self):
        self.assertFalse(mocurly.backend.accounts_backend.has_object(self.base_account_data['account_code']))

        recurly.Account(**self.base_account_data).save()

        # Verify account object exists in backend
        self.assertTrue(mocurly.backend.accounts_backend.has_object(self.base_account_data['account_code']))
        new_account = mocurly.backend.accounts_backend.get_object(self.base_account_data['account_code'])
        for k, v in self.base_account_data.items():
            self.assertEqual(new_account[k], v)
        self.assertTrue('hosted_login_token' in new_account) # adds a hosted_login_token by default
        self.assertTrue('created_at' in new_account) # adds a created_at field by default

        # Verify account has no billing info
        recurly_account = recurly.Account.get(self.base_account_data['account_code'])
        self.assertRaises(AttributeError, lambda: recurly_account.billing_info)

    def test_account_creation_with_address(self):
        self.assertFalse(mocurly.backend.accounts_backend.has_object(self.base_account_data['account_code']))

        self.base_account_data['address'] = recurly.Address(**self.base_address_data)
        new_account = recurly.Account(**self.base_account_data)
        new_account.save()

        # Verify account object exists in backend
        self.assertTrue(mocurly.backend.accounts_backend.has_object(self.base_account_data['account_code']))
        new_account = mocurly.backend.accounts_backend.get_object(self.base_account_data['account_code'])
        for k, v in self.base_account_data.items():
            if k == 'address':
                address = new_account[k]
                for address_k, address_v in self.base_address_data.items():
                    self.assertEqual(address[address_k], address_v)
            else:
                self.assertEqual(new_account[k], v)
        self.assertTrue('hosted_login_token' in new_account) # adds a hosted_login_token by default
        self.assertTrue('created_at' in new_account) # adds a created_at field by default

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
        for k, v in self.base_account_data.items():
            self.assertEqual(new_account[k], v)
        self.assertTrue('hosted_login_token' in new_account) # adds a hosted_login_token by default
        self.assertTrue('created_at' in new_account) # adds a created_at field by default

        # Verify billing info object exists in backend
        self.assertTrue(mocurly.backend.billing_info_backend.has_object(self.base_account_data['account_code']))
        new_billing_info = mocurly.backend.billing_info_backend.get_object(self.base_account_data['account_code'])
        for k, v in self.base_billing_info_data.items():
            self.assertEqual(new_billing_info[k], v)

    def test_simple_get_account(self):
        self.base_account_data['hosted_login_token'] = 'abcd1234'
        self.base_account_data['created_at'] = '2014-08-11'
        mocurly.backend.accounts_backend.add_object(self.base_account_data['account_code'], self.base_account_data)

        account = recurly.Account.get(self.base_account_data['account_code'])
        for k, v in self.base_account_data.items():
            if k in ['uuid', 'uris']:
                continue # skip
            if k == 'created_at':
                self.assertEqual(getattr(account, k), datetime.datetime(2014, 8, 11, 0, 0, tzinfo=pytz.utc))
            else:
                self.assertEqual(getattr(account, k), v)

    def test_simple_account_update_billing_info(self):
        # Create a simple account
        recurly.Account(**self.base_account_data).save()

        # Verify account has no billing info
        recurly_account = recurly.Account.get(self.base_account_data['account_code'])
        self.assertRaises(AttributeError, lambda: recurly_account.billing_info)

        # Update the billing info using the update_billing_info method
        billing_info = recurly.BillingInfo(**self.base_billing_info_data)
        recurly_account.update_billing_info(billing_info)

        # Verify billing info object exists in backend
        self.assertTrue(mocurly.backend.billing_info_backend.has_object(self.base_account_data['account_code']))
        new_billing_info = mocurly.backend.billing_info_backend.get_object(self.base_account_data['account_code'])
        for k, v in self.base_billing_info_data.items():
            self.assertEqual(new_billing_info[k], v)

    def test_delete_billing_info(self):
        self.base_account_data['hosted_login_token'] = 'abcd1234'
        self.base_account_data['created_at'] = '2014-08-11'
        mocurly.backend.accounts_backend.add_object(self.base_account_data['account_code'], self.base_account_data)
        self.base_billing_info_data['account'] = self.base_account_data['account_code']
        mocurly.backend.billing_info_backend.add_object(self.base_account_data['account_code'], self.base_billing_info_data)

        self.assertEqual(len(mocurly.backend.accounts_backend.datastore), 1)
        self.assertEqual(len(mocurly.backend.billing_info_backend.datastore), 1)
        recurly.Account.get(self.base_account_data['account_code']).billing_info.delete()
        self.assertEqual(len(mocurly.backend.accounts_backend.datastore), 1)
        self.assertEqual(len(mocurly.backend.billing_info_backend.datastore), 0)

    def test_close(self):
        self.base_account_data['hosted_login_token'] = 'abcd1234'
        self.base_account_data['created_at'] = '2014-08-11'
        mocurly.backend.accounts_backend.add_object(self.base_account_data['account_code'], self.base_account_data)
        self.base_billing_info_data['account'] = self.base_account_data['account_code']
        mocurly.backend.billing_info_backend.add_object(self.base_account_data['account_code'], self.base_billing_info_data)

        account = recurly.Account.get(self.base_account_data['account_code'])
        account.delete()

        self.assertEqual(len(mocurly.backend.accounts_backend.datastore), 1) # only marks account as closed, but...
        self.assertEqual(len(mocurly.backend.billing_info_backend.datastore), 0) # billing info should be deleted
        account = mocurly.backend.accounts_backend.get_object(self.base_account_data['account_code'])
        self.assertEqual(account['state'], 'closed')


    def test_address_get_account(self):
        self.base_account_data['hosted_login_token'] = 'abcd1234'
        self.base_account_data['created_at'] = '2014-08-11'
        self.base_account_data['address'] = self.base_address_data
        mocurly.backend.accounts_backend.add_object(self.base_account_data['account_code'], self.base_account_data)

        account = recurly.Account.get(self.base_account_data['account_code'])
        for k, v in self.base_account_data.items():
            if k in ['uuid', 'uris']:
                continue # skip
            if k == 'created_at':
                self.assertEqual(getattr(account, k), datetime.datetime(2014, 8, 11, 0, 0, tzinfo=pytz.utc))
            elif k == 'address':
                address = getattr(account, k)
                self.assertEqual(type(address), recurly.Address)
                for address_k, address_v in v.items():
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
        for k, v in self.base_account_data.items():
            if k in ['uuid', 'uris']:
                continue # skip
            if k == 'created_at':
                self.assertEqual(getattr(account, k), datetime.datetime(2014, 8, 11, 0, 0, tzinfo=pytz.utc))
            else:
                self.assertEqual(getattr(account, k), v)

        billing_info = account.billing_info
        for k, v in self.base_billing_info_data.items():
            if k in ['uuid', 'uris', 'account']:
                continue # skip
            self.assertEqual(getattr(billing_info, k), v)

    def test_update_creditcard_billing_info(self):
        self.base_account_data['hosted_login_token'] = 'abcd1234'
        self.base_account_data['created_at'] = '2014-08-11'
        mocurly.backend.accounts_backend.add_object(self.base_account_data['account_code'], self.base_account_data)
        self.base_billing_info_data['account'] = self.base_account_data['account_code']
        mocurly.backend.billing_info_backend.add_object(self.base_account_data['account_code'], self.base_billing_info_data)

        account = recurly.Account.get(self.base_account_data['account_code'])
        billing_info = account.billing_info
        billing_info.first_name = 'Verena'
        billing_info.last_name = 'Example'
        billing_info.number = '4111-1111-1111-1111'
        billing_info.verification_value = '123'
        billing_info.month = 11
        billing_info.year = 2015
        billing_info.save()

        self.assertEqual(len(mocurly.backend.billing_info_backend.datastore), 1)
        billing_info_backed = mocurly.backend.billing_info_backend.get_object(self.base_account_data['account_code'])
        self.assertEqual(billing_info_backed['first_name'], 'Verena')
        self.assertEqual(billing_info_backed['last_name'], 'Example')
        self.assertEqual(billing_info_backed['number'], '4111-1111-1111-1111')
        self.assertEqual(billing_info_backed['first_six'], '411111')
        self.assertEqual(billing_info_backed['last_four'], '1111')
        self.assertEqual(billing_info_backed['verification_value'], '123')
        self.assertEqual(billing_info_backed['month'], '11')
        self.assertEqual(billing_info_backed['year'], '2015')

    def test_update_paypal_billing_info(self):
        self.base_account_data['hosted_login_token'] = 'abcd1234'
        self.base_account_data['created_at'] = '2014-08-11'
        mocurly.backend.accounts_backend.add_object(self.base_account_data['account_code'], self.base_account_data)
        self.base_billing_info_data['account'] = self.base_account_data['account_code']
        mocurly.backend.billing_info_backend.add_object(self.base_account_data['account_code'], self.base_billing_info_data)

        account = recurly.Account.get(self.base_account_data['account_code'])
        billing_info = account.billing_info
        billing_info.first_name = 'Verena'
        billing_info.last_name = 'Example'
        billing_info.paypal_billing_agreement_id = 'PP-7594'
        billing_info.save()

        self.assertEqual(len(mocurly.backend.billing_info_backend.datastore), 1)
        billing_info_backed = mocurly.backend.billing_info_backend.get_object(self.base_account_data['account_code'])
        self.assertEqual(billing_info_backed['first_name'], 'Verena')
        self.assertEqual(billing_info_backed['last_name'], 'Example')
        self.assertEqual(billing_info_backed['paypal_billing_agreement_id'], 'PP-7594')

    def test_update_account_with_billing_info(self):
        # Case 1: account exists, but has no billing data
        self.base_account_data['hosted_login_token'] = 'abcd1234'
        self.base_account_data['created_at'] = '2014-08-11'
        mocurly.backend.accounts_backend.add_object(self.base_account_data['account_code'], self.base_account_data)

        account = recurly.Account.get(self.base_account_data['account_code'])
        account.company_name = 'Mocurly'
        account.billing_info = billing_info = recurly.BillingInfo()
        billing_info.first_name = 'Verena'
        billing_info.last_name = 'Example'
        billing_info.number = '4111-1111-1111-1111'
        billing_info.verification_value = '123'
        billing_info.month = 11
        billing_info.year = 2015
        account.save()

        self.assertEqual(len(mocurly.backend.accounts_backend.datastore), 1)
        self.assertEqual(len(mocurly.backend.billing_info_backend.datastore), 1)
        account_backed = mocurly.backend.accounts_backend.get_object(self.base_account_data['account_code'])
        self.assertEqual(account_backed['company_name'], 'Mocurly')
        billing_info_backed = mocurly.backend.billing_info_backend.get_object(self.base_account_data['account_code'])
        self.assertEqual(billing_info_backed['first_name'], 'Verena')
        self.assertEqual(billing_info_backed['last_name'], 'Example')
        self.assertEqual(billing_info_backed['number'], '4111-1111-1111-1111')
        self.assertEqual(billing_info_backed['first_six'], '411111')
        self.assertEqual(billing_info_backed['last_four'], '1111')
        self.assertEqual(billing_info_backed['verification_value'], '123')
        self.assertEqual(billing_info_backed['month'], '11')
        self.assertEqual(billing_info_backed['year'], '2015')

        # Case 2: billing data exists
        account = recurly.Account.get(self.base_account_data['account_code'])
        account.email = 'verana@mocurly.com'
        account.billing_info = billing_info = recurly.BillingInfo()
        billing_info.last_name = 'Mocurly'
        account.save()

        self.assertEqual(len(mocurly.backend.accounts_backend.datastore), 1)
        self.assertEqual(len(mocurly.backend.billing_info_backend.datastore), 1)
        account_backed = mocurly.backend.accounts_backend.get_object(self.base_account_data['account_code'])
        self.assertEqual(account_backed['email'], 'verana@mocurly.com')
        billing_info_backed = mocurly.backend.billing_info_backend.get_object(self.base_account_data['account_code'])
        self.assertEqual(billing_info_backed['last_name'], 'Mocurly')

    def test_list_account(self):
        self.base_account_data['hosted_login_token'] = 'abcd1234'
        self.base_account_data['created_at'] = '2014-08-11'
        mocurly.backend.accounts_backend.add_object(self.base_account_data['account_code'], self.base_account_data)
        self.base_account_data['account_code'] = 'foo'
        mocurly.backend.accounts_backend.add_object(self.base_account_data['account_code'], self.base_account_data)
        self.base_account_data['account_code'] = 'bar'
        mocurly.backend.accounts_backend.add_object(self.base_account_data['account_code'], self.base_account_data)

        accounts = recurly.Account.all()

        self.assertEqual(len(accounts), 3)
        self.assertEqual(set([account.account_code for account in accounts]), set(['foo', 'bar', 'blah']))

    def test_invoice_list(self):
        mocurly.backend.accounts_backend.add_object(self.base_account_data['account_code'], self.base_account_data)
        base_invoice_data = {
                'account': self.base_account_data['account_code'],
                'uuid': 'foo',
                'state': 'collected',
                'invoice_number': '1234',
                'subtotal_in_cents': 1000,
                'currency': 'USD',
                'created_at': '2014-08-11',
                'net_terms': 0,
                'collection_method': 'automatic',

                'tax_type': 'usst',
                'tax_rate': 0,
                'tax_in_cents': 0,
                'total_in_cents': 1000,
            }
        mocurly.backend.invoices_backend.add_object('1234', base_invoice_data)
        base_invoice_data['invoice_number'] = '1235'
        mocurly.backend.invoices_backend.add_object('1235', base_invoice_data)

        account = recurly.Account.get(self.base_account_data['account_code'])
        invoices = account.invoices()
        self.assertEqual(len(invoices), 2)
        self.assertEqual(set(map(operator.attrgetter('invoice_number'), invoices)), set([1234, 1235]))
