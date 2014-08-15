import string
import datetime
import random
from .core import BaseRecurlyEndpoint, details_route, serialize, BASE_URI
from .backend import accounts_backend, billing_info_backend, transactions_backend

class AccountsEndpoint(BaseRecurlyEndpoint):
    base_uri = '/accounts'
    pk_attr = 'account_code'
    backend = accounts_backend
    object_type = 'account'
    template = 'account.xml'

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
        create_info['hosted_login_token'] = self.generate_id()
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
        return serialize('billing_info.xml', 'billing_info', obj)

    @details_route('GET', 'billing_info')
    def get_billing_info(self, pk):
        return self.serialize_billing_info(billing_info_backend.get_object(pk))

    @details_route('PUT', 'billing_info')
    def update_billing_info(self, pk, update_info):
        return self.serialize_billing_info(billing_info_backend.update_object(pk, update_info))

    @details_route('DELETE', 'billing_info')
    def delete_billing_info(self, pk):
        billing_info_backend.delete_object(pk)

class TransactionsEndpoint(BaseRecurlyEndpoint):
    base_uri = '/transactions'
    backend = transactions_backend
    object_type = 'transaction'
    template = 'transaction.xml'

    def uris(self, obj):
        uri_out = super(TransactionsEndpoint, self).uris(obj)
        obj['account']['uris'] = AccountsEndpoint().uris(obj['account'])
        uri_out['account_uri'] = obj['account']['uris']['object_uri']
        uri_out['invoice_uri'] = 'TODO'
        uri_out['subscription_uri'] = 'TODO'
        return uri_out

    def serialize(self, obj):
        if isinstance(obj['account'], basestring):
            # hydrate account
            obj['account'] = accounts_backend.get_object(obj['account'])
        return super(TransactionsEndpoint, self).serialize(obj)

    def create(self, create_info):
        account_code = create_info['account'][AccountsEndpoint.pk_attr]
        assert accounts_backend.has_object(account_code)
        create_info['account'] = account_code

        create_info['tax_in_cents'] = 0
        create_info['action'] = 'purchase'
        create_info['status'] = 'success'
        create_info['test'] = True
        create_info['voidable'] = True
        create_info['refundable'] = True
        create_info['created_at'] = datetime.datetime.now().isoformat()
        return super(TransactionsEndpoint, self).create(create_info)

    def delete(self, pk, amount_in_cents=None):
        ''' DELETE is a refund action '''
        transaction = TransactionsEndpoint.backend.get_object(pk)
        if transaction['voidable'] and amount_in_cents is None:
            transaction['status'] = 'void'
            transaction['voidable'] = False
            transaction['refundable'] = False
            TransactionsEndpoint.backend.update_object(pk, transaction)
        elif transaction['refundable']:
            refund_transaction = transaction.copy()
            refund_transaction['uuid'] = self.generate_id()
            refund_transaction['type'] = 'refund'
            refund_transaction['voidable'] = False
            refund_transaction['refundable'] = False
            if amount_in_cents is not None:
                refund_transaction['amount_in_cents'] = amount_in_cents
            TransactionsEndpoint.backend.add_object(refund_transaction)
        else:
            # TODO: raise exception - transaction cannot be refunded
            pass

