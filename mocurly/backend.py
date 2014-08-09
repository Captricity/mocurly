class BaseBackend(object):
    def __init__(self):
        self.datastore = {}

    def has_object(self, uuid):
        return uuid in self.datastore

    def add_object(self, obj):
        self.datastore[obj['uuid']] = obj
        return obj

    def list_objects(self):
        return self.datastore.values()

    def get_object(self, uuid):
        return self.datastore[uuid]

    def update_object(self, uuid, updated_data):
        obj = self.datastore[uuid]
        obj.update(updated_data)
        return obj

    def delete_object(self, uuid):
        del self.datastore[uuid]

class AccountBackend(BaseBackend):
    pass

class BillingInfoBackend(BaseBackend):
    pass

class InvoiceBackend(BaseBackend):
    pass

class SubscriptionPlanBackend(BaseBackend):
    pass

class SubscriptionEnrollmentBackend(BaseBackend):
    pass

class TransactionBackend(BaseBackend):
    pass

accounts_backend = AccountBackend()
billing_info_backend = BillingInfoBackend()
invoices = InvoiceBackend()
plans = SubscriptionPlanBackend()
subscriptions = SubscriptionEnrollmentBackend()
transactions = TransactionBackend()
