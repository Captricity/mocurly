'''
TODO
'''
from .backends import AccountBackend, BillingInfoBackend

class RecurlyObject(object):
    @classmethod
    def get(cls, uuid):
        return cls.backend.get_object(uuid)

    @classmethod
    def all(cls, uuid):
        return cls.backend.get_all_objects()

    def save(self):
        cls = self.__class__
        if cls.backend.exists(self.uuid):
            cls.backend.update_object(self)
        else:
            cls.backend.add_object(self)

    def delete(self):
        cls.backend.delete_object(self)

    @property
    def attributes(self):
        return self.__class__.backend.attributes

class Account(RecurlyObject):
    backend = AccountBackend()

    @property
    def uuid(self):
        return self.account_code

    def reopen(self):
        # TODO
        raise NotImplementedError

    def notes(self):
        # TODO
        raise NotImplementedError

    def adjustments(self):
        # TODO
        raise NotImplementedError

    @property
    def billing_info(self):
        if hasattr(self, '_billinginfo'):
            return self._billinginfo
        if BillingInfo.backend.exists(self.uuid):
            return BillingInfo.backend.get_object(self.uuid)
        raise AttributeError

    @billing_info.setter
    def set_billing_info(self, billing_info):
        billing_info.uuid = self.uuid
        self._billinginfo = billing_info

class BillingInfo(RecurlyObject):
    backend = BillingInfoBackend()

    def account(self):
        return Account.backend.get_object(self.uuid)
