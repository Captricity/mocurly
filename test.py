import recurly

recurly.API_KEY = 'blah'

import mocurly.core

mocurly.core.register()
mocurly.core.HTTPretty.enable()

new_account = recurly.Account()
new_account.account_code = 'blah'
new_account.email = 'verena@example.com'
new_account.first_name = 'Verana'
new_account.last_name = 'Example'
new_account.address = recurly.Address(address1='123 Jackson St.', city='Captricity', state='CA', zip='94105')
new_account.billing_info = recurly.BillingInfo(first_name='Verana', last_name='Example')
new_account.save()

x = recurly.Account.get('blah')
print x.billing_info
