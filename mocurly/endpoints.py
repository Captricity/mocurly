import string
import datetime
import random
from .core import BaseRecurlyEndpoint, details_route, serialize, BASE_URI
from .backend import accounts_backend, billing_info_backend

class AccountsEndpoint(BaseRecurlyEndpoint):
    base_uri = '/accounts'
    pk_attr = 'account_code'
    backend = accounts_backend
    object_type = 'account'
    template = 'templates/account.xml'

    def uris(self, obj):
        uri_out = super(AccountsEndpoint, self).uris(obj)
        uri_out['adjustments_uri'] = uri_out['object_uri'] + '/adjustments'
        uri_out['billing_info_uri'] = uri_out['object_uri'] + '/billing_info'
        uri_out['invoices_uri'] = uri_out['object_uri'] + '/invoices'
        uri_out['redemption_uri'] = uri_out['object_uri'] + '/redemption'
        uri_out['subscriptions_uri'] = uri_out['object_uri'] + '/subscriptions'
        uri_out['transactions_uri'] = uri_out['object_uri'] + '/transactions'
        return uri_out

    def create(self, create_info):
        if 'billing_info' in create_info:
            billing_info = create_info['billing_info']
            billing_info['uuid'] = create_info[AccountsEndpoint.pk_attr]
            billing_info_backend.add_object(billing_info)
            del create_info['billing_info']
        create_info['hosted_login_token'] = AccountsEndpoint.generate_login_token()
        create_info['created_at'] = datetime.datetime.now().isoformat()
        return super(AccountsEndpoint, self).create(create_info)

    def update(self, pk, update_info):
        if 'billing_info' in update_info:
            updated_billing_info = update_info['billing_info']
            if billing_info_backend.has_object(pk):
                billing_info_backend.update_object(pk, updated_billing_info)
            else:
                updated_billing_info['uuid'] = update_info[AccountsEndpoint.pk_attr]
                billing_info_backend.add_object(updated_billing_info)
            del update_info['billing_info']
        return super(AccountsEndpoint, self).update(pk, update_info)

    def billing_info_uris(self, obj):
        uri_out = {}
        uri_out['account_uri'] = BASE_URI + AccountsEndpoint.base_uri + '/' + obj['uuid']
        uri_out['object_uri'] = uri_out['account_uri'] + '/billing_info'
        return uri_out

    def serialize_billing_info(self, obj):
        obj['uris'] = self.billing_info_uris(obj)
        return serialize('templates/billing_info.xml', 'billing_info', obj)

    @details_route('GET', 'billing_info')
    def get_billing_info(self, pk):
        return self.serialize_billing_info(billing_info_backend.get_object(pk))

    @details_route('PUT', 'billing_info')
    def update_billing_info(self, pk, update_info):
        return self.serialize_billing_info(billing_info_backend.update_object(pk, update_info))

    @details_route('DELETE', 'billing_info')
    def delete_billing_info(self, pk):
        billing_info_backend.delete_object(pk)

    @staticmethod
    def generate_login_token():
        return ''.join(random.choice(string.ascii_lowercase + string.digits) for i in xrange(32))
