import unittest
import datetime
import iso8601
import recurly
recurly.API_KEY = 'blah'

import mocurly.core
import mocurly.backend

class TestTransaction(unittest.TestCase):
    def setUp(self):
        mocurly.core.register()
        mocurly.core.HTTPretty.enable()

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
        mocurly.backend.accounts_backend.add_object(self.base_account_data)
        mocurly.backend.billing_info_backend.add_object(self.base_billing_info_data)

        self.base_transaction_data = {
                'amount_in_cents': 100,
                'currency': 'USD'
            }

    def tearDown(self):
        mocurly.backend.clear_backends()

    def test_simple_transaction_creation(self):
        self.assertEqual(len(mocurly.backend.transactions_backend.datastore), 0)

        self.base_transaction_data['account'] = recurly.Account(account_code=self.base_account_data['uuid'])
        new_transaction = recurly.Transaction(**self.base_transaction_data)
        new_transaction.save()

        self.assertEqual(len(mocurly.backend.transactions_backend.datastore), 1)
        new_transaction = mocurly.backend.transactions_backend.get_object(new_transaction.uuid)
        for k, v in self.base_transaction_data.iteritems():
            if k == 'account':
                self.assertEqual(new_transaction[k], v.account_code)
            else:
                self.assertEqual(new_transaction[k], str(v))
        self.assertIn('created_at', new_transaction)
        self.assertTrue(new_transaction['test'])
        self.assertTrue(new_transaction['voidable'])
        self.assertTrue(new_transaction['refundable'])
        self.assertEqual(new_transaction['tax_in_cents'], 0)
        self.assertEqual(new_transaction['action'], 'purchase')
        self.assertEqual(new_transaction['status'], 'success')

    def test_transaction_refund(self):
        self.assertEqual(len(mocurly.backend.transactions_backend.datastore), 0)

        self.base_transaction_data['uuid'] = '1234'
        self.base_transaction_data['account'] = self.base_account_data['uuid']
        self.base_transaction_data['test'] = True
        self.base_transaction_data['voidable'] = True
        self.base_transaction_data['refundable'] = True
        self.base_transaction_data['tax_in_cents'] = 0
        self.base_transaction_data['action'] = 'purchase'
        self.base_transaction_data['status'] = 'success'
        self.base_transaction_data['created_at'] = '2014-08-11'
        mocurly.backend.transactions_backend.add_object(self.base_transaction_data)

        transaction = recurly.Transaction.get('1234')
        transaction.refund()

        self.assertEqual(len(mocurly.backend.transactions_backend.datastore), 1)
        voided_transaction = mocurly.backend.transactions_backend.get_object('1234')
        for k, v in self.base_transaction_data.iteritems():
            if k in ['voidable', 'refundable']:
                self.assertEqual(voided_transaction[k], False) # already refunded
            elif k == 'status':
                self.assertEqual(voided_transaction[k], 'void') # is now voided
            else:
                self.assertEqual(voided_transaction[k], v)
