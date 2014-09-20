==============
Advanced Usage
==============

Error handling
==============

Mocurly supports simulating certain error scenarios that commonly occur through the use of Recurly. Currently, as of version |release|, Mocurly supports the following three scenarios:

- `Request timeout`_
- `Request timeout with a successful POST`_
- `Declined transactions`_

Note that at this time, error handling is only supported in manual usage.

Request timeout
---------------

Sometimes API calls may timeout. This may be due to faulty internet connections, or a server outage at recurly.com. While this is an unlikely case, we want to be prepared for those scenarios. That is why Mocurly supports simulating a request that times out.

To trigger timeouts for requests, you can use the :meth:`~mocurly.start_timeout` method on your `mocurly` instance, assuming the context has been started. When called, this will trigger Mocurly to always simulate a timeout by raising an :class:`ssl.SSLError` exception for all requests.

You can stop this behavior at any point by calling the :meth:`~mocurly.stop_timeout` method.

In the following code snippet, the first :meth:`~recurly.Account.save` call will raise an :class:`ssl.SSLError` because it is wrapped in the timeout context, but the second will succeed:

::

  >>> mocurly_ = mocurly()
  >>> mocurly_.start()
  >>> mocurly_.start_timeout()
  >>> # Will fail
  >>> recurly.Account(account_code='foo').save()
  >>> mocurly_.stop_timeout()
  >>> # Will succeed
  >>> recurly.Account(account_code='foo').save()
  >>> mocurly_.stop()

You can also pass an optional filter function to :meth:`~mocurly.start_timeout` to control what requests get timed out. The filter function will receive a `request` object, which contains several attributes you can use to filter the call on. Refer to the API reference for more details on what attributes the request object contains.

For example, the following snippet will only trigger timeouts on GET requests:

::

  >>> mocurly_ = mocurly()
  >>> mocurly_.start()
  >>> mocurly_.start_timeout(lambda request: request.method == 'GET')
  >>> # Will succeed
  >>> recurly.Account(account_code='foo').save()
  >>> # Will fail
  >>> recurly.Account.get('foo')
  >>> mocurly_.stop_timeout()
  >>> mocurly_.stop()

Request timeout with a successful POST
--------------------------------------

As mentioned in the `previous section`__, Mocurly supports simulating requests that timeout. However, sometimes the request times out while receiving a response from the Recurly servers, after the POST request has successfully reached the Recurly server. These cases are especially difficult to deal with, because the Python client raises an exception, even though the request went through and created the object on Recurly's side, which could have charged the user's credit card. Mocurly supports this scenario as well, using a similar syntax as simulating `request timeout`_.

__ `Request timeout`_

To simulate a request timeout with a successfuly POST, use the :meth:`~mocurly.start_timeout_successful_post` method of the Mocurly instance.

Note that by nature of the simulation, this will only simulate the timeout on POST requests. This means that you can use this in combination with :meth:`~mocurly.start_timeout` to simulate complex timeout scenarios.

In the following example, although the save call fails, the account will still be created in the Mocurly database:

::

  >>> mocurly_ = mocurly()
  >>> mocurly_.start()
  >>> mocurly_.start_timeout_successful_post()
  >>> # Will fail, but the account is created successfully
  >>> recurly.Account(account_code='foo').save()
  >>> recurly.Account.get('foo') # returns an actual account
  >>> mocurly_.stop_timeout_successful_post()
  >>> mocurly_.stop()

Like :meth:`~mocurly.start_timeout`, this can also take in a filter function to simulate the timeout only on certain requests.

Declined transactions
---------------------

When we deal with real credit cards out in the wild, there will always be a case where a transaction might fail due to a declined credit card. Mocurly supports simulating transaction requests with a declined credit card, both for one time transactions and subscription payments.

To trigger a declined credit card, use the :meth:`~mocurly.register_transaction_failure` method on your `mocurly` instance. :meth:`~mocurly.register_transaction_failure` takes two arguments: the `account_code` of the user who's credit card will be rejected, and the error code to use. These error codes should be pulled from `mocurly.errors`. Refer to the API reference for more info on what error codes are available.

In the following snippet, the transaction made for Joe will be declined by Mocurly, but not for Billy:

::

  >>> mocurly_ = mocurly()
  >>> mocurly_.start()
  >>> mocurly_.register_transaction_failure('joe', mocurly.errors.TRANSACTION_DECLINED)
  >>> joe = recurly.Account.get('joe')
  >>> recurly.Transaction(amount_in_cents=10, currency='USD', account=joe).save() # will fail
  >>> billy = recurly.Account.get('joe')
  >>> recurly.Transaction(amount_in_cents=10, currency='USD', account=billy).save() # will succeed
  >>> mocurly_.stop()

