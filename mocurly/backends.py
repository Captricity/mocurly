'''
TODO
'''
import datetime
import string
import random

class Backend(object):
    def __init__(self):
        self.datastore = {}

    def add_object(self, new_object):
        cls = self.__class__
        for attribute in cls.required_attributes:
            if not hasattr(new_object, attribute):
                # TODO: throw real exception
                raise Exception('Missing required attribute {}'.format(attribute))
        for attribute in cls.attributes:
            if not hasattr(new_object, attribute):
                setattr(new_object, attribute, '')

        self.datastore[uuid] = new_object
        return new_object

    def get_object(self, uuid):
        return self.datastore[uuid]

    def get_all_objects(self):
        return self.datastore.values()

    def exists(self, uuid):
        return uuid in self.datastore

    def update_object(self, updated_object):
        assert self.exists(updated_object.uuid)
        self.datastore[updated_object.uuid] = updated_object
        return updated_object

    def delete_object(self, deleted_object):
        del self.datastore[deleted_object.uuid]

class AccountBackend(object):
    attributes = ('account_code', 'username', 'email', 'first_name',
            'last_name', 'company_name', 'vat_number', 'tax_exempt',
            'billing_info', 'address', 'accept_language', 'created_at',
            'hosted_login_token')
    required_attributes = ('account_code',)

    def add_object(self, new_account):
        from .models import BillingInfo
        new_account.hosted_login_token = self.generate_random_login_token()
        new_account.created_at = datetime.datetime.now().isoformat()
        new_account = super(AccountBackend, self).add_object(new_account)
        try:
            new_billing_info = new_account.billing_info
            BillingInfo.backend.add_object(new_billing_info, new_account.uuid)
        except AttributeError:
            pass

    def generate_random_login_token(self):
        return ''.join(random.choice(string.ascii_lowercase + string.digits) for i in xrange(32))

class BillingInfoBackend(Backend):
    attributes = ('type', 'first_name', 'last_name', 'number',
            'verification_value', 'year', 'month', 'start_month', 'start_year',
            'issue_number', 'company', 'address1', 'address2', 'city', 'state',
            'zip', 'country', 'phone', 'vat_number', 'ip_address',
            'ip_address_country', 'card_type', 'first_six', 'last_four',
            'billing_agreement_id')
    required_attributes = ('first_name', 'last_name', 'number', 'month', 'year', 'uuid')
