===========
Basic Usage
===========

Mocurly is designed to be used as a wrapper around blocks of code that needs the mocked recurly context. Within the context, all calls made using the recurly python client will talk to the mocked in-memory service instead of the real recurly.

In the following example, the call to the :meth:`~recurly.Account.save` method of the :class:`recurly.Account` class will create an instance of the account object in mocurly's in-memory database, but not in your recurly account:

::

  >>> import recurly
  >>> recurly.API_KEY = 'foo'
  >>> recurly.SUBDOMAIN = 'bar'
  >>> from mocurly import mocurly
  >>> with mocurly():
  >>>     recurly.Account(account_code='foo').save()

Mocurly can be used as a decorator, context manager, or manually. In all 3 cases, the mocurly context is reset at the start of the invocation.



mocurly as decorator
====================

::

  @mocurly
  def test_count_recurly_accounts():
      for i in range(10):
          recurly.Account(account_code=str(i)).save()
      assert count_recurly_accounts() == 10



mocurly as context manager
==========================

::

  def test_count_recurly_accounts():
      with mocurly():
          for i in range(10):
              recurly.Account(account_code=str(i)).save()
          assert count_recurly_accounts() == 10



mocurly used manually
=====================

::

  def test_count_recurly_accounts():
      mocurly_ = mocurly()
      mocurly_.start()
  
      for i in range(10):
          recurly.Account(account_code=str(i)).save()
      assert count_recurly_accounts() == 10
  
      mocurly_.stop()
