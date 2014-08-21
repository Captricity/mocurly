TRANSACTION_DECLINED = 'declined'
ERROR_CODES = [TRANSACTION_DECLINED]

TRANSACTION_ERRORS = {}
TRANSACTION_ERRORS[TRANSACTION_DECLINED] =  {
        'error_code': TRANSACTION_DECLINED,
        'error_category': 'declined',
        'customer': 'The transaction was declined. Please use a different card or contact your bank.',
        'merchant': 'The transaction was declined without specific information. Please contact your payment gateway for more details or ask the customer to contact their bank.'
    }

class ResponseError(Exception):
    def __init__(self, status_code, response_body):
        self.status_code = status_code
        self.response_body = response_body

    def __str__(self):
        return repr(self.status_code)
