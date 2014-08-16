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
        mocurly.backend.accounts_backend.add_object(self.base_account_data['uuid'], self.base_account_data)
        mocurly.backend.billing_info_backend.add_object(self.base_billing_info_data['uuid'], self.base_billing_info_data)

        self.base_transaction_data = {
                'amount_in_cents': 100,
                'currency': 'USD'
            }

    def tearDown(self):
        self.mocurly_.stop()

    def test_simple_transaction_creation(self):
        self.assertEqual(len(mocurly.backend.transactions_backend.datastore), 0)
        self.assertEqual(len(mocurly.backend.invoices_backend.datastore), 0)

        self.base_transaction_data['account'] = recurly.Account(account_code=self.base_account_data['uuid'])
        new_transaction = recurly.Transaction(**self.base_transaction_data)
        new_transaction.save()

        self.assertEqual(len(mocurly.backend.transactions_backend.datastore), 1)
        self.assertEqual(len(mocurly.backend.invoices_backend.datastore), 1)
        new_transaction_backed = mocurly.backend.transactions_backend.get_object(new_transaction.uuid)
        for k, v in self.base_transaction_data.items():
            if k == 'account':
                self.assertEqual(new_transaction_backed[k], v.account_code)
            else:
                self.assertEqual(new_transaction_backed[k], str(v))
        self.assertTrue('created_at' in new_transaction_backed)
        self.assertTrue(new_transaction_backed['test'])
        self.assertTrue(new_transaction_backed['voidable'])
        self.assertTrue(new_transaction_backed['refundable'])
        self.assertEqual(new_transaction_backed['tax_in_cents'], 0)
        self.assertEqual(new_transaction_backed['action'], 'purchase')
        self.assertEqual(new_transaction_backed['status'], 'success')

        new_invoice = new_transaction.invoice()
        new_invoice_backed = mocurly.backend.invoices_backend.get_object(str(new_invoice.invoice_number))
        self.assertEqual(len(new_invoice_backed['transactions']), 1)
        self.assertEqual(new_invoice_backed['transactions'][0], new_transaction.uuid)
        self.assertEqual(new_invoice_backed['state'], 'collected')
        self.assertEqual(new_invoice_backed['subtotal_in_cents'], self.base_transaction_data['amount_in_cents'])
        self.assertEqual(new_invoice_backed['total_in_cents'], self.base_transaction_data['amount_in_cents'])
        self.assertEqual(new_invoice_backed['currency'], self.base_transaction_data['currency'])
        self.assertEqual(new_invoice_backed['tax_in_cents'], 0)
        self.assertEqual(new_invoice_backed['tax_type'], 'usst')
        self.assertEqual(new_invoice_backed['tax_rate'], 0)
        self.assertEqual(new_invoice_backed['net_terms'], 0)

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
        mocurly.backend.transactions_backend.add_object('1234', self.base_transaction_data)

        transaction = recurly.Transaction.get('1234')
        transaction.refund()

        self.assertEqual(len(mocurly.backend.transactions_backend.datastore), 1)
        voided_transaction = mocurly.backend.transactions_backend.get_object('1234')
        for k, v in self.base_transaction_data.items():
            if k in ['voidable', 'refundable']:
                self.assertEqual(voided_transaction[k], False) # already refunded
            elif k == 'status':
                self.assertEqual(voided_transaction[k], 'void') # is now voided
            else:
                self.assertEqual(voided_transaction[k], v)
