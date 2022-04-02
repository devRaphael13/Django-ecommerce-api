import http.client
import json
from django.conf import settings



class Paystack:

    def __init__(self,**kwargs):
        self.secret_key = settings.PAYSTACK_SECRET_KEY
        self.conn = http.client.HTTPSConnection('api.paystack.co')



    def get_headers(self, method):
        headers = { 'Authorization': 'Bearer {}'.format(self.secret_key), 'Content-Type': 'application/json'}
        if method == 'GET':
            del headers['Content-Type']
        return headers


    def request(self, method, path, headers, payload=None):
        if payload is not None:
            self.conn.request(method, path, body=payload, headers=headers)
        else:
            self.conn.request(method, path, headers=headers)
        response = self.conn.getresponse().read().decode('utf-8')
        return response
        
    def transaction(self, email, amount, ref):
        """Accept payments with paystack.

        Args:
            email (str): The email of the customer
            amount (int): Amount in the lowest unit of the currency
            ref (str): Random reference string

        Returns:
            func : returns the result after requesting.
        """
        # TODO provide call_back_url for the user.
        path = '/transaction/initialize'
        headers = self.get_headers('POST')
        payload = json.dumps({
            'email': email,
            'amount': amount,
            'currency': 'NGN',
            'reference': ref,
            'channels': [ 'card', 'bank' ],
            })
        return self.request('POST', path, headers, payload=payload)


    def transfer_recipient(self, name, acct_number, bank_code):

        """Create a transfer recipient with a name (str) and
        a bank code (str).

        Returns:
            func : returns the result after requesting.
        """

        path = '/transferrecipient'
        headers = self.get_headers('POST')
        payload = json.dumps({
                'type': 'nuban',
                'name': '{}'.format(name),
                'account_number': acct_number,
                'bank_code': '{}'.format(bank_code),
                'currency': 'NGN'
            })
        return self.request('POST', path, headers, payload=payload)

    def bulk_transfer_recipients(self, data):

        """
        Creates multiple transfer recipients from a list of 
        dictionaries, with each dictionary containing the name
        (str) and bank_code (str) of the recipient, eg

        [
            { 'name': 'test', 'bank_code': '041', 'account_number': 1234567890 }
        ]
        Returns:
            func : returns the result after requesting.
        """


        path = '/transferrecipient/bulk'
        headers = self.get_headers('POST')
        payload = json.dumps({
            'batch': []
        })
        
        for x in data:
            name = x.get('name', None)
            bank_code = x.get('bank_code', None)
            acct_no = x.get('acct_no', None)
            if  name and bank_code and acct_no:
                y = {
                    'type': 'nuban',
                    'name': name,
                    'account_number': acct_no,
                    'bank_code': bank_code,
                    'currency': 'NGN'
                }
                payload['batch'].append(y)
        return self.request('POST', path, headers, payload=payload)

    def resolve(self, acct_number, bank_code):
        path = '/bank/resolve?account_number={}&bank_code={}'.format(acct_number, bank_code)
        headers = self.get_headers('GET')
        return self.request('GET', path, headers)


    def transfer(self, ref, amount, recipient_code, reason):
        path = '/transfer'
        headers = self.get_headers('POST')
        payload = json.dumps({
            'source': 'balance',
            'reference': ref,
            'amount': amount,
            'recipient': recipient_code,
            'reason': reason
        })
        return self.request('POST', path, headers, payload=payload)

    def bulk_transfer(self, data):

        """
        Initialize transfer to multiple recipients from a list of 
        dictionaries, with each dictionary containing the amount, recipient
         ( as in the recipient code for the customer ) and the reference.

        Returns:
            func : returns the result after requesting.
        """

        path = '/transfer/bulk'
        headers = self.get_headers('POST')
        payload = json.dumps({
            'currency': 'NGN',
            'source': 'balance',
            'transfers': []
        })

        for x in data:
            code = x.get('recipient_code', None)
            amt = x.get('amount', None)
            ref = x.get('ref', None)

            if code and amt and ref:
                payload['transfers'].append({
                    'amount': amt,
                    'recipient': code,
                    'reference': ref
                })

        return self.request('POST', path, headers, payload=payload)

    def verify(self, ref):

        """
        Verify a transaction with the reference.

        Returns:
            func : returns the result after requesting.
        """

        path = '/transaction/verify/{}'.format(ref)
        headers = self.get_headers('GET')
        return self.request('GET', path, headers)

