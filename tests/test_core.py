import unittest
import ssl
import recurly
recurly.API_KEY = 'blah'

import mocurly
import mocurly.backend

class TestCore(unittest.TestCase):
    def setUp(self):
        self.base_account_data = {
                'account_code': 'blah',
                'email': 'foo@bar.com',
                'first_name': 'Foo',
                'last_name': 'Bar'
            }
        self.base_billing_info_data = {
                'uuid': 'blah',
                'first_name': 'Foo',
                'last_name': 'Bar'
            }

    def test_decorator(self):
        @mocurly.mocurly
        def foo():
            self.assertFalse(mocurly.backend.accounts_backend.has_object(self.base_account_data['account_code']))
            recurly.Account(**self.base_account_data).save()
            self.assertTrue(mocurly.backend.accounts_backend.has_object(self.base_account_data['account_code']))
        foo()

    def test_decorate_class_method(self):
        class Demo(object):
            @mocurly.mocurly
            def foo(this):
                self.assertFalse(mocurly.backend.accounts_backend.has_object(self.base_account_data['account_code']))
                recurly.Account(**self.base_account_data).save()
                self.assertTrue(mocurly.backend.accounts_backend.has_object(self.base_account_data['account_code']))
        Demo().foo()

    def test_context_manager(self):
        with mocurly.mocurly():
            self.assertFalse(mocurly.backend.accounts_backend.has_object(self.base_account_data['account_code']))
            recurly.Account(**self.base_account_data).save()
            self.assertTrue(mocurly.backend.accounts_backend.has_object(self.base_account_data['account_code']))

    def test_normal(self):
        mocurly_ = mocurly.mocurly()
        mocurly_.start()
        self.assertFalse(mocurly.backend.accounts_backend.has_object(self.base_account_data['account_code']))
        recurly.Account(**self.base_account_data).save()
        self.assertTrue(mocurly.backend.accounts_backend.has_object(self.base_account_data['account_code']))
        mocurly_.stop()

    def test_timeout(self):
        mocurly_ = mocurly.mocurly()
        mocurly_.start()

        mocurly_.start_timeout()

        self.assertFalse(mocurly.backend.accounts_backend.has_object(self.base_account_data['account_code']))
        self.assertRaises(ssl.SSLError, recurly.Account(**self.base_account_data).save)
        self.assertFalse(mocurly.backend.accounts_backend.has_object(self.base_account_data['account_code']))

        mocurly_.stop_timeout()

        self.assertFalse(mocurly.backend.accounts_backend.has_object(self.base_account_data['account_code']))
        recurly.Account(**self.base_account_data).save()
        self.assertTrue(mocurly.backend.accounts_backend.has_object(self.base_account_data['account_code']))

        mocurly_.stop()

    def test_timeout_successful_post(self):
        mocurly_ = mocurly.mocurly()
        mocurly_.start()

        mocurly_.start_timeout_successful_post()

        self.assertFalse(mocurly.backend.accounts_backend.has_object(self.base_account_data['account_code']))
        self.assertRaises(ssl.SSLError, recurly.Account(**self.base_account_data).save)
        self.assertTrue(mocurly.backend.accounts_backend.has_object(self.base_account_data['account_code']))

        mocurly_.stop_timeout_successful_post()

        self.base_account_data['account_code'] = 'foo'
        self.assertFalse(mocurly.backend.accounts_backend.has_object(self.base_account_data['account_code']))
        recurly.Account(**self.base_account_data).save()
        self.assertTrue(mocurly.backend.accounts_backend.has_object(self.base_account_data['account_code']))

        mocurly_.stop()

    def test_selective_timeout(self):
        mocurly_ = mocurly.mocurly()
        mocurly_.start()

        # Only timeout on get requests
        def timeout_filter(request):
            return request.method == 'GET'

        mocurly_.start_timeout(timeout_filter=timeout_filter)

        self.assertFalse(mocurly.backend.accounts_backend.has_object(self.base_account_data['account_code']))
        recurly.Account(**self.base_account_data).save()
        self.assertTrue(mocurly.backend.accounts_backend.has_object(self.base_account_data['account_code']))
        self.assertRaises(ssl.SSLError, recurly.Account.get, self.base_account_data['account_code'])

        mocurly_.stop_timeout()

        self.assertEqual(recurly.Account.get(self.base_account_data['account_code']).account_code, self.base_account_data['account_code'])

        mocurly_.stop()

    def test_timeout_successful_post(self):
        mocurly_ = mocurly.mocurly()
        mocurly_.start()

        # Only timeout on creating transactions
        def timeout_filter(request):
            return request.path.endswith('transactions')
        mocurly_.start_timeout_successful_post(timeout_filter=timeout_filter)

        self.assertFalse(mocurly.backend.accounts_backend.has_object(self.base_account_data['account_code']))
        new_account = recurly.Account(**self.base_account_data)
        new_account.billing_info = recurly.BillingInfo(**self.base_billing_info_data)
        new_account.save()
        self.assertTrue(mocurly.backend.accounts_backend.has_object(self.base_account_data['account_code']))

        self.assertEqual(len(mocurly.backend.transactions_backend.datastore), 0)
        new_transaction = recurly.Transaction(account=new_account, amount_in_cents=20, currency='USD')
        self.assertRaises(ssl.SSLError, new_transaction.save)
        self.assertEqual(len(mocurly.backend.transactions_backend.datastore), 1)

        mocurly_.stop_timeout_successful_post()

        recurly.Transaction(account=new_account, amount_in_cents=20, currency='USD').save()
        self.assertEqual(len(mocurly.backend.transactions_backend.datastore), 2)

        mocurly_.stop()

    def test_exceptions(self):
        """Tests that exception objects do the right thing."""
        error_object = mocurly.ResponseError(200, 'Body')
        self.assertEqual(error_object.status_code, 200)
        self.assertEqual(error_object.response_body, 'Body')
        self.assertEqual(str(error_object), '200')

    def test_url_encoding_handling(self):
        """Tests that mocurly correctly routes urlencoded pks"""
        self.base_account_data['account_code'] += '+foo'

        @mocurly.mocurly
        def foo():
            self.assertFalse(mocurly.backend.accounts_backend.has_object(self.base_account_data['account_code']))
            recurly.Account(**self.base_account_data).save()
            self.assertTrue(mocurly.backend.accounts_backend.has_object(self.base_account_data['account_code']))
            self.assertIsNotNone(recurly.Account.get(self.base_account_data['account_code']))
        foo()
