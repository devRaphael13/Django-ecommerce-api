import uuid
from rest_framework.test import APITestCase
from django.conf import settings
from api.models import (
    Account, 
    Product, 
    Category, 
    Brand, 
    Bank, 
    Message, 
    Order, 
    Transfer, 
    User, 
    OrderItem, 
    Cart, 
    Variant, 
    Size,
    Review,
    Image,
    SizeChart
)

class TestSetUp(APITestCase):

    def setUp(self) -> None:
        self.user_data = {'email': 'test@test.com', 'password': 'test'}
        self.user_data2 = { 'email': 'test2@test.com', 'password': 'test'}
        self.admin_data = {'email': 'admin2@admin.com', 'password': 'admin2'}
        SizeChart.objects.bulk_create([
            SizeChart(name="EU 40"),
            SizeChart(name="EU 41"),
            SizeChart(name="EU 42"),
            SizeChart(name="EU 43"),
            SizeChart(name="EU 44"),
        ])
        settings.PAYSTACK_SECRET_KEY = "Gibberish"
        return super().setUp()

    def create_size(self, variant, quantity):
        return Size.objects.create(variant=variant, quantity=quantity, size="EU 40", is_available=True)

    def create_image(self, user):
        return Image.objects.create(product=self.create_product(user, 5), url="http://google.com")

    def create_review(self, user, product):
        product.customers.add(user)
        product.save()
        return Review.objects.create(user=user, product=product, review="Review", stars=5)

    def create_order_item(self, variant, quantity):
        return OrderItem.objects.create(variant=variant, quantity=quantity, size=self.create_size(variant, quantity))

    def create_user1(self):
        return User.objects.create(**self.user_data)

    def create_cart(self, user):
        return Cart.objects.create(user=user)

    def create_product_variant(self, product):
        return Variant.objects.create(quantity=5, product=product, is_available=True, image_url="http://google.com")
    
    def create_user2(self):
        return User.objects.create(**self.user_data2)
    
    def create_admin(self):
        return User.objects.create_superuser(**self.admin_data)

    def create_item(self, product, quantity):
        return OrderItem.objects.create(product=product, quantity=quantity)

    def create_product(self, user, quantity):
        brand = self.create_brand(user)
        category = self.create_category()
        product = Product.objects.create(name='Test', category=category, brand=brand, price=150000, quantity=quantity)
        return product
    
    def create_brand(self, user):
        user.is_brand_owner = True
        user.save()
        return Brand.objects.create(owner=user, name='Test')

    def create_category(self):
        return Category.objects.create(name='Test')

    def create_bank(self):
        return Bank.objects.create(name='Test', code='065')

    def create_acct(self, brand):
        return Account.objects.create(bank=self.create_bank(), brand=brand, acct_no=1234567890, recipient_code="random_giberish1")
    
    def create_acct2(self, brand):
        return Account.objects.create(bank=self.create_bank(), brand=brand, acct_no=9876543210, recipient_code="random_giberish2")
        

    def create_message(self, brand):
        return Message.objects.create(message='Test message', status='payment.successful', brand=brand)
    
    def create_order(self, user, item=None):
        if item is None:
            return Order.objects.create(user=user)
        return Order.objects.create(user=user, order_item=item)


    def create_transfer(self, brand):
        return Transfer.objects.create(brand=brand, amount=100000)

    def tearDown(self) -> None:
        return super().tearDown()


def mock_secret_key():
    return "lorem ipsum gibberish"

def mock_transferrecipient():
    return {
        "status": True,
        "message": "Transfer recipient created successfully",
        "data": {
            "active": True,
            "createdAt": "2020-11-05T11:27:53.131Z",
            "currency": "NGN",
            "domain": "test",
            "id": 29317609,
            "integration": 463433,
            "name": "Tolu Roberts",
            "recipient_code": "RCP_m7ljkv8leesep7p",
            "type": "nuban",
            "updatedAt": "2021-11-05T11:27:53.131Z",
            "is_deleted": False,
            "details": {
                "authorization_code": None,
                "account_number": "1234567890",
                "account_name": "Tolu Roberts",
                "bank_code": "065",
                "bank_name": "Test"
            }
        }
    }

def mock_subaccount():
    return {
        "status": True,
        "message": "Subaccount created",
        "data": {
            "integration": 100973,
            "domain": "test",
            "subaccount_code": "ACCT_4hl4xenwpjy5wb",
            "business_name": "Sunshine Studios",
            "description": None,
            "primary_contact_name": None,
            "primary_contact_email": None,
            "primary_contact_phone": None,
            "metadata": None,
            "percentage_charge": 18.2,
            "is_verified": False,
            "settlement_bank": "Access Bank",
            "account_number": "0193274682",
            "settlement_schedule": "AUTO",
            "active": True,
            "migrate": False,
            "id": 55,
            "createdAt": "2016-10-05T13:22:04.000Z",
            "updatedAt": "2016-10-21T02:19:47.000Z"
        }
    }

def mock_resolve():
    return {
        "status": True,
        "message": "Account number resolved",
        "data": {
            "account_number": "1234567890",
            "account_name": "Tolu Roberts"
        }
    }

def mock_unresolve():
    return {
        'status': False,
        'message': 'Account number unresolved'
    }

def mock_verify():
    return {
            'status': True,
            'message': 'verification successful',
            'data': {
                'amount': 27000,
                'currency': 'NGN',
                'transaction_date': '2017-10-01T11:03:09.000Z',
                'status': 'success',
                'reference': 'DG4uishudoq9OLD',
                'domain': 'test',
                'metadata': 0,
                'gateway_response': 'Successful',
                'message': None,
                'channel': 'card',
                'ip_address': '41.1.25.1',
                'log': {
                    'time_spent': 9,
                    'attempts': 1,
                    'authentication': None,
                    'errors': 0,
                    'success': True,
                    'mobile': False,
                    'input': [],
                    'channel': None,
                    'history': [{
                        'type': 'input',
                        'message': 'Filled these fields: card number, card expiry, card cvv',
                        'time': 7
                    },
                    {
                        'type': 'action',
                        'message': 'Attempted to pay',
                        'time': 7
                    },
                    {
                        'type': 'success',
                        'message': 'Succefully paid',
                        'time': 8
                    },
                    {
                        'type': 'close',
                        'message': 'Page closed',
                        'time': 9
                    }]
                },
                'fees': None,
                'authorization': {
                    'authorization_code': 'AUTH_8dfhjjdt',
                    'card_type': 'visa',
                    'last4': '1381',
                    'exp_month': '08',
                    'exp_year': '2018',
                    'bin': '412345',
                    'bank': 'TEST BANK',
                    'channel': 'card',
                    'signature': 'SIG_idyuhgd87dUYSH092D',
                    'reuseable': True,
                    'country_code': 'NG',
                    'account_name': 'Bojack Horseman'
                }
            }
        }


def mock_transaction():
    return {
            'status': True,
            'message': 'Authorization URL created',
            'data': {
                'authorization_url': 'https://checkout.paystack.com/Opeioxfhpn',
                'access_code': 'Opeioxfhpn',
                'reference': '7PVGX8MEk85tgeEpVDtD'
            }
        }


def mock_bulk_transfer():
    return {
            'status': True,
            'message': '2 transfers queued.',
            'data': [
                {
                    'recipient': 'RCP_db342dvqvz9qcrn',
                    'amount': 5000000,
                    'transfer_code': 'TRF_jblmryckdrc6zq4',
                    'currency': 'NGN'
                },
                {
                    'recipient': 'RCP_db342dvqvz9qcrn',
                    'amount': 5000000,
                    'transfer_code': 'TRF_jblmryckdrc6zq4',
                    'currency': 'NGN'
                }
            ]
        }

def mock_event_transfer_success(ref):
    return {
        'event': 'transfer.success',
        'data': {
            'amount': 30000,
            'currency': 'NGN',
            'domain': 'test',
            'failures': None,
            'id': 37272792,
            'integration': {
                'id': 463433,
                'is_live': True,
                'business_name': 'Usell'
            },
            'reason': 'Have fun',
            'reference': ref,
            'source': 'balance',
            'source_details': None,
            'status': 'success',
            'titan_code': None,
            'transfer_code': 'TRF_wpl1dem44967avzm',
            'transferred_at': None,
            'recipient': {
                'active': True,
                'currency': 'NGN',
                'description': '',
                'domain': 'test',
                'email': None,
                'id': 8690817,
                'integration': 463433,
                'metadata': None,
                'name': 'Jack Sparrow',
                'recipient_code': 'RCP_a8wkxiychzdzfgs',
                'type': 'nuban',
                'is_deleted': False,
                'details': {
                    'account_details': '000000000000',
                    'account_name': None,
                    'bank_code': '011',
                    'bank_name': 'First Bank of Nigeria'
                },
                'created_at': '2020-09-03T12:11:25.000Z',
                'updated_at': '2020-09-03T12:11:25.000Z'
            },
            'session': { 'provider': None, 'id': None },
            'created_at': '2020-10-26T12:28:57.000Z',
            'updated_at': '2020-10-26T12:29:57.000Z'
        }
    }

def mock_event_transfer_failed(ref):
    return {
        'event': 'transfer.failed',
        'data': {
            'amount': 30000,
            'currency': 'NGN',
            'domain': 'test',
            'failures': None,
            'id': 37272792,
            'integration': {
                'id': 463433,
                'is_live': True,
                'business_name': 'Usell'
            },
            'reason': 'Have fun',
            'reference': ref,
            'source': 'balance',
            'source_details': None,
            'status': 'failed',
            'titan_code': None,
            'transfer_code': 'TRF_wpl1dem44967avzm',
            'transferred_at': None,
            'recipient': {
                'active': True,
                'currency': 'NGN',
                'description': '',
                'domain': 'test',
                'email': None,
                'id': 8690817,
                'integration': 463433,
                'metadata': None,
                'name': 'Jack Sparrow',
                'recipient_code': 'RCP_a8wkxiychzdzfgs',
                'type': 'nuban',
                'is_deleted': False,
                'details': {
                    'account_details': '000000000000',
                    'account_name': None,
                    'bank_code': '011',
                    'bank_name': 'First Bank of Nigeria'
                },
                'created_at': '2020-09-03T12:11:25.000Z',
                'updated_at': '2020-09-03T12:11:25.000Z'
            },
            'session': { 'provider': None, 'id': None },
            'created_at': '2020-10-26T12:28:57.000Z',
            'updated_at': '2020-10-26T12:29:57.000Z'
        }
    }

def mock_event_charge_success(ref):
    return {
        'event': 'charge.success',
        'data': {
            'id': 302961,
            'domain': 'live',
            'status': 'success',
            'reference': ref,
            'amount': 100000,
            'message': None,
            'gateway_response': 'Approved by Financial Institution',
            'paid_at': '2016-09-30T21z:10:19.000Z',
            'created_at': '2016-09-30T21:09:56.000Z',
            'channel': 'card',
            'currency': 'NGN',
            'ip_address': '41.242.49.37',
            'metadata': 0,
            'log': {
                'time_spent': 16,
                'attempts': 1,
                'success': False,
                'mobile': False,
                'input': [],
                'channel': None,
                'history': [
                    {
                        'type': 'input',
                        'message': 'Filled these fields: card number, card expiry, card cvv',
                        'time': 15
                    },
                    {
                        'type': 'action',
                        'message': 'Attempted to pay',
                        'time': 15
                    },
                    {
                        'type': 'auth',
                        'message': 'Authentication Required: pin',
                        'time': 16
                    }
                ]
            },
            'fees': None,
            'customer': {
                'id': 68324,
                'first_name': 'BoJack',
                'last_name': 'Horseman',
                'email': 'bojack@horseman.com',
                'customer_code': 'CUS_qo38as2hpsgk2ro',
                'phone': None,
                'metadata': None,
                'risk_action': 'default'
            },
            'authorization': {
                'authorization_code': 'AUTH_f5rnfq9p',
                'bin': '539999',
                'last4': '8877',
                'exp_month': '08',
                'exp_year': '2020',
                'card_type': 'mastercard DEBIT',
                'bank': 'Guaranty Trust Bank',
                'country_code': 'NG',
                'brand': 'mastercard',
                'account_name': 'BoJack Horseman'
            },
            'plan': {}
        }
    }

def mock_event_transfer_reversed(ref):
    return {
        'event': 'transfer.reversed',
        'data': {
            'amount': 30000,
            'currency': 'NGN',
            'domain': 'test',
            'failures': None,
            'id': 37272792,
            'integration': {
                'id': 463433,
                'is_live': True,
                'business_name': 'Usell'
            },
            'reason': 'Have fun',
            'reference': ref,
            'source': 'balance',
            'source_details': None,
            'status': 'reversed',
            'titan_code': None,
            'transfer_code': 'TRF_wpl1dem44967avzm',
            'transferred_at': '2020-03-24T07:14:00.000Z',
            'recipient': {
                'active': True,
                'currency': 'NGN',
                'description': '',
                'domain': 'test',
                'email': None,
                'id': 8690817,
                'integration': 463433,
                'metadata': None,
                'name': 'Jack Sparrow',
                'recipient_code': 'RCP_a8wkxiychzdzfgs',
                'type': 'nuban',
                'is_deleted': False,
                'details': {
                    'account_details': '000000000000',
                    'account_name': None,
                    'bank_code': '011',
                    'bank_name': 'First Bank of Nigeria'
                },
                'created_at': '2020-09-03T12:11:25.000Z',
                'updated_at': '2020-09-03T12:11:25.000Z'
            },
            'session': { 'provider': None, 'id': None },
            'created_at': '2020-10-26T12:28:57.000Z',
            'updated_at': '2020-10-26T12:29:57.000Z'
        }
    }