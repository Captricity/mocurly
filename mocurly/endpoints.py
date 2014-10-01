"""Classes used to simulate recurly resources and endpoints

Each endpoint class will define the CRUD interface into the resource.
"""
import recurly
import six
import random
import string
import dateutil.relativedelta
import dateutil.parser

from .utils import current_time
from .errors import TRANSACTION_ERRORS, ResponseError
from .utils import details_route, serialize, serialize_list
from .backend import accounts_backend, billing_info_backend, transactions_backend, invoices_backend, subscriptions_backend, plans_backend, plan_add_ons_backend, adjustments_backend, coupons_backend, coupon_redemptions_backend


class BaseRecurlyEndpoint(object):
    """Baseclass for simulating resource endpoints.

    Provides basic CRUD functionality given a resource XML template, and object
    store backend.
    """
    pk_attr = 'uuid'
    XML = 0
    RAW = 1

    def hydrate_foreign_keys(self, obj):
        """Hydrates all foreign key objects from Id strings into actual objects
        """
        return obj

    def get_object_uri(self, obj):
        """Returns the URI to access the given object resource
        """
        cls = self.__class__
        return recurly.base_uri() + cls.base_uri + '/' + obj[cls.pk_attr]

    def uris(self, obj):
        """Returns a dictionary of all URIs related to the object, including foreign keys
        """
        obj = self.hydrate_foreign_keys(obj)
        uri_out = {}
        uri_out['object_uri'] = self.get_object_uri(obj)
        return uri_out

    def serialize(self, obj, format=XML):
        """Serialize the object into the provided format, using the resource
        template.

        Currently only supports XML (for XML representation of the resource.
        This is what recurly expects) and RAW (a dictionary representation of
        the resource)
        """
        if format == BaseRecurlyEndpoint.RAW:
            return obj

        cls = self.__class__
        if type(obj) == list:
            for o in obj:
                o['uris'] = self.uris(o)
            return serialize_list(cls.template, cls.object_type_plural, cls.object_type, obj)
        else:
            obj['uris'] = self.uris(obj)
            return serialize(cls.template, cls.object_type, obj)

    def list(self, format=XML):
        """Endpoint to list all resources stored in the backend
        """
        cls = self.__class__
        out = cls.backend.list_objects()
        return self.serialize(out, format=format)

    def create(self, create_info, format=XML):
        """Endpoint to create a new instance of the resource into the backend
        """
        cls = self.__class__
        if cls.pk_attr in create_info:
            create_info['uuid'] = create_info[cls.pk_attr]
        else:
            create_info['uuid'] = self.generate_id()
        new_obj = cls.backend.add_object(create_info['uuid'], create_info)
        return self.serialize(new_obj, format=format)

    def retrieve(self, pk, format=XML):
        """Endpoint to retrieve an existing resource from the backend

        Raises a 404 if the requested object does not exist.
        """
        cls = self.__class__
        if not cls.backend.has_object(pk):
            raise ResponseError(404, '')
        out = cls.backend.get_object(pk)
        return self.serialize(out, format=format)

    def update(self, pk, update_info, format=XML):
        """Endpoint to update an existing resource from the backend

        Raises a 404 if the requested object does not exist.
        """
        cls = self.__class__
        if not cls.backend.has_object(pk):
            raise ResponseError(404, '')
        out = cls.backend.update_object(pk, update_info)
        return self.serialize(out, format=format)

    def delete(self, pk):
        """Endpoint to delete an existing resource from the backend

        Raises a 404 if the requested object does not exist.
        """
        cls = self.__class__
        if not cls.backend.has_object(pk):
            raise ResponseError(404, '')
        cls.backend.delete_object(pk)
        return ''

    def generate_id(self):
        """Generates a random ID that can be used as a UUID or recurly ID
        """
        return ''.join(random.choice(string.ascii_lowercase + string.digits) for i in range(32))


class AccountsEndpoint(BaseRecurlyEndpoint):
    base_uri = 'accounts'
    pk_attr = 'account_code'
    backend = accounts_backend
    object_type = 'account'
    object_type_plural = 'accounts'
    template = 'account.xml'

    def uris(self, obj):
        uri_out = super(AccountsEndpoint, self).uris(obj)
        uri_out['adjustments_uri'] = uri_out['object_uri'] + '/adjustments'
        if billing_info_backend.has_object(obj[AccountsEndpoint.pk_attr]):
            uri_out['billing_info_uri'] = uri_out['object_uri'] + '/billing_info'
        uri_out['invoices_uri'] = uri_out['object_uri'] + '/invoices'
        uri_out['redemption_uri'] = uri_out['object_uri'] + '/redemption'
        uri_out['subscriptions_uri'] = uri_out['object_uri'] + '/subscriptions'
        uri_out['transactions_uri'] = uri_out['object_uri'] + '/transactions'
        return uri_out

    def create(self, create_info, format=BaseRecurlyEndpoint.XML):
        if 'billing_info' in create_info:
            billing_info = create_info['billing_info']
            billing_info['account'] = create_info['account_code']
            billing_info_backend.add_object(create_info[AccountsEndpoint.pk_attr], billing_info)
            del create_info['billing_info']
        create_info['hosted_login_token'] = self.generate_id()
        create_info['created_at'] = current_time().isoformat()
        return super(AccountsEndpoint, self).create(create_info, format=format)

    def update(self, pk, update_info, format=BaseRecurlyEndpoint.XML):
        if 'billing_info' in update_info:
            updated_billing_info = update_info['billing_info']
            if billing_info_backend.has_object(pk):
                billing_info_backend.update_object(pk, updated_billing_info)
            else:
                updated_billing_info['account'] = pk
                billing_info_backend.add_object(pk, updated_billing_info)
            del update_info['billing_info']
        return super(AccountsEndpoint, self).update(pk, update_info, format=format)

    def delete(self, pk):
        AccountsEndpoint.backend.update_object(pk, {'state': 'closed'})
        billing_info_backend.delete_object(pk)
        return ''

    # Support for nested resources
    # BillingInfo and CouponRedemption are managed by this endpoint, as
    # opposed to having their own since Recurly API only provides access to these
    # resources through the Account endpoint.
    def billing_info_uris(self, obj):
        uri_out = {}
        uri_out['account_uri'] = recurly.base_uri() + AccountsEndpoint.base_uri + '/' + obj['account']
        uri_out['object_uri'] = uri_out['account_uri'] + '/billing_info'
        return uri_out

    def serialize_billing_info(self, obj, format=BaseRecurlyEndpoint.XML):
        if format == BaseRecurlyEndpoint.RAW:
            return obj

        obj['uris'] = self.billing_info_uris(obj)
        return serialize('billing_info.xml', 'billing_info', obj)

    @details_route('GET', 'billing_info')
    def get_billing_info(self, pk, format=BaseRecurlyEndpoint.XML):
        out = billing_info_backend.get_object(pk)
        return self.serialize_billing_info(out, format=format)

    @details_route('PUT', 'billing_info')
    def update_billing_info(self, pk, update_info, format=BaseRecurlyEndpoint.XML):
        out = billing_info_backend.update_object(pk, update_info)
        return self.serialize_billing_info(out, format=format)

    @details_route('DELETE', 'billing_info')
    def delete_billing_info(self, pk):
        billing_info_backend.delete_object(pk)
        return ''

    @details_route('GET', 'transactions', is_list=True)
    def get_transactions_list(self, pk, filters=None, format=BaseRecurlyEndpoint.XML):
        out = TransactionsEndpoint.backend.list_objects(lambda transaction: transaction['account'] == pk)
        return transactions_endpoint.serialize(out, format=format)

    @details_route('GET', 'invoices', is_list=True)
    def get_invoices_list(self, pk, filters=None, format=BaseRecurlyEndpoint.XML):
        out = InvoicesEndpoint.backend.list_objects(lambda invoice: invoice['account'] == pk)
        return invoices_endpoint.serialize(out, format=format)

    @details_route('GET', 'subscriptions', is_list=True)
    def get_subscriptions_list(self, pk, filters=None, format=BaseRecurlyEndpoint.XML):
        def filter_subscriptions(subscription):
            if filters:
                if 'state' in filters and filters['state'][0] == 'live':
                    filters['state'] = ['active', 'canceled', 'future', 'in_trial']
                cond = all(subscription[k] in v for k, v in filters.items())
            else:
                cond = True
            return subscription['account'] == pk and cond
        out = SubscriptionsEndpoint.backend.list_objects(filter_subscriptions)
        return subscriptions_endpoint.serialize(out, format=format)

    @details_route('GET', 'redemption')
    def get_coupon_redemption_view(self, account_code, format=BaseRecurlyEndpoint.XML):
        coupon_redemption = self.get_coupon_redemption(account_code)
        if coupon_redemption is None:
            raise ResponseError(404, '')
        return coupons_endpoint.serialize_coupon_redemption(coupon_redemption, format=format)

    def get_coupon_redemption(self, account_code):
        account_coupon_redemptions = coupon_redemptions_backend.list_objects(lambda redemption: redemption['account_code'] == account_code)
        if len(account_coupon_redemptions) == 0:
            return None

        assert len(account_coupon_redemptions) == 1
        coupon_redemption = account_coupon_redemptions[0]
        return coupons_endpoint.hydrate_coupon_redemption_foreign_keys(coupon_redemption)

    @details_route('DELETE', 'redemption')
    def delete_coupon_redemption(self, account_code, format=BaseRecurlyEndpoint.XML):
        coupon_redemption = self.get_coupon_redemption(account_code)
        if coupon_redemption is None:
            raise ResponseError(404, '')

        coupon_redemption_uuid = coupons_endpoint.generate_coupon_redemption_uuid(coupon_redemption['coupon']['coupon_code'], account_code)
        coupon_redemptions_backend.delete_object(coupon_redemption_uuid)
        return ''


class TransactionsEndpoint(BaseRecurlyEndpoint):
    base_uri = 'transactions'
    backend = transactions_backend
    object_type = 'transaction'
    object_type_plural = 'transactions'
    template = 'transaction.xml'

    def __init__(self):
        self.registered_errors = {}
        return super(TransactionsEndpoint, self).__init__()

    def clear_state(self):
        """Clears all registered errors
        """
        self.registered_errors = {}

    def register_transaction_failure(self, account_code, error_code):
        """Registers an error_code to associate with the given account for all
        transactions made by the account
        """
        self.registered_errors[account_code] = error_code

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
        obj['account']['uris'] = accounts_endpoint.uris(obj['account'])
        uri_out['account_uri'] = obj['account']['uris']['object_uri']
        if 'invoice' in obj:
            # To avoid infinite recursion
            uri_out['invoice_uri'] = invoices_endpoint.get_object_uri(obj['invoice'])
        if 'subscription' in obj:
            pseudo_subscription_object = {}
            pseudo_subscription_object[SubscriptionsEndpoint.pk_attr] = obj['subscription']
            uri_out['subscription_uri'] = subscriptions_endpoint.get_object_uri(pseudo_subscription_object)
        return uri_out

    def create(self, create_info, format=BaseRecurlyEndpoint.XML):
        # Like recurly, creates an invoice that is associated with the
        # transaction
        account_code = create_info['account'][AccountsEndpoint.pk_attr]
        assert AccountsEndpoint.backend.has_object(account_code)
        create_info['account'] = account_code

        create_info['uuid'] = self.generate_id()  # generate id now for invoice
        create_info['tax_in_cents'] = 0  # unsupported
        create_info['action'] = 'purchase'
        create_info['status'] = 'success'
        create_info['test'] = True
        create_info['voidable'] = True
        create_info['refundable'] = True
        create_info['created_at'] = current_time().isoformat()
        create_info['type'] = 'credit_card'
        if 'description' not in create_info:
            create_info['description'] = ''

        # Check to see if we need to throw an error for card failure
        if create_info['account'] in self.registered_errors:
            # update the new transaction with error info
            create_info['voidable'] = False
            create_info['refundable'] = False
            create_info['status'] = 'declined'
            error_code = self.registered_errors[create_info['account']]
            transaction_error = TRANSACTION_ERRORS[error_code]
            create_info['transaction_error'] = transaction_error
            transaction_xml = super(TransactionsEndpoint, self).create(create_info, format)
            error_xml = serialize('transaction_error.xml', 'transaction_error', transaction_error)
            raise ResponseError(422, '<errors>{0}{1}</errors>'.format(error_xml, transaction_xml))

        # Every new transaction creates a new invoice
        new_invoice = {'account': account_code,
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
                       'tax_rate': 0}
        new_invoice['tax_in_cents'] = new_invoice['subtotal_in_cents'] * new_invoice['tax_rate']
        new_invoice['total_in_cents'] = new_invoice['subtotal_in_cents'] + new_invoice['tax_in_cents']
        new_invoice['transactions'] = [create_info['uuid']]
        InvoicesEndpoint.backend.add_object(new_invoice['invoice_number'], new_invoice)
        new_invoice_id = new_invoice[InvoicesEndpoint.pk_attr]

        # Every transaction should have a line item as well
        transaction_charge_line_item = {'account_code': new_invoice['account'],
                                        'currency': new_invoice['currency'],
                                        'unit_amount_in_cents': int(new_invoice['total_in_cents']),
                                        'description': create_info['description'],
                                        'quantity': 1,
                                        'invoice': new_invoice_id}
        transaction_charge_line_item = adjustments_endpoint.create(transaction_charge_line_item, format=BaseRecurlyEndpoint.RAW)
        InvoicesEndpoint.backend.update_object(new_invoice_id, {'line_items': [transaction_charge_line_item]})

        create_info['invoice'] = new_invoice_id
        return super(TransactionsEndpoint, self).create(create_info, format)

    def delete(self, pk, amount_in_cents=None):
        """DELETE is a refund action, and as such this will not delete the
        object from the backend.
        """
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
            # Refunded, so now its no longer refundable
            TransactionsEndpoint.backend.update_object(transaction['uuid'], {'refundable': False})

            invoice = InvoicesEndpoint.backend.get_object(transaction['invoice'])
            InvoicesEndpoint.backend.update_object(transaction['invoice'], {'transactions': invoice['transactions'] + [refund_transaction['uuid']]})
        else:
            # TODO: raise exception - transaction cannot be refunded
            pass
        return ''


class AdjustmentsEndpoint(BaseRecurlyEndpoint):
    base_uri = 'adjustments'
    backend = adjustments_backend
    object_type = 'adjustment'
    object_type_plural = 'adjustments'
    template = 'adjustment.xml'
    defaults = {'state': 'active',
                'quantity': 1,
                'origin': 'credit',
                'product_code': 'basic',
                'discount_in_cents': 0,
                # unsupported
                'tax_exempt': False}

    def uris(self, obj):
        uri_out = super(AdjustmentsEndpoint, self).uris(obj)
        pseudo_account_object = {}
        pseudo_account_object[AccountsEndpoint.pk_attr] = obj['account_code']
        uri_out['account_uri'] = accounts_endpoint.get_object_uri(pseudo_account_object)
        pseudo_invoice_object = {}
        pseudo_invoice_object[InvoicesEndpoint.pk_attr] = obj['invoice']
        uri_out['invoice_uri'] = invoices_endpoint.get_object_uri(pseudo_invoice_object)
        return uri_out

    def create(self, create_info, format=BaseRecurlyEndpoint.XML):
        create_info['created_at'] = create_info['start_date'] = current_time().isoformat()
        if int(create_info['unit_amount_in_cents']) >= 0:
            create_info['type'] = 'charge'
        else:
            create_info['type'] = 'credit'

        # UNSUPPORTED
        create_info['tax_in_cents'] = 0
        create_info['total_in_cents'] = int(create_info['unit_amount_in_cents']) + int(create_info['tax_in_cents'])

        defaults = AdjustmentsEndpoint.defaults.copy()
        defaults.update(create_info)
        defaults['total_in_cents'] -= defaults['discount_in_cents']

        return super(AdjustmentsEndpoint, self).create(defaults, format)


class InvoicesEndpoint(BaseRecurlyEndpoint):
    base_uri = 'invoices'
    backend = invoices_backend
    object_type = 'invoice'
    object_type_plural = 'invoices'
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
                transaction['uris'] = transactions_endpoint.uris(transaction)
        if 'line_items' in obj:
            obj['line_items'] = [AdjustmentsEndpoint.backend.get_object(adjustment_id) if isinstance(adjustment_id, six.string_types) else adjustment_id for adjustment_id in obj['line_items']]
            for adjustment in obj['line_items']:
                adjustment['uris'] = adjustments_endpoint.uris(adjustment)
        return obj

    def uris(self, obj):
        uri_out = super(InvoicesEndpoint, self).uris(obj)
        uri_out['account_uri'] = accounts_endpoint.get_object_uri(obj['account'])
        if 'subscription' in obj:
            uri_out['subscription_uri'] = subscriptions_endpoint.get_object_uri({'uuid': obj['subscription']})
        return uri_out

    @staticmethod
    def generate_invoice_number():
        if InvoicesEndpoint.backend.empty():
            return '1000'
        return str(max(int(invoice['invoice_number']) for invoice in InvoicesEndpoint.backend.list_objects()) + 1)


class CouponsEndpoint(BaseRecurlyEndpoint):
    base_uri = 'coupons'
    backend = coupons_backend
    object_type = 'coupon'
    object_type_plural = 'coupons'
    pk_attr = 'coupon_code'
    template = 'coupon.xml'
    defaults = {'state': 'redeemable',
                'applies_to_all_plans': True,
                'single_use': False}

    def uris(self, obj):
        uri_out = super(CouponsEndpoint, self).uris(obj)
        uri_out['redemptions_uri'] = uri_out['object_uri'] + '/redemptions'
        uri_out['redeem_uri'] = uri_out['object_uri'] + '/redeem'
        return uri_out

    def create(self, create_info, format=BaseRecurlyEndpoint.XML):
        defaults = CouponsEndpoint.defaults.copy()
        defaults.update(create_info)
        return super(CouponsEndpoint, self).create(defaults, format)

    def generate_coupon_redemption_uuid(self, coupon_code, account_code):
        return '__'.join([coupon_code, account_code])

    def hydrate_coupon_redemption_foreign_keys(self, obj):
        if isinstance(obj['coupon'], six.string_types):
            obj['coupon'] = CouponsEndpoint.backend.get_object(obj['coupon'])
        return obj

    def coupon_redemption_uris(self, obj):
        uri_out = {}
        uri_out['coupon_uri'] = coupons_endpoint.get_object_uri(obj['coupon'])
        pseudo_account_object = {}
        pseudo_account_object[AccountsEndpoint.pk_attr] = obj['account_code']
        uri_out['account_uri'] = accounts_endpoint.get_object_uri(pseudo_account_object)
        uri_out['object_uri'] = uri_out['account_uri'] + '/redemption'
        return uri_out

    def serialize_coupon_redemption(self, obj, format=BaseRecurlyEndpoint.XML):
        if format == BaseRecurlyEndpoint.RAW:
            obj = self.hydrate_coupon_redemption_foreign_keys(obj)
            return obj

        if type(obj) == list:
            obj = [self.hydrate_coupon_redemption_foreign_keys(o) for o in obj]
            for o in obj:
                o['uris'] = self.coupon_redemption_uris(o)
            return serialize_list('redemption.xml', 'redemptions', 'redemption', obj)
        else:
            obj = self.hydrate_coupon_redemption_foreign_keys(obj)
            obj['uris'] = self.coupon_redemption_uris(obj)
            return serialize('redemption.xml', 'redemption', obj)

    @details_route('GET', 'redemptions', is_list=True)
    def get_coupon_redemptions(self, pk, filters=None, format=BaseRecurlyEndpoint.XML):
        obj_list = coupon_redemptions_backend.list_objects(lambda redemption: redemption['coupon'] == pk)
        return self.serialize_coupon_redemption(obj_list, format=format)

    @details_route('POST', 'redeem')
    def redeem_coupon(self, pk, redeem_info, format=BaseRecurlyEndpoint.XML):
        assert CouponsEndpoint.backend.has_object(pk)
        redeem_info['coupon'] = pk
        redeem_info['created_at'] = current_time().isoformat()
        return self.serialize_coupon_redemption(coupon_redemptions_backend.add_object(self.generate_coupon_redemption_uuid(pk, redeem_info['account_code']), redeem_info), format=format)

    def determine_coupon_discount(self, coupon, charge):
        type = coupon['discount_type']
        if type == 'percent':
            return int(charge * float(coupon['discount_percent']) / 100)
        else:
            return int(coupon['discount_in_cents'])


class PlansEndpoint(BaseRecurlyEndpoint):
    base_uri = 'plans'
    backend = plans_backend
    pk_attr = 'plan_code'
    object_type = 'plan'
    object_type_plural = 'plans'
    template = 'plan.xml'
    defaults = {'plan_interval_unit': 'months',
                'plan_interval_length': 1,
                'trial_interval_unit': 'months',
                'trial_interval_length': 0,
                'display_quantity': False,
                # unsupported
                'tax_exempt': False}
    add_on_defaults = {'default_quantity': 1,
                       'display_quantity_on_hosted_page': False}

    def uris(self, obj):
        uri_out = super(PlansEndpoint, self).uris(obj)
        uri_out['add_ons_uri'] = uri_out['object_uri'] + '/add_ons'
        return uri_out

    def create(self, create_info, format=BaseRecurlyEndpoint.XML):
        create_info['created_at'] = current_time().isoformat()
        defaults = PlansEndpoint.defaults.copy()
        defaults.update(create_info)
        return super(PlansEndpoint, self).create(defaults, format)

    def generate_plan_add_on_uuid(self, plan_code, add_on_code):
        return '__'.join([plan_code, add_on_code])

    def plan_add_on_uris(self, obj):
        uri_out = {}
        pseudo_plan_object = {}
        pseudo_plan_object[PlansEndpoint.pk_attr] = obj['plan']
        uri_out['plan_uri'] = plans_endpoint.get_object_uri(pseudo_plan_object)
        uri_out['object_uri'] = uri_out['plan_uri'] + '/add_ons/' + obj['add_on_code']
        return uri_out

    def serialize_plan_add_on(self, obj, format=BaseRecurlyEndpoint.XML):
        if format == BaseRecurlyEndpoint.RAW:
            return obj

        if type(obj) == list:
            for o in obj:
                o['uris'] = self.plan_add_on_uris(o)
            return serialize_list('add_on.xml', 'add_ons', 'add_on', obj)
        else:
            obj['uris'] = self.plan_add_on_uris(obj)
            return serialize('add_on.xml', 'add_on', obj)

    @details_route('GET', 'add_ons', is_list=True)
    def get_add_on_list(self, pk, filters=None, format=BaseRecurlyEndpoint.XML):
        out = plan_add_ons_backend.list_objects(lambda add_on: add_on['plan'] == pk)
        return self.serialize_plan_add_on(out, format=format)

    @details_route('POST', 'add_ons')
    def create_add_on(self, pk, create_info, format=BaseRecurlyEndpoint.XML):
        assert PlansEndpoint.backend.has_object(pk)
        create_info['plan'] = pk
        create_info['created_at'] = current_time().isoformat()
        if 'accounting_code' not in create_info:
            create_info['accounting_code'] = create_info['add_on_code']
        return self.serialize_plan_add_on(plan_add_ons_backend.add_object(self.generate_plan_add_on_uuid(pk, create_info['add_on_code']), create_info), format=format)


class SubscriptionsEndpoint(BaseRecurlyEndpoint):
    base_uri = 'subscriptions'
    backend = subscriptions_backend
    object_type = 'subscription'
    object_type_plural = 'subscriptions'
    template = 'subscription.xml'
    defaults = {'quantity': 1, 'collection_method': 'automatic'}

    def _calculate_timedelta(self, units, length):
        timedelta_info = {}
        timedelta_info[units] = int(length)
        return dateutil.relativedelta.relativedelta(**timedelta_info)

    def _parse_isoformat(self, isoformat):
        return dateutil.parser.parse(isoformat)

    def hydrate_foreign_keys(self, obj):
        if 'plan' not in obj:
            obj['plan'] = PlansEndpoint.backend.get_object(obj['plan_code'])
        if 'subscription_add_ons' in obj:
            def hydrate_add_ons(add_on):
                if isinstance(add_on, six.string_types):
                    add_on = plan_add_ons_backend.get_object(plans_endpoint.generate_plan_add_on_uuid(obj['plan_code'], add_on))
                    add_on['unit_amount_in_cents'] = add_on['unit_amount_in_cents'][obj['currency']]
                return add_on
            obj['subscription_add_ons'] = map(hydrate_add_ons, obj['subscription_add_ons'])
        return obj

    def uris(self, obj):
        uri_out = super(SubscriptionsEndpoint, self).uris(obj)
        pseudo_account_object = {}
        pseudo_account_object[AccountsEndpoint.pk_attr] = obj['account']
        uri_out['account_uri'] = accounts_endpoint.get_object_uri(pseudo_account_object)
        if 'invoice' in obj:
            pseudo_invoice_object = {}
            pseudo_invoice_object[InvoicesEndpoint.pk_attr] = obj['invoice']
            uri_out['invoice_uri'] = invoices_endpoint.get_object_uri(pseudo_invoice_object)
        uri_out['plan_uri'] = plans_endpoint.get_object_uri(obj['plan'])
        uri_out['cancel_uri'] = uri_out['object_uri'] + '/cancel'
        uri_out['terminate_uri'] = uri_out['object_uri'] + '/terminate'
        return uri_out

    def create(self, create_info, format=BaseRecurlyEndpoint.XML):
        # Like recurly, this will create a new invoice and transaction that
        # goes with the new subscription enrollment
        account_code = create_info['account'][AccountsEndpoint.pk_attr]
        if not AccountsEndpoint.backend.has_object(account_code):
            accounts_endpoint.create(create_info['account'])
        else:
            accounts_endpoint.update(account_code, create_info['account'])
        create_info['account'] = account_code

        assert plans_backend.has_object(create_info['plan_code'])
        plan = plans_backend.get_object(create_info['plan_code'])

        now = current_time()

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
            # TODO: confirm recurly sets current_period_started_at for future subs
            create_info['current_period_started_at'] = create_info['starts_at']
        elif 'trial_started_at' in create_info:
            create_info['activated_at'] = self._parse_isoformat(create_info['trial_ends_at'])
            create_info['current_period_started_at'] = create_info['trial_started_at']
            create_info['current_period_ends_at'] = create_info['trial_ends_at']
        else:
            create_info['activated_at'] = now.isoformat()
            create_info['current_period_started_at'] = now.isoformat()

        started_at = self._parse_isoformat(create_info['current_period_started_at'])
        if now >= started_at:
            # Plan already started
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
            for add_on in create_info['subscription_add_ons']:
                add_on_uuid = plans_endpoint.generate_plan_add_on_uuid(create_info['plan_code'], add_on['add_on_code'])
                assert plan_add_ons_backend.has_object(add_on_uuid)
            create_info['subscription_add_ons'] = [add_on['add_on_code'] for add_on in create_info['subscription_add_ons']]

        defaults = SubscriptionsEndpoint.defaults.copy()
        defaults['unit_amount_in_cents'] = plan['unit_amount_in_cents'][create_info['currency']]
        defaults.update(create_info)

        # TODO: support bulk

        new_sub = super(SubscriptionsEndpoint, self).create(defaults, format=BaseRecurlyEndpoint.RAW)
        self.hydrate_foreign_keys(new_sub)

        if defaults['state'] == 'active':
            # Setup charges first, to calculate total charge to put on the
            # invoice and transaction
            total = 0
            adjustment_infos = []
            plan_charge_line_item = {
                'account_code': new_sub['account'],
                'currency': new_sub['currency'],
                'unit_amount_in_cents': int(new_sub['unit_amount_in_cents']),
                'description': new_sub['plan']['name'],
                'quantity': new_sub['quantity']
            }
            total += plan_charge_line_item['unit_amount_in_cents']
            adjustment_infos.append(plan_charge_line_item)

            if 'subscription_add_ons' in new_sub:
                for add_on in new_sub['subscription_add_ons']:
                    plan_charge_line_item = {
                        'account_code': new_sub['account'],
                        'currency': new_sub['currency'],
                        'unit_amount_in_cents': int(add_on['unit_amount_in_cents']),
                        'description': add_on['name'],
                        'quantity': new_sub['quantity'],
                    }
                    total += plan_charge_line_item['unit_amount_in_cents']
                    adjustment_infos.append(plan_charge_line_item)

            # now calculate discounts
            coupon_redemption = accounts_endpoint.get_coupon_redemption(new_sub['account'])
            if coupon_redemption:
                for plan_charge_line_item in adjustment_infos:
                    discount = coupons_endpoint.determine_coupon_discount(coupon_redemption['coupon'], plan_charge_line_item['unit_amount_in_cents'])
                    plan_charge_line_item['discount_in_cents'] = discount
                    total -= plan_charge_line_item['discount_in_cents']

            # create a transaction if the subscription is started
            new_transaction = {}
            new_transaction['account'] = {}
            new_transaction['account'][AccountsEndpoint.pk_attr] = new_sub['account']
            new_transaction['amount_in_cents'] = total
            new_transaction['currency'] = new_sub['currency']
            new_transaction['subscription'] = new_sub[SubscriptionsEndpoint.pk_attr]
            new_transaction = transactions_endpoint.create(new_transaction, format=BaseRecurlyEndpoint.RAW)
            new_invoice_id = new_transaction['invoice']

            # Now create accumulated new adjustments for the sub to track line items
            adjustments = []
            for plan_charge_line_item in adjustment_infos:
                plan_charge_line_item['invoice'] = new_invoice_id
                plan_charge_line_item = adjustments_endpoint.create(plan_charge_line_item, format=BaseRecurlyEndpoint.RAW)
                adjustments.append(plan_charge_line_item[AdjustmentsEndpoint.pk_attr])

            InvoicesEndpoint.backend.update_object(new_invoice_id, {'subscription': new_sub[SubscriptionsEndpoint.pk_attr], 'line_items': adjustments})

            new_sub = SubscriptionsEndpoint.backend.update_object(defaults['uuid'], {'invoice': new_invoice_id})
        return self.serialize(new_sub, format=format)

    @details_route('PUT', 'terminate')
    def terminate_subscription(self, pk, terminate_info, format=format):
        subscription = SubscriptionsEndpoint.backend.get_object(pk)
        # assume base transaction exists
        transaction = TransactionsEndpoint.backend.list_objects(lambda trans: trans['subscription'] == subscription[SubscriptionsEndpoint.pk_attr])[0]
        start = self._parse_isoformat(subscription['current_period_started_at'])
        end = self._parse_isoformat(subscription['current_period_ends_at'])
        now = current_time()
        refund_type = terminate_info['refund'][0]
        if refund_type == 'partial':
            if now > end:
                now = end
            days_left = (end - now).days
            total_days = (end - start).days
            refund_amount = int((days_left / total_days) * transaction['amount_in_cents'])
            transactions_endpoint.delete(transaction[TransactionsEndpoint.pk_attr], amount_in_cents=refund_amount)
        elif refund_type == 'full':
            transactions_endpoint.delete(transaction[TransactionsEndpoint.pk_attr])

        return self.serialize(SubscriptionsEndpoint.backend.update_object(pk, {
            'state': 'expired',
            'expires_at': now.isoformat(),
            'current_period_ends_at': now.isoformat()
        }), format=format)

    @details_route('PUT', 'cancel')
    def cancel_subscription(self, pk, cancel_info, format=format):
        subscription = SubscriptionsEndpoint.backend.get_object(pk)
        return self.serialize(SubscriptionsEndpoint.backend.update_object(pk, {
            'state': 'canceled',
            'expires_at': subscription['current_period_ends_at'],
            'canceled_at': current_time().isoformat()
        }), format=format)

accounts_endpoint = AccountsEndpoint()
adjustments_endpoint = AdjustmentsEndpoint()
transactions_endpoint = TransactionsEndpoint()
coupons_endpoint = CouponsEndpoint()
invoices_endpoint = InvoicesEndpoint()
plans_endpoint = PlansEndpoint()
subscriptions_endpoint = SubscriptionsEndpoint()
endpoints = [accounts_endpoint,
             adjustments_endpoint,
             transactions_endpoint,
             coupons_endpoint,
             invoices_endpoint,
             plans_endpoint,
             subscriptions_endpoint]


def clear_endpoints():
    """Clear state off of all endpoints. This ensures that no residual state
    carries over between mocurly contexts.
    """
    transactions_endpoint.clear_state()
