> **NOTICE!**
> As of Jan. 1, 2019, Captricity has stopped active development and maintenance of this project.
> 
> We know that there are external users of the project. So we will continue to host
> the project for the time being. We may review and accept minor bug-fixes to the project, 
> but make no commitment to doing so on an on-going basis.
>


mocurly
=======

[![Build Status](https://travis-ci.org/Captricity/mocurly.svg?branch=master)](https://travis-ci.org/Captricity/mocurly) [![Coverage Status](https://coveralls.io/repos/Captricity/mocurly/badge.png?branch=master)](https://coveralls.io/r/Captricity/mocurly?branch=master) [![Documentation Status](https://readthedocs.org/projects/mocurly/badge/?version=latest)](https://readthedocs.org/projects/mocurly/?badge=latest)

Mocurly is a library that mocks the recurly python client so that you can easily write tests for applications that use the recurly python client.

Full documentation is available at [readthedocs](http://mocurly.readthedocs.org/en/latest/).

Overview
========
Mocurly acts as a mock backend for the recurly client, allowing you to use the recurly python client AS IS. This means that all your code that uses the recurly python client and targets recurly objects will all work as you would expect. Best of all: you can use the recurly python client to setup the test environment!

For example, suppose you had a simple function in your app that lists all the users in recurly, and counts them:
```python
import recurly
recurly.API_KEY = 'foo'
recurly.SUBDOMAIN = 'bar'

def count_recurly_accounts():
    return len(recurly.Account.all())
```

With mocurly, you can test the above code like so:
```python
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
```

Within the decorator context, all calls to recurly are captured by mocurly, which keeps the state in memory for the duration of the context. No actual web calls are made, allowing you to test your recurly code without worrying about existing context or internet connections.

Usage
=====
You can use mocurly as a decorator, context manager, or manually.

Decorator
---------
```python
@mocurly
def test_count_recurly_accounts():
    for i in range(10):
        recurly.Account(account_code=str(i)).save()
    assert count_recurly_accounts() == 10
```

Context Manager
---------------
```python
def test_count_recurly_accounts():
    with mocurly():
        for i in range(10):
            recurly.Account(account_code=str(i)).save()
        assert count_recurly_accounts() == 10
```

Manual
------
```python
def test_count_recurly_accounts():
    mocurly_ = mocurly()
    mocurly_.start()

    for i in range(10):
        recurly.Account(account_code=str(i)).save()
    assert count_recurly_accounts() == 10

    mocurly_.stop()
```

Install
=======
```shell
$ pip install mocurly
```
