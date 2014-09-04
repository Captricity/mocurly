=======
Mocurly
=======

:Author: Captricity
:Version: |release|
:Date: 2014/09/03
:Homepage: `Mocurly Homepage
           <https://github.com/Captricity/mocurly>`_
:Download: `PyPI
           <https://pypi.python.org/pypi/mocurly>`_
:License: `MIT License`_
:Issue tracker: `Github issues
                <https://github.com/Captricity/mocurly/issues>`_


Mocurly is a library that mocks the recurly python client so that you can easily write tests for applications that use the recurly python client.

Mocurly acts as a mock backend for the recurly client, allowing you to use the recurly python client AS IS. This means that all your code that uses the recurly python client and targets recurly objects will all work as you would expect. Best of all: you can use the recurly python client to setup the test environment!

For example, suppose you had a simple function in your app that lists all the users in recurly, and counts them:

::

  import recurly
  recurly.API_KEY = 'foo'
  recurly.SUBDOMAIN = 'bar'
  
  def count_recurly_accounts():
      return len(recurly.Account.all())

With mocurly, you can test the above code like so:

::

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

Within the decorator context, all calls to recurly are captured by mocurly, which keeps the state in memory for the duration of the context. No actual web calls are made, allowing you to test your recurly code without worrying about existing context or internet connections.



Usage
=====

.. toctree::

   basic-usage
   advanced-usage


.. _MIT License:

LICENSE
=======

::

  The MIT License (MIT)
  
  Copyright (c) 2014 Captricity
  
  Permission is hereby granted, free of charge, to any person obtaining a copy
  of this software and associated documentation files (the "Software"), to deal
  in the Software without restriction, including without limitation the rights
  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
  copies of the Software, and to permit persons to whom the Software is
  furnished to do so, subject to the following conditions:
  
  The above copyright notice and this permission notice shall be included in all
  copies or substantial portions of the Software.
  
  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
  OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
  SOFTWARE.
