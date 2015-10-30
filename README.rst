mocurly
=======

|Build Status| |Coverage Status| |Documentation Status|

Mocurly is a library that mocks the recurly python client so that you
can easily write tests for applications that use the recurly python
client.

Full documentation is available at
`readthedocs <http://mocurly.readthedocs.org/en/latest/>`__.

Overview
========

Mocurly acts as a mock backend for the recurly client, allowing you to
use the recurly python client AS IS. This means that all your code that
uses the recurly python client and targets recurly objects will all work
as you would expect. Best of all: you can use the recurly python client
to setup the test environment!

For example, suppose you had a simple function in your app that lists
all the users in recurly, and counts them:

.. code:: python

    import recurly
    recurly.API_KEY = 'foo'
    recurly.SUBDOMAIN = 'bar'

    def count_recurly_accounts():
        return len(recurly.Account.all())

With mocurly, you can test the above code like so:

.. code:: python

    import recurly
    recurly.API_KEY = 'foo'
    recurly.SUBDOMAIN = 'bar'
    from mocurly import mocurly
    from count_module import count_recurly_accounts

    @mocurly
    def test_count_recurly_accounts():
        for i in range(10):
            recurly.Account(account_code=str(i)).save()
        assert count_recurly_accounts() == 10

Within the decorator context, all calls to recurly are captured by
mocurly, which keeps the state in memory for the duration of the
context. No actual web calls are made, allowing you to test your recurly
code without worrying about existing context or internet connections.

Usage
=====

You can use mocurly as a decorator, context manager, or manually.

Decorator
---------

.. code:: python

    @mocurly
    def test_count_recurly_accounts():
        for i in range(10):
            recurly.Account(account_code=str(i)).save()
        assert count_recurly_accounts() == 10

Context Manager
---------------

.. code:: python

    def test_count_recurly_accounts():
        with mocurly():
            for i in range(10):
                recurly.Account(account_code=str(i)).save()
            assert count_recurly_accounts() == 10

Manual
------

.. code:: python

    def test_count_recurly_accounts():
        mocurly_ = mocurly()
        mocurly_.start()

        for i in range(10):
            recurly.Account(account_code=str(i)).save()
        assert count_recurly_accounts() == 10

        mocurly_.stop()

Install
=======

.. code:: shell

    $ pip install mocurly

.. |Build Status| image:: https://travis-ci.org/Captricity/mocurly.svg?branch=master
   :target: https://travis-ci.org/Captricity/mocurly
.. |Coverage Status| image:: https://coveralls.io/repos/Captricity/mocurly/badge.png?branch=master
   :target: https://coveralls.io/r/Captricity/mocurly?branch=master
.. |Documentation Status| image:: https://readthedocs.org/projects/mocurly/badge/?version=latest
   :target: https://readthedocs.org/projects/mocurly/?badge=latest
