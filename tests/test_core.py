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

    def test_decorator(self):
        @mocurly.mocurly
        def foo():
            self.assertFalse(mocurly.backend.accounts_backend.has_object(self.base_account_data['account_code']))
            recurly.Account(**self.base_account_data).save()
            self.assertTrue(mocurly.backend.accounts_backend.has_object(self.base_account_data['account_code']))
        foo()

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

        mocurly_.start_timeout_all_connections()

        self.assertFalse(mocurly.backend.accounts_backend.has_object(self.base_account_data['account_code']))
        self.assertRaises(ssl.SSLError, recurly.Account(**self.base_account_data).save)
        self.assertFalse(mocurly.backend.accounts_backend.has_object(self.base_account_data['account_code']))

        mocurly_.stop_timeout_all_connections()

        self.assertFalse(mocurly.backend.accounts_backend.has_object(self.base_account_data['account_code']))
        recurly.Account(**self.base_account_data).save()
        self.assertTrue(mocurly.backend.accounts_backend.has_object(self.base_account_data['account_code']))

        mocurly_.stop()

    def test_timeout_successful_post(self):
        mocurly_ = mocurly.mocurly()
        mocurly_.start()

        mocurly_.start_timeout_all_connections_successful_post()

        self.assertFalse(mocurly.backend.accounts_backend.has_object(self.base_account_data['account_code']))
        self.assertRaises(ssl.SSLError, recurly.Account(**self.base_account_data).save)
        self.assertTrue(mocurly.backend.accounts_backend.has_object(self.base_account_data['account_code']))

        mocurly_.stop_timeout_all_connections_successful_post()

        self.base_account_data['account_code'] = 'foo'
        self.assertFalse(mocurly.backend.accounts_backend.has_object(self.base_account_data['account_code']))
        recurly.Account(**self.base_account_data).save()
        self.assertTrue(mocurly.backend.accounts_backend.has_object(self.base_account_data['account_code']))

        mocurly_.stop()

