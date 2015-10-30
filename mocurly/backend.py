"""In-memory database backends for each recurly resource
"""
import six


class BaseBackend(object):
    """Datastore to store resource objects in memory throughout the recurly context.
    """
    def __init__(self):
        self.datastore = {}

    def empty(self):
        """Whether or not the datastore is empty
        """
        return not bool(self.datastore)

    def has_object(self, uuid):
        """Whether or not the datastore has an object with the requested id
        """
        return uuid in self.datastore

    def add_object(self, uuid, obj):
        """Add the provided object into the datastore
        """
        self.datastore[uuid] = obj.copy()
        return obj

    def list_objects(self, filter_pred=lambda x: True):
        """List the objects in the datastore.

        You can pass in a filter function that returns a boolean given a
        resource object to limit the number of objects to return.
        """
        return list(six.moves.filter(filter_pred, [v.copy() for v in self.datastore.values()]))

    def get_object(self, uuid):
        """Retrieve the object with the given id from the datastore
        """
        return self.datastore[uuid].copy()

    def update_object(self, uuid, updated_data):
        """Update the object with the given id with the new information
        """
        obj = self.datastore[uuid]
        obj.update(updated_data)
        return obj.copy()

    def delete_object(self, uuid):
        """Delete the object with the given id from the datastore
        """
        del self.datastore[uuid]

    def clear_all(self):
        """Clear all objects from the datastore
        """
        self.datastore = {}


class AccountBackend(BaseBackend):
    pass


class BillingInfoBackend(BaseBackend):
    def add_object(self, uuid, obj):
        if obj.get('number', None) is not None:
            raw_number = obj['number'].replace('-', '')
            obj['first_six'] = raw_number[:6]
            obj['last_four'] = raw_number[-4:]
        return super(BillingInfoBackend, self).add_object(uuid, obj)

    def update_object(self, uuid, obj):
        if obj.get('number', None) is not None:
            raw_number = obj['number'].replace('-', '')
            obj['first_six'] = raw_number[:6]
            obj['last_four'] = raw_number[-4:]
        return super(BillingInfoBackend, self).update_object(uuid, obj)


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


# Provide public access to each resource backend, so that users can do low
# level object checking in their tests (e.g query objects that were created as
# a side effect of an action)
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
    """Clears all resource datastores. This ensures that no residual state
    carries over across mocurly contexts.
    """
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
