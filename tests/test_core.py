import unittest
import recurly
recurly.API_KEY = 'blah'

import mocurly.core
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
        @mocurly.core.mocurly
        def foo():
            self.assertFalse(mocurly.backend.accounts_backend.has_object(self.base_account_data['account_code']))
            recurly.Account(**self.base_account_data).save()
            self.assertTrue(mocurly.backend.accounts_backend.has_object(self.base_account_data['account_code']))
        foo()

    def test_context_manager(self):
        with mocurly.core.mocurly():
            self.assertFalse(mocurly.backend.accounts_backend.has_object(self.base_account_data['account_code']))
            recurly.Account(**self.base_account_data).save()
            self.assertTrue(mocurly.backend.accounts_backend.has_object(self.base_account_data['account_code']))

    def test_normal(self):
        mocurly_ = mocurly.core.mocurly()
        mocurly_.start()
        self.assertFalse(mocurly.backend.accounts_backend.has_object(self.base_account_data['account_code']))
        recurly.Account(**self.base_account_data).save()
        self.assertTrue(mocurly.backend.accounts_backend.has_object(self.base_account_data['account_code']))
        mocurly_.stop()

