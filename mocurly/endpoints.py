import datetime
import recurly
import six
import random
import string
import dateutil.relativedelta
import dateutil.parser

from .core import details_route, serialize
from .backend import accounts_backend, billing_info_backend, transactions_backend, invoices_backend, subscriptions_backend, plans_backend, subscription_addons_backend

class BaseRecurlyEndpoint(object):
    pk_attr = 'uuid'

    def hydrate_foreign_keys(self, obj):
        return obj

    def get_object_uri(self, obj):
        cls = self.__class__
        return recurly.base_uri() + cls.base_uri + '/' + obj[cls.pk_attr]

    def uris(self, obj):
        obj = self.hydrate_foreign_keys(obj)
        uri_out = {}
        uri_out['object_uri'] = self.get_object_uri(obj)
        return uri_out

    def serialize(self, obj):
        cls = self.__class__
        obj['uris'] = self.uris(obj)
        return serialize(cls.template, cls.object_type, obj)

    def list(self):
        raise NotImplementedError

    def create(self, create_info):
        cls = self.__class__
        if cls.pk_attr in create_info:
            create_info['uuid'] = create_info[cls.pk_attr]
        else:
            create_info['uuid'] = self.generate_id()
        new_obj = cls.backend.add_object(create_info['uuid'], create_info)
        return self.serialize(new_obj)

    def retrieve(self, pk):
        cls = self.__class__
        return self.serialize(cls.backend.get_object(pk))

    def update(self, pk, update_info):
        cls = self.__class__
        return self.serialize(cls.backend.update_object(pk, update_info))

    def delete(self, pk):
        cls = self.__class__
        cls.backend.delete_object(pk)

    def generate_id(self):
        return ''.join(random.choice(string.ascii_lowercase + string.digits) for i in range(32))

class AccountsEndpoint(BaseRecurlyEndpoint):
    base_uri = 'accounts'
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
            billing_info['account'] = create_info['account_code']
            billing_info_backend.add_object(create_info[AccountsEndpoint.pk_attr], billing_info)
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
                updated_billing_info['account'] = pk
                billing_info_backend.add_object(pk, updated_billing_info)
            del update_info['billing_info']
        return super(AccountsEndpoint, self).update(pk, update_info)

    def billing_info_uris(self, obj):
        uri_out = {}
        uri_out['account_uri'] = recurly.base_uri() + AccountsEndpoint.base_uri + '/' + obj['account']
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
    base_uri = 'transactions'
    backend = transactions_backend
    object_type = 'transaction'
    template = 'transaction.xml'

    def hydrate_foreign_keys(self, obj):
        if isinstance(obj['account'], six.string_types):
            # hydrate account
            obj['account'] = AccountsEndpoint.backend.get_object(obj['account'])
        if 'invoice' in obj and isinstance(obj['invoice'], six.string_types):
            # hydrate invoice
            obj['invoice'] = InvoicesEndpoint.backend.get_object(obj['invoice'])
        return obj

    def uris(self, obj):
        uri_out = super(TransactionsEndpoint, self).uris(obj)
        obj['account']['uris'] = AccountsEndpoint().uris(obj['account'])
        uri_out['account_uri'] = obj['account']['uris']['object_uri']
        if 'invoice' in obj:
            # To avoid infinite recursion
            uri_out['invoice_uri'] = InvoicesEndpoint().get_object_uri(obj['invoice'])
        uri_out['subscription_uri'] = 'TODO'
        return uri_out

    def create(self, create_info):
        account_code = create_info['account'][AccountsEndpoint.pk_attr]
        assert AccountsEndpoint.backend.has_object(account_code)
        create_info['account'] = account_code

        create_info['uuid'] = self.generate_id() # generate id now for invoice
        create_info['tax_in_cents'] = 0 #unsupported
        create_info['action'] = 'purchase'
        create_info['status'] = 'success'
        create_info['test'] = True
        create_info['voidable'] = True
        create_info['refundable'] = True
        create_info['created_at'] = datetime.datetime.now().isoformat()

        # Every new transaction creates a new invoice
        new_invoice = {
                'account': account_code,
                'uuid': self.generate_id(),
                'state': 'collected',
                'invoice_number': InvoicesEndpoint.generate_invoice_number(),
                'subtotal_in_cents': int(create_info['amount_in_cents']),
                'currency': create_info['currency'],
                'created_at': create_info['created_at'],
                'net_terms': 0,
                'collection_method': 'automatic',

                # unsupported
                'tax_type': 'usst',
                'tax_rate': 0
            }
        new_invoice['tax_in_cents'] = new_invoice['subtotal_in_cents'] * new_invoice['tax_rate']
        new_invoice['total_in_cents'] = new_invoice['subtotal_in_cents'] + new_invoice['tax_in_cents']
        new_invoice['transactions'] = [create_info['uuid']]
        InvoicesEndpoint.backend.add_object(new_invoice['invoice_number'], new_invoice)

        create_info['invoice'] = new_invoice[InvoicesEndpoint.pk_attr]
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
            TransactionsEndpoint.backend.add_object(refund_transaction['uuid'], refund_transaction)

            invoice = InvoicesEndpoint.backend.get_object(transaction['invoice'])
            InvoicesEndpoint.backend.update_object(transaction['invoice'], {'transactions': invoice['transactions'].append(refund_transaction['uuid'])})
        else:
            # TODO: raise exception - transaction cannot be refunded
            pass

class InvoicesEndpoint(BaseRecurlyEndpoint):
    base_uri = 'invoices'
    backend = invoices_backend
    object_type = 'invoice'
    pk_attr = 'invoice_number'
    template = 'invoice.xml'

    def hydrate_foreign_keys(self, obj):
        if isinstance(obj['account'], six.string_types):
            # hydrate account
            obj['account'] = AccountsEndpoint.backend.get_object(obj['account'])
        if 'transactions' in obj:
            obj['transactions'] = [TransactionsEndpoint.backend.get_object(transaction_id) if isinstance(transaction_id, six.string_types) else transaction_id for transaction_id in obj['transactions']]
            for transaction in obj['transactions']:
                transaction['invoice'] = obj
                transaction['uris'] = TransactionsEndpoint().uris(transaction)
        return obj

    def uris(self, obj):
        uri_out = super(InvoicesEndpoint, self).uris(obj)
        uri_out['account_uri'] = AccountsEndpoint().get_object_uri(obj['account'])
        if 'subscription' in obj:
            uri_out['subscription_uri'] = SubscriptionsEndpoint().get_object_uri({'uuid': obj['subscription']})
        return uri_out

    @staticmethod
    def generate_invoice_number():
        if InvoicesEndpoint.backend.empty():
            return '1000'
        return str(max(int(invoice['invoice_number']) for invoice in InvoicesEndpoint.backend.list_objects()) + 1)

class PlansEndpoint(BaseRecurlyEndpoint):
    base_uri = 'plans'
    backend = plans_backend
    pk_attr = 'plan_code'
    object_type = 'plan'
    template = 'plan.xml'
    defaults = {
        'plan_interval_unit': 'months',
        'plan_interval_length': 1,
        'trial_interval_unit': 'months',
        'trial_interval_length': 0,
        'display_quantity': False,
        'tax_exempt': False
    }

    def create(self, create_info):
        create_info['created_at'] = datetime.datetime.now().isoformat()
        defaults = PlansEndpoint.defaults.copy()
        defaults.update(create_info)
        return super(PlansEndpoint, self).create(defaults)

class SubscriptionsEndpoint(BaseRecurlyEndpoint):
    base_uri = 'subscriptions'
    backend = subscriptions_backend
    object_type = 'subscription'
    template = 'subscription.xml'
    defaults = { 'quantity': 1 }

    def _calculate_timedelta(self, units, length):
        timedelta_info = {}
        timedelta_info[units] = length
        return dateutil.relativedelta.relativedelta(**timedelta_info)

    def _parse_isoformat(self, isoformat):
        return dateutil.parser.parse(isoformat)

    def hydrate_foreign_keys(self, obj):
        if 'plan' not in obj:
            obj['plan'] = PlansEndpoint.backend.get_object(obj['plan_code'])
        return obj

    def uris(self, obj):
        uri_out = super(SubscriptionsEndpoint, self).uris(obj)
        pseudo_account_object = {}
        pseudo_account_object[AccountsEndpoint.pk_attr] = obj['account']
        uri_out['account_uri'] = AccountsEndpoint().get_object_uri(pseudo_account_object)
        if 'invoice' in obj:
            pseudo_invoice_object = {}
            pseudo_invoice_object[InvoicesEndpoint.pk_attr] = obj['invoice']
            uri_out['invoice_uri'] = InvoicesEndpoint().get_object_uri(pseudo_invoice_object)
        uri_out['plan_uri'] = PlansEndpoint().get_object_uri(obj['plan'])
        uri_out['cancel_uri'] = uri_out['object_uri'] + '/cancel'
        uri_out['terminate_uri'] = uri_out['object_uri'] + '/terminate'
        return uri_out

    def create(self, create_info):
        account_code = create_info['account'][AccountsEndpoint.pk_attr]
        if not AccountsEndpoint.backend.has_object(account_code):
            AccountsEndpoint().create(create_info['account'])
        else:
            AccountsEndpoint().update(create_info['account'])
        create_info['account'] = account_code

        assert plans_backend.has_object(create_info['plan_code'])
        plan = plans_backend.get_object(create_info['plan_code'])

        now = datetime.datetime.now()

        # Trial dates need to be calculated
        if 'trial_ends_at' in create_info:
            create_info['trial_started_at'] = now.isoformat()
        elif plan['trial_interval_length'] > 0:
            create_info['trial_started_at'] = now.isoformat()
            create_info['trial_ends_at'] = (now + self._calculate_timedelta(plan['trial_interval_unit'], plan['trial_interval_length'])).isoformat()

        # Plan start and end date needs to be calculated
        if 'starts_at' in create_info:
            # A custom start date is specified
            create_info['activated_at'] = create_info['starts_at']
            create_info['current_period_started_at'] = create_info['starts_at'] # TODO: confirm recurly sets current_period_started_at for future subs
        elif 'trial_started_at' in create_info:
            create_info['activated_at'] = self._parse_isoformat(create_info['trial_ends_at'])
            create_info['current_period_started_at'] = create_info['trial_started_at']
            create_info['current_period_ends_at'] = create_info['trial_ends_at']
        else:
            create_info['activated_at'] = now.isoformat()
            create_info['current_period_started_at'] = now.isoformat()

        started_at = self._parse_isoformat(create_info['current_period_started_at'])
        if now >= started_at: # Plan already started
            if 'first_renewal_date' in create_info:
                create_info['current_period_ends_at'] = self._parse_isoformat(create_info['first_renewal_date'])
            else:
                create_info['current_period_ends_at'] = (started_at + self._calculate_timedelta(plan['plan_interval_unit'], plan['plan_interval_length'])).isoformat()

        # Tax calculated based on plan info
        # UNSUPPORTED
        create_info['tax_in_cents'] = 0
        create_info['tax_type'] = 'usst'
        create_info['tax_rate'] = 0

        # Subscription states
        if 'trial_started_at' in create_info:
            create_info['state'] = 'trial'
        elif 'current_period_ends_at' not in create_info:
            create_info['state'] = 'future'
        else:
            create_info['state'] = 'active'

        # If there are addons, make sure they exist in the system
        if 'subscription_add_ons' in create_info:
            for addon in create_info['subscription_add_ons']:
                assert subscription_addons_backend.has_object(addon['add_on_code'])
                addon_obj = subscription_addons_backend.get_object(addon['add_on_code'])
                addon['unit_amount_in_cents'] = addon_obj['unit_amount_in_cents'][create_info['currency']]

        defaults = SubscriptionsEndpoint.defaults.copy()
        defaults['unit_amount_in_cents'] = plan['unit_amount_in_cents'][create_info['currency']]
        defaults.update(create_info)

        # TODO: support bulk

        new_sub = super(SubscriptionsEndpoint, self).create(defaults)

        # create a transaction if the subscription is started
        if defaults['state'] == 'active':
            new_transaction = {}
            new_transaction['account'] = {}
            new_transaction['account'][AccountsEndpoint.pk_attr] = defaults['account']
            new_transaction['amount_in_cents'] = defaults['unit_amount_in_cents']
            new_transaction['currency'] = defaults['currency']
            TransactionsEndpoint().create(new_transaction)
            new_invoice = new_transaction['invoice']
            InvoicesEndpoint.backend.update_object(new_invoice[InvoicesEndpoint.pk_attr], {'subscription': defaults[SubscriptionsEndpoint.pk_attr]})
            new_sub = SubscriptionsEndpoint.backend.update_object(defaults['uuid'], {'invoice': new_invoice[InvoicesEndpoint.pk_attr]})
            return self.serialize(new_sub)
        return new_sub
