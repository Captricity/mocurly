"""Defines errors that can be returned from recurly
"""

# Error codes used key into messages to be returned. This should mirror that of
# recurly.
TRANSACTION_DECLINED = 'declined'
ERROR_CODES = [TRANSACTION_DECLINED]

# Represents error objects that are used to generate the XML response in case
# of simulated failure
# Requires:
#   error_code - Recurly error code that represnts the particular error
#   error_category - Category of the error
#   customer - Error message that should be used for the customer, as provided
#       by recurly.
#   merchant - Error message that should be used for the merchant, as provided
#       by recurly.
TRANSACTION_ERRORS = {}
TRANSACTION_ERRORS[TRANSACTION_DECLINED] = {
    'error_code': TRANSACTION_DECLINED,
    'error_category': 'declined',
    'customer': 'The transaction was declined. Please use a different card or contact your bank.',
    'merchant': 'The transaction was declined without specific information.  Please contact your payment gateway for more details or ask the customer to contact their bank.'
}


class ResponseError(Exception):
    """Exception class used to signal returning an error response from the
    mocked endpoints

    Should only be raised from within the HTTPretty request callbacks.
    """
    def __init__(self, status_code, response_body):
        self.status_code = status_code
        self.response_body = response_body

    def __str__(self):
        return repr(self.status_code)
