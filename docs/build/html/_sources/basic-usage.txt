===========
Basic Usage
===========

Mocurly is designed to be used as a wrapper around blocks of code that needs the mocked Recurly context. Within the context, all calls made using the Recurly Python client will talk to the mocked in-memory service instead of the real Recurly.

In the following example, the call to the :meth:`~recurly.Account.save` method of the :class:`recurly.Account` class will create an instance of the account object in Mocurly's in-memory database, but not in your Recurly account:

::

  >>> import recurly
  >>> recurly.API_KEY = 'foo'
  >>> recurly.SUBDOMAIN = 'bar'
  >>> from mocurly import mocurly
  >>> with mocurly():
  >>>     recurly.Account(account_code='foo').save()

Note that you still have to set the `API_KEY` and `SUBDOMAIN` on the Recurly instance, since the Recurly client itself has assertions to make sure they are set. However, the values you use do not matter. They also have to be set outside the Mocurly context, as in the example.

Mocurly can be used as a decorator, context manager, or manually. In all 3 cases, the Mocurly context is reset at the start of the invocation.



Mocurly as decorator
====================

::

  @mocurly
  def test_count_recurly_accounts():
      for i in range(10):
          recurly.Account(account_code=str(i)).save()
      assert count_recurly_accounts() == 10



Mocurly as context manager
==========================

::

  def test_count_recurly_accounts():
      with mocurly():
          for i in range(10):
              recurly.Account(account_code=str(i)).save()
          assert count_recurly_accounts() == 10



Mocurly used manually
=====================

::

  def test_count_recurly_accounts():
      mocurly_ = mocurly()
      mocurly_.start()
  
      for i in range(10):
          recurly.Account(account_code=str(i)).save()
      assert count_recurly_accounts() == 10
  
      mocurly_.stop()
