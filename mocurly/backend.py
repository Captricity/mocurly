class BaseBackend(object):
    def __init__(self):
        self.datastore = {}

    def has_object(self, uuid):
        return uuid in self.datastore

    def add_object(self, obj):
        self.datastore[obj['uuid']] = obj.copy()
        return obj

    def list_objects(self):
        return [v.copy() for v in self.datastore.values()]

    def get_object(self, uuid):
        return self.datastore[uuid].copy()

    def update_object(self, uuid, updated_data):
        obj = self.datastore[uuid]
        obj.update(updated_data)
        return obj.copy()

    def delete_object(self, uuid):
        del self.datastore[uuid]

    def clear_all(self):
        self.datastore = {}

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
invoices_backend = InvoiceBackend()
plans_backend = SubscriptionPlanBackend()
subscriptions_backend = SubscriptionEnrollmentBackend()
transactions_backend = TransactionBackend()

def clear_backends():
    accounts_backend.clear_all()
    billing_info_backend.clear_all()
    invoices_backend.clear_all()
    plans_backend.clear_all()
    subscriptions_backend.clear_all()
    transactions_backend.clear_all()
