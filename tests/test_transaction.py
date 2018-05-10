import unittest
import recurly
recurly.API_KEY = 'blah'

import mocurly.core
import mocurly.backend
import mocurly.errors

FULL = 0
PARTIAL = 1

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
                'currency': 'USD',
                'description': 'foo'
            }

        self.base_invoice_data = {
                'account': self.base_account_data['uuid'],
                'uuid': 'foo',
                'state': 'collected',
                'invoice_number': '1234',
                'subtotal_in_cents': self.base_transaction_data['amount_in_cents'],
                'currency': self.base_transaction_data['currency'],
                'created_at': '2014-08-11',
                'net_terms': 0,
                'collection_method': 'automatic',

                'tax_type': 'usst',
                'tax_rate': 0,
                'tax_in_cents': 0,
                'total_in_cents': self.base_transaction_data['amount_in_cents'],
                'transactions': ['1234'],
                'line_items': ['abcd1234']
            }

        self.base_line_item = {
                'uuid': 'abcd1234',
                'type': 'charge',
                'created_at': '2014-08-11',
                'account_code': self.base_account_data['uuid'],
                'currency': self.base_transaction_data['currency'],
                'unit_amount_in_cents': self.base_transaction_data['amount_in_cents'],
                'tax_in_cents': 0,
                'discount_in_cents': 0,
                'total_in_cents': self.base_transaction_data['amount_in_cents'],
                'description': 'Foozle is the Barzam',
                'quantity': 1,
                'invoice': self.base_invoice_data['invoice_number']
            }


    def tearDown(self):
        self.mocurly_.stop()

    def test_transaction_failure(self):
        self.assertEqual(len(mocurly.backend.transactions_backend.datastore), 0)
        self.assertEqual(len(mocurly.backend.invoices_backend.datastore), 0)

        self.mocurly_.register_transaction_failure(self.base_account_data['uuid'], mocurly.errors.TRANSACTION_DECLINED)
        self.base_transaction_data['account'] = recurly.Account(account_code=self.base_account_data['uuid'])
        new_transaction = recurly.Transaction(**self.base_transaction_data)
        try:
            new_transaction.save()
            self.fail('No exception raised')
        except recurly.ValidationError as exc:
            self.assertEqual(exc.error, mocurly.errors.TRANSACTION_ERRORS[mocurly.errors.TRANSACTION_DECLINED]['customer'])

        self.assertEqual(len(mocurly.backend.transactions_backend.datastore), 1)
        self.assertEqual(len(mocurly.backend.invoices_backend.datastore), 0)

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

        line_items = new_invoice.line_items
        self.assertEqual(len(line_items), 1)
        new_line_item_backed = mocurly.backend.adjustments_backend.get_object(line_items[0].uuid)
        self.assertEqual(new_line_item_backed['description'], self.base_transaction_data['description'])
        self.assertEqual(new_line_item_backed['unit_amount_in_cents'], self.base_transaction_data['amount_in_cents'])
        self.assertEqual(new_line_item_backed['total_in_cents'], self.base_transaction_data['amount_in_cents'])
        self.assertEqual(new_line_item_backed['currency'], self.base_transaction_data['currency'])
        self.assertEqual(new_line_item_backed['type'], 'charge')
        self.assertEqual(new_line_item_backed['tax_in_cents'], 0)

    def test_transaction_refund_deprecation(self):
        """Tests that the old transaction refund interface no longer exists in mocurly."""
        self.assertEqual(len(mocurly.backend.transactions_backend.datastore), 0)

        transaction_id = self._directly_create_transaction_without_invoice()
        transaction = recurly.Transaction.get(transaction_id)
        with self.assertRaises(recurly.NotFoundError):
            transaction.refund()

    def test_transaction_refund_via_invoice(self):
        """
        Tests that using the invoice refund system to refund an unvoidable
        transaction behaves in the way expected.
        """
        self.assertEqual(len(mocurly.backend.transactions_backend.datastore), 0)

        original_transaction_id, original_invoice_number, original_line_item_id = self._directly_create_transaction_with_invoice()
        # Make transaction unvoidable and apply refund
        mocurly.backend.transactions_backend.update_object(original_transaction_id, {'voidable': False})
        new_invoice = self._refund_transaction_by_line_items(original_transaction_id)

        # Verify behavior of invoice line item refund
        # - Creates a new invoice with adjustments that cancel out original invoice
        # - Creates a new transaction object to be REFUND
        original_invoice, refund_invoice, _, _ = self._assert_invoices_are_paired(original_invoice_number)

        # Verify that the two invoices have different transactions
        self.assertNotEqual(refund_invoice['transactions'][0], original_invoice['transactions'][0])

        self.assertEqual(len(mocurly.backend.transactions_backend.datastore), 2)
        for transaction_uuid, transaction in mocurly.backend.transactions_backend.datastore.items():
            if transaction_uuid == original_transaction_id:
                original_transaction = transaction
            else:
                refund_transaction = transaction
        self.assertEqual(original_transaction['action'], 'purchase')
        self.assertEqual(original_transaction['status'], 'success')
        self.assertEqual(original_transaction['voidable'], False)
        self.assertEqual(original_transaction['refundable'], False)
        self.assertEqual(refund_transaction['action'], 'refund')
        self.assertEqual(refund_transaction['status'], 'success')
        self.assertEqual(refund_transaction['voidable'], True)
        self.assertEqual(refund_transaction['refundable'], False)

        self.assertEqual(new_invoice.original_invoice().invoice_number, 1234)


    def test_transaction_void_via_invoice(self):
        """Uses the invoice refund system to void a transaction."""
        self.assertEqual(len(mocurly.backend.transactions_backend.datastore), 0)

        original_transaction_id, original_invoice_number, original_line_item_id = self._directly_create_transaction_with_invoice()
        new_invoice = self._refund_transaction_by_line_items(original_transaction_id)

        # Verify behavior of invoice line item refund
        # - Creates a new invoice with adjustments that cancel out original invoice
        # - Updates associated transaction object to be VOID
        original_invoice, refund_invoice, _, _ = self._assert_invoices_are_paired(original_invoice_number)
        # Verify that the two invoices have the same transactions
        self.assertEqual(refund_invoice['transactions'][0], original_invoice['transactions'][0])

        self.assertEqual(len(mocurly.backend.transactions_backend.datastore), 1)
        transaction = recurly.Transaction.get(original_transaction_id)
        self.assertEqual(transaction.status, 'void')
        self.assertEqual(transaction.voidable, False)
        self.assertEqual(transaction.refundable, False)

        self.assertEqual(new_invoice.original_invoice().invoice_number, 1234)

    def test_transaction_refund_amount_via_invoice(self):
        """
        Tests that using the invoice refund system will void a transaction if
        voidable.
        """
        self.assertEqual(len(mocurly.backend.transactions_backend.datastore), 0)

        original_transaction_id, original_invoice_number, original_line_item_id = self._directly_create_transaction_with_invoice()

        transaction = recurly.Transaction.get(original_transaction_id)
        invoice = transaction.invoice()
        invoice.refund_amount(1)

        # Verify behavior of invoice refund amount
        # - Creates a new transaction to track the refund
        # - Creates a new invoice with adjustments that track the refunded amount
        original_invoice, refund_invoice, _, _ = self._assert_invoices_are_paired(original_invoice_number, type=PARTIAL, partial_amount=1)
        # Verify that the two invoices have different transactions
        self.assertNotEqual(refund_invoice['transactions'][0], original_invoice['transactions'][0])

        self.assertEqual(len(mocurly.backend.transactions_backend.datastore), 2)
        for transaction_uuid, transaction in mocurly.backend.transactions_backend.datastore.items():
            if transaction_uuid == original_transaction_id:
                original_transaction = transaction
            else:
                refund_transaction = transaction
        self.assertEqual(original_transaction['action'], 'purchase')
        self.assertEqual(original_transaction['refundable'], True)
        self.assertEqual(original_transaction['voidable'], True)
        self.assertEqual(original_transaction['amount_in_cents'], self.base_transaction_data['amount_in_cents'])
        self.assertEqual(refund_transaction['action'], 'refund')
        self.assertEqual(refund_transaction['refundable'], False)
        self.assertEqual(refund_transaction['voidable'], True)
        self.assertEqual(refund_transaction['amount_in_cents'], -1)


    def test_transaction_list(self):
        self._directly_create_transaction_without_invoice()
        self._directly_create_transaction_without_invoice(transaction_id='abcd')

        acc = recurly.Account.get(self.base_account_data['uuid'])
        transactions = list(acc.transactions())
        self.assertEqual(len(transactions), 2)
        self.assertEqual(set([transaction.uuid for transaction in transactions]), set(['1234', 'abcd']))


    def _directly_create_transaction_without_invoice(self, transaction_id='1234'):
        """
        This method will directly injects a transaction object, as if it was
        created by recurly.
        """
        self.base_transaction_data['uuid'] = transaction_id
        self.base_transaction_data['account'] = self.base_account_data['uuid']
        self.base_transaction_data['test'] = True
        self.base_transaction_data['voidable'] = True
        self.base_transaction_data['refundable'] = True
        self.base_transaction_data['tax_in_cents'] = 0
        self.base_transaction_data['action'] = 'purchase'
        self.base_transaction_data['status'] = 'success'
        self.base_transaction_data['created_at'] = '2014-08-11'
        mocurly.backend.transactions_backend.add_object(transaction_id, self.base_transaction_data)
        return transaction_id
 
    def _directly_create_transaction_with_invoice(self):
        """
        This method will directly inject a transaction object and the related
        invoice objects, as well as line items, as if it was created by recurly.
        """
        transaction_id = self._directly_create_transaction_without_invoice()
        invoice_number = self.base_invoice_data['invoice_number']
        line_item_id = 'abcd1234'
        mocurly.backend.transactions_backend.update_object(transaction_id, {'invoice': self.base_invoice_data['invoice_number']})
        mocurly.backend.invoices_backend.add_object(self.base_invoice_data['invoice_number'], self.base_invoice_data)
        mocurly.backend.adjustments_backend.add_object(line_item_id, self.base_line_item)
        return transaction_id, invoice_number, line_item_id
 
    def _refund_transaction_by_line_items(self, transaction_id):
        """
        Given a transaction id, this method will refund all the line items on
        the associated invoice.
        """
        transaction = recurly.Transaction.get(transaction_id)
        invoice = transaction.invoice()
        line_items = invoice.line_items
        adjustments_to_refund = []
        for line_item in line_items:
            adjustments_to_refund.append({
                'adjustment': line_item,
                'quantity': line_item.quantity,
                'prorate': False 
            })
        return invoice.refund(adjustments_to_refund)
 
    def _assert_invoices_are_paired(self, original_invoice_number, type=FULL, partial_amount=None):
        """
        Given an ID that identifies the original invoice, this method asserts
        that there is only a pair of invoices, where they relate to each other
        in a refund manner.
 
        type is full or partial. If partial, must also provided the partial amount.
        """
        self.assertEqual(len(mocurly.backend.invoices_backend.datastore), 2)
        for invoice_number, invoice in mocurly.backend.invoices_backend.datastore.items():
            self.assertEqual(len(invoice['transactions']), 1)
            if invoice_number == original_invoice_number:
                original_invoice = invoice
            else:
                refund_invoice = invoice

        self.assertEqual(len(mocurly.backend.adjustments_backend.datastore), 2)
        for adjustment_uuid, adjustment in mocurly.backend.adjustments_backend.datastore.items():
            if adjustment['invoice'] == original_invoice_number:
                original_adjustment = adjustment
            else:
                refund_adjustment = adjustment
        self.assertEqual(int(original_adjustment['quantity']), -int(refund_adjustment['quantity']))

        if type == FULL:
            self.assertEqual(original_invoice['total_in_cents'], -refund_invoice['total_in_cents'])
            self.assertEqual(original_adjustment['total_in_cents'], -refund_adjustment['total_in_cents'])
        else:
            self.assertEqual(refund_invoice['total_in_cents'], -partial_amount)
            self.assertEqual(refund_adjustment['total_in_cents'], -partial_amount)
        return original_invoice, refund_invoice, original_adjustment, refund_adjustment
