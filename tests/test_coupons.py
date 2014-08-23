import unittest
import datetime
import iso8601
import recurly
recurly.API_KEY = 'blah'

import mocurly.core
import mocurly.backend

class TestCoupons(unittest.TestCase):
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

        self.base_coupon_data = {
                'coupon_code': 'special',
                'name': 'Special 10% off',
                'discount_type': 'percent',
                'discount_percent': 10
            }

    def tearDown(self):
        self.mocurly_.stop()

    def test_simple_coupon_creation(self):
        self.assertEqual(len(mocurly.backend.coupons_backend.datastore), 0)
        
        coupon = recurly.Coupon(**self.base_coupon_data)
        coupon.save()

        self.assertEqual(len(mocurly.backend.coupons_backend.datastore), 1)

    def test_coupon_redemption(self):
        self.assertEqual(len(mocurly.backend.coupon_redemptions_backend.datastore), 0)
        mocurly.backend.coupons_backend.add_object(self.base_coupon_data['coupon_code'], self.base_coupon_data)

        coupon = recurly.Coupon.get(self.base_coupon_data['coupon_code'])
        redemption = recurly.Redemption(account_code=self.base_account_data['account_code'], currency='USD')
        redemption = coupon.redeem(redemption)

        self.assertEqual(len(mocurly.backend.coupon_redemptions_backend.datastore), 1)

        redemption = recurly.Account.get(self.base_account_data['account_code']).redemption()
        self.assertEqual(redemption.coupon().coupon_code, self.base_coupon_data['coupon_code'])

        redemption.delete()
        self.assertEqual(len(mocurly.backend.coupon_redemptions_backend.datastore), 0)
