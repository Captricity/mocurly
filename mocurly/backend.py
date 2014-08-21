import six

class BaseBackend(object):
    def __init__(self):
        self.datastore = {}

    def empty(self):
        return not bool(self.datastore)

    def has_object(self, uuid):
        return uuid in self.datastore

    def add_object(self, uuid, obj):
        self.datastore[uuid] = obj.copy()
        return obj

    def list_objects(self, filter_pred=lambda x: True):
        return list(six.moves.filter(filter_pred, [v.copy() for v in self.datastore.values()]))

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

class CouponBackend(BaseBackend):
    pass

class CouponRedemptionBackend(BaseBackend):
    pass

class PlanBackend(BaseBackend):
    pass

class PlanAddOnBackend(BaseBackend):
    pass

class SubscriptionBackend(BaseBackend):
    pass

class TransactionBackend(BaseBackend):
    pass

class AdjustmentBackend(BaseBackend):
    pass

accounts_backend = AccountBackend()
billing_info_backend = BillingInfoBackend()
invoices_backend = InvoiceBackend()
coupons_backend = CouponBackend()
coupon_redemptions_backend = CouponRedemptionBackend()
plans_backend = PlanBackend()
plan_add_ons_backend = PlanAddOnBackend()
subscriptions_backend = SubscriptionBackend()
transactions_backend = TransactionBackend()
adjustments_backend = AdjustmentBackend()

def clear_backends():
    accounts_backend.clear_all()
    billing_info_backend.clear_all()
    invoices_backend.clear_all()
    coupons_backend.clear_all()
    coupon_redemptions_backend.clear_all()
    plans_backend.clear_all()
    plan_add_ons_backend.clear_all()
    subscriptions_backend.clear_all()
    transactions_backend.clear_all()
    adjustments_backend.clear_all()
