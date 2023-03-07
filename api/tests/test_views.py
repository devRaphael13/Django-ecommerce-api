from unittest.mock import patch
from django.forms import ValidationError
from django.urls import reverse
from api.tests.test_setup import (
    TestSetUp,
    mock_bulk_transfer,
    mock_event_transfer_failed,
    mock_event_transfer_reversed,
    mock_event_transfer_success,
    mock_event_charge_success,
    mock_resolve,
    mock_transaction,
    mock_transferrecipient,
    mock_unresolve,
    mock_verify,
    mock_subaccount
)

class TestUserViewSet(TestSetUp):

    def test_admin_can_view_user_list(self):
        admin = self.create_admin()
        res = self.client.get(reverse('user-list'), HTTP_AUTHORIZATION='Token {}'.format(admin.auth_token.key))
        self.assertEqual(res.status_code, 200)

    def test_users_cannot_see_user_list(self):
        user = self.create_user1()
        res = self.client.get(reverse('user-list'), HTTP_AUTHORIZATION='Token {}'.format(user.auth_token.key))
        self.assertEqual(res.status_code, 403)

    def test_admin_can_view_user_detail(self):
        admin = self.create_admin()
        res = self.client.get(reverse('user-detail', kwargs={'pk': 1}), HTTP_AUTHORIZATION='Token {}'.format(admin.auth_token.key))
        self.assertEqual(res.status_code, 200)

    def test_users_can_view_own_detail(self):
        user = self.create_user1()
        res = self.client.get(reverse('user-detail', kwargs={'pk': 1}), HTTP_AUTHORIZATION='Token {}'.format(user.auth_token.key))
        self.assertEqual(res.status_code, 200)
    
    def test_one_cannot_create_account_without_details(self):
        res = self.client.post(reverse('user-list'))
        self.assertEqual(res.status_code, 400)

    def test_anyone_can_create_account(self):
        res = self.client.post(reverse('user-list'), self.user_data)
        self.assertEqual(res.status_code, 201)
    
    def test_user_can_update_account(self):
        user = self.create_user1()
        res = self.client.patch(reverse('user-detail', kwargs={'pk': user.id}), {'first_name': 'Jon'}, HTTP_AUTHORIZATION='Token {}'.format(user.auth_token.key))
        self.assertEqual(res.status_code, 200)

    def test_user_can_delete_account(self):
        user = self.create_user1()
        res = self.client.delete(reverse('user-detail', kwargs={'pk': user.id}), HTTP_AUTHORIZATION='Token {}'.format(user.auth_token.key))
        self.assertEqual(res.status_code, 204)

    def test_user_cannot_delete_another_account(self):
        user_1 = self.create_user1()
        user_2 = self.create_user2()
        res = self.client.delete(reverse('user-detail', kwargs={'pk': user_1.id}), HTTP_AUTHORIZATION='Token {}'.format(user_2.auth_token.key))
        self.assertEqual(res.status_code, 403)

    def test_user_can_add_to_cart(self):
        user = self.create_user1()
        product = self.create_product(user, 5)
        variant = self.create_product_variant(product)
        size = self.create_size(variant, 5)
        res = self.client.post(reverse("user-update-cart"), { "product_variant_id": variant.id, "quantity": 1, "action": "add", "size": size.id}, HTTP_AUTHORIZATION="Token {}".format(user.auth_token.key))
        self.assertEqual(res.status_code, 200)
        self.assertTrue(user.cart.items.exists())

    def test_user_can_subtract_from_cart(self):
        user = self.create_user1()
        product = self.create_product(user, 5)
        variant = self.create_product_variant(product)
        size = self.create_size(variant, 5)
        self.client.post(reverse("user-update-cart"), { "product_variant_id": variant.id, "quantity": 5, "action": "add", "size": size.id}, HTTP_AUTHORIZATION="Token {}".format(user.auth_token.key))
        res = self.client.post(reverse("user-update-cart"), { "product_variant_id": variant.id, "quantity": 2, "action": "subtract"}, HTTP_AUTHORIZATION="Token {}".format(user.auth_token.key))
        self.assertEqual(res.status_code, 200)
        self.assertTrue(user.cart.items.exists())

    def test_user_can_remove_from_cart(self):
        user = self.create_user1()
        product = self.create_product(user, 5)
        variant = self.create_product_variant(product)
        size = self.create_size(variant, 5)
        self.client.post(reverse("user-update-cart"), { "product_variant_id": variant.id, "quantity": 4, "action": "add", "size": size.id}, HTTP_AUTHORIZATION="Token {}".format(user.auth_token.key))
        res = self.client.post(reverse("user-update-cart"), { "product_variant_id": variant.id, "quantity": 2, "action": "remove"}, HTTP_AUTHORIZATION="Token {}".format(user.auth_token.key))
        self.assertEqual(res.status_code, 200)
        self.assertFalse(user.cart.items.exists())

    def test_user_cannot_edit_cart_without_params(self):
        user = self.create_user1()
        res = self.client.post(reverse('user-update-cart'), HTTP_AUTHORIZATION='Token {}'.format(user.auth_token.key))
        self.assertEqual(res.status_code, 400)

class TestProductViewSet(TestSetUp):

    def test_brand_owners_can_create_products(self):
        user = self.create_user1()
        brand = self.create_brand(user)
        cat = self.create_category()
        res = self.client.post(reverse('product-list'), {'name': 'Test', 'category': cat.id, 'price': 1500000, 'brand': brand.id, 'display_image': "https://google.com"}, HTTP_AUTHORIZATION='Token {}'.format(user.auth_token.key))
        self.assertEqual(res.status_code, 201)
        self.assertTrue(user.is_brand_owner)
    
    def test_users_cannot_create_products(self):
        user_1 = self.create_user1()
        user_2 = self.create_user2()
        brand = self.create_brand(user_1)
        cat = self.create_category()
        res = self.client.post(reverse('product-list'), {'name': 'Test', 'category': cat.id, 'price': 1500000, 'brand': brand.id}, HTTP_AUTHORIZATION='Token {}'.format(user_2.auth_token.key))
        self.assertEqual(res.status_code, 403)

    def test_brand_owners_cannot_create_product_with_empty_details(self):
        user = self.create_user1()
        self.create_brand(user)
        res = self.client.post(reverse('product-list'), HTTP_AUTHORIZATION='Token {}'.format(user.auth_token.key))
        self.assertEqual(res.status_code, 400)

    def test_only_the_owner_can_edit_product(self):
        user_1 = self.create_user1()
        user_2 = self.create_user2()
        product = self.create_product(user_1, 1)

        # Test that another user cannot edit another's product
        res = self.client.patch(reverse('product-detail', kwargs={'pk': product.id}), {'name': 'test'}, HTTP_AUTHORIZATION='Token {}'.format(user_2.auth_token.key))
        self.assertEqual(res.status_code, 403)

        # Test that another user cannote delete another's product.
        res = self.client.delete(reverse('product-detail', kwargs={'pk': product.id}), HTTP_AUTHORIZATION='Token {}'.format(user_2.auth_token.key))
        self.assertEqual(res.status_code, 403)

class TestBrandViewSet(TestSetUp):

    def test_authenticated_users_can_create_brand(self):
        user = self.create_user1()
        res = self.client.post(reverse('brand-list'), {'name': 'Test'}, HTTP_AUTHORIZATION='Token {}'.format(user.auth_token.key))
        self.assertEqual(res.status_code, 201)

    def test_unauthenticated_users_cannot_create_brand(self):
        res = self.client.post(reverse('brand-list'), {'name': 'Test'})
        self.assertEqual(res.status_code, 401)

    def test_unauthorized_users_cannot_edit_brand(self):
        user = self.create_user1()
        brand = self.create_brand(user)
        res = self.client.patch(reverse('brand-detail', kwargs={'pk': brand.id}), {'name': 'Test', 'owner': user.id})
        self.assertEqual(res.status_code, 401)


    def test_brand_owner_can_edit_brand(self):
        user = self.create_user1()
        brand = self.create_brand(user)
        res = self.client.patch(reverse('brand-detail', kwargs={'pk': brand.id}), {'name': 'Test2'}, HTTP_AUTHORIZATION='Token {}'.format(user.auth_token.key))
        self.assertEqual(res.status_code, 200)

    def test_another_user_cannot_edit_brand(self):
        user_1 = self.create_user1()
        user_2 = self.create_user2()
        brand = self.create_brand(user_1)
        res = self.client.patch(reverse('brand-detail', kwargs={'pk': brand.id}), {'name': 'Test2'}, HTTP_AUTHORIZATION='Token {}'.format(user_2.auth_token.key))
        self.assertEqual(res.status_code, 403)

    def test_another_brand_owner_cannot_edit_brand(self):
        user_1 = self.create_user1()
        user_2 = self.create_user2()
        brand_1 = self.create_brand(user_1)
        self.create_brand(user_2)
        res = self.client.patch(reverse('brand-detail', kwargs={'pk': brand_1.id}), {'name': 'Test2'}, HTTP_AUTHORIZATION='Token {}'.format(user_2.auth_token.key))
        self.assertEqual(res.status_code, 403)

class TestSizeViewSet(TestSetUp):

    def test_only_owner_can_add_size(self):
        owner = self.create_user1()
        user = self.create_user2()
        product = self.create_product(owner, 5)
        variant = self.create_product_variant(product)
        res_owner = self.client.post(reverse("size-list"), {"size": "EU 41", "variant": variant.id, "quantity": 2}, HTTP_AUTHORIZATION=f"Token {owner.auth_token.key}")
        res_user = self.client.post(reverse("size-list"), {"size": "EU 42", "variant": variant.id, "quantity": 2}, HTTP_AUTHORIZATION=f"Token {user.auth_token.key}")
        self.assertEqual(res_owner.status_code, 201)
        self.assertEqual(res_user.status_code, 403)

    def test_only_owner_can_update_size(self):
        owner = self.create_user1()
        user = self.create_user2()
        product = self.create_product(owner, 6)
        variant = self.create_product_variant(product)
        size = self.create_size(variant, 1)
        res_owner = self.client.patch(reverse("size-detail", kwargs={"pk": size.id}), {"quantity": 2}, HTTP_AUTHORIZATION=f"Token {owner.auth_token.key}")
        res_user = self.client.patch(reverse("size-detail", kwargs={"pk": size.id}), {"quantity": 2}, HTTP_AUTHORIZATION=f"Token {user.auth_token.key}")
        self.assertEqual(res_owner.status_code, 200)
        self.assertEqual(res_user.status_code, 403)

    def test_only_owner_can_delete_size(self):
        owner = self.create_user1()
        user = self.create_user2()
        product = self.create_product(owner, 6)
        variant = self.create_product_variant(product)
        size = self.create_size(variant, 1)
        res_user = self.client.delete(reverse("size-detail", kwargs={"pk": size.id}), HTTP_AUTHORIZATION=f"Token {user.auth_token.key}")
        self.assertEqual(res_user.status_code, 403)

    def test_size_in_sizechart(self):
        owner = self.create_user1()
        product = self.create_product(owner, 5)
        variant = self.create_product_variant(product)
        res_owner = self.client.post(reverse("size-list"), {"size": "Rubbish", "variant": variant.id, "quantity": 2}, HTTP_AUTHORIZATION=f"Token {owner.auth_token.key}")
        self.assertEqual(res_owner.status_code, 400)

    def test_size_cannot_be_more_than_its_variant(self):
        owner = self.create_user1()
        product = self.create_product(owner, 6)
        variant = self.create_product_variant(product)
        res_owner = self.client.post(reverse("size-list"), {"size": "Rubbish", "variant": variant.id, "quantity": 6}, HTTP_AUTHORIZATION=f"Token {owner.auth_token.key}")
        self.assertEqual(res_owner.status_code, 400)

class TestVariantViewSet(TestSetUp):
    
    def test_owner_can_create_variant(self):
        owner = self.create_user1()
        user = self.create_user2()
        brand = self.create_brand(owner)
        product = self.create_product(owner, 5)
        res_owner = self.client.post(reverse("variant-list"), {"product": product.id, "image_url": "https://google.com", "quantity": 2}, HTTP_AUTHORIZATION=f"Token {owner.auth_token.key}")
        res_user = self.client.post(reverse("variant-list"), {"product": product.id, "image_url": "https://google.com", "quantity": 2}, HTTP_AUTHORIZATION=f"Token {user.auth_token.key}")
        self.assertEqual(res_owner.status_code, 201)
        self.assertEqual(res_user.status_code, 403)

    def test_owner_can_update_variant(self):
        owner = self.create_user1()
        user = self.create_user2()
        variant = self.create_product_variant(self.create_product(owner, 5))
        res_owner = self.client.patch(reverse("variant-detail", kwargs={"pk": variant.id}), {"quantity": 3}, HTTP_AUTHORIZATION=f"Token {owner.auth_token.key}")
        res_user = self.client.patch(reverse("variant-detail", kwargs={"pk": variant.id}), {"quantity": 2}, HTTP_AUTHORIZATION=f"Token {user.auth_token.key}")
        self.assertEqual(res_owner.status_code, 200)
        self.assertEqual(res_user.status_code, 403)

    def test_only_owner_can_delete_variant(self):
        owner = self.create_user1()
        user = self.create_user2()
        variant = self.create_product_variant(self.create_product(owner, 5))
        res_user = self.client.delete(reverse("variant-detail", kwargs={"pk": variant.id}), HTTP_AUTHORIZATION=f"Token {user.auth_token.key}")
        self.assertEqual(res_user.status_code, 403)

    def test_variant_cannot_be_higher_than_its_product(self):
        owner = self.create_user1()
        product = self.create_product(owner, 5)
        res = self.client.post(reverse("variant-list"), {"product": product.id, "image_url": "https://google.com", "quantity": 7}, HTTP_AUTHORIZATION=f"Token {owner.auth_token.key}")
        self.assertEqual(res.status_code, 400)

class TestImageViewSet(TestSetUp):
    
    def test_only_product_owner_can_add_image(self):
        owner = self.create_user1()
        user = self.create_user2()
        product = self.create_product(owner, 5)
        res_owner = self.client.post(reverse("image-list"), {"product": product.id, "url": "https://google.com"}, HTTP_AUTHORIZATION=f"Token {owner.auth_token.key}")
        res_user = self.client.post(reverse("image-list"), {"product": product.id, "url": "https://google.com"}, HTTP_AUTHORIZATION=f"Token {user.auth_token.key}")
        self.assertEqual(res_owner.status_code, 201)
        self.assertEqual(res_user.status_code, 403)


    def test_only_owner_can_update_image(self):
        owner = self.create_user1()
        user = self.create_user2()
        image = self.create_image(owner)
        res_owner = self.client.patch(reverse("image-detail", args=(image.id,)), {"url": "https://google2.com"}, HTTP_AUTHORIZATION=f"Token {owner.auth_token.key}")
        res_user = self.client.patch(reverse("image-detail", args=(image.id,)), {"url": "https://google2.com"}, HTTP_AUTHORIZATION=f"Token {user.auth_token.key}")
        self.assertEqual(res_owner.status_code, 200)
        self.assertEqual(res_user.status_code, 403)


    def test_only_owner_can_delete_image(self):
        owner = self.create_user1()
        user = self.create_user2()
        image = self.create_image(owner)
        res = self.client.delete(reverse("image-detail", args=(image.id,)), HTTP_AUTHORIZATION=f"Token {user.auth_token.key}")
        self.assertEqual(res.status_code, 403)

    def test_anyone_can_list_retrieve_image(self):
        owner = self.create_user1()
        user = self.create_user2()
        image = self.create_image(owner)
        res = self.client.get(reverse("image-detail", args=(image.id,)), HTTP_AUTHORIZATION=f"Token {user.auth_token.key}")
        self.assertEqual(res.status_code, 200)

class TestCategoryViewSet(TestSetUp):
    
    def test_admin_can_create_category(self):
        admin = self.create_admin()
        res = self.client.post(reverse('category-list'), {'name': 'Test'}, HTTP_AUTHORIZATION='Token {}'.format(admin.auth_token.key))
        self.assertEqual(res.status_code, 201)

    def test_users_cannot_create_category(self):
        user = self.create_user1()

        # Test for authorized users
        res1 = self.client.post(reverse('category-list'), {'name': 'Test'}, HTTP_AUTHORIZATION='Token {}'.format(user.auth_token.key))
        self.assertEqual(res1.status_code, 403)

        # Test for unauthorized users
        res2 = self.client.post(reverse('category-list'), {'name': 'Test'})
        self.assertEqual(res2.status_code, 401)


    def test_anyone_can_view_category(self):
        category = self.create_category()

        res = self.client.get(reverse('category-list'))
        self.assertEqual(res.status_code, 200)

        res = self.client.get(reverse('category-detail', kwargs={'pk': category.id}))
        self.assertEqual(res.status_code, 200)

    def test_admin_can_edit_category(self):
        category = self.create_category()
        admin = self.create_admin()
        res = self.client.patch(reverse('category-detail', kwargs={'pk': category.id}), {'name': 'Test1'}, HTTP_AUTHORIZATION='Token {}'.format(admin.auth_token.key))
        self.assertEqual(res.status_code, 200)

    def test_admin_can_delete_category(self):
        category = self.create_category()
        admin = self.create_admin()
        res = self.client.delete(reverse('category-detail', kwargs={'pk': category.id}), HTTP_AUTHORIZATION='Token {}'.format(admin.auth_token.key))
        self.assertEqual(res.status_code, 204)

    def test_users_cannot_edit_category(self):
        category = self.create_category()
        user = self.create_user1()

        # Test for authorized Users
        res = self.client.patch(reverse('category-detail', kwargs={'pk': category.id}), {'name': 'Test1'}, HTTP_AUTHORIZATION='Token {}'.format(user.auth_token.key))
        self.assertEqual(res.status_code, 403)

        # Test for unauthorized users
        res = self.client.patch(reverse('category-detail', kwargs={'pk': category.id}), {'name': 'Test1'})
        self.assertEqual(res.status_code, 401)

    def test_users_cannot_delete_category(self):
        category = self.create_category()
        user = self.create_user1()

        # Test for authorized Users
        res = self.client.delete(reverse('category-detail', kwargs={'pk': category.id}), HTTP_AUTHORIZATION='Token {}'.format(user.auth_token.key))
        self.assertEqual(res.status_code, 403)

        # Test for unauthorized Users
        res = self.client.delete(reverse('category-detail', kwargs={'pk': category.id}))
        self.assertEqual(res.status_code, 401)

class TestBankViewSet(TestSetUp):
    
    def test_admin_can_create_bank(self):
        admin = self.create_admin()
        res = self.client.post(reverse('bank-list'), {'name': 'Test', 'code': '054'}, HTTP_AUTHORIZATION='Token {}'.format(admin.auth_token.key))
        self.assertEqual(res.status_code, 201)

    def test_users_cannot_create_bank(self):
        user = self.create_user1()

        # Test for authorized users
        res1 = self.client.post(reverse('bank-list'), {'name': 'Test', 'code': '054'}, HTTP_AUTHORIZATION='Token {}'.format(user.auth_token.key))
        self.assertEqual(res1.status_code, 403)

        # Test for unauthorized users
        res2 = self.client.post(reverse('bank-list'), {'name': 'Test', 'code': '065'})
        self.assertEqual(res2.status_code, 401)

    def test_authorized_users_can_view_bank(self):
        bank = self.create_bank()
        user = self.create_user1()
        res = self.client.get(reverse('bank-list'),  HTTP_AUTHORIZATION='Token {}'.format(user.auth_token.key))
        self.assertEqual(res.status_code, 200)

        res = self.client.get(reverse('bank-detail', kwargs={'pk': bank.id}),  HTTP_AUTHORIZATION='Token {}'.format(user.auth_token.key))
        self.assertEqual(res.status_code, 200)

    def test_unauthorized_users_cannot_view_bank(self):
        bank = self.create_bank()

        # Test for bank_list
        res = self.client.get(reverse('bank-list'))
        self.assertEqual(res.status_code, 401)

        # Test for bank_detail
        res = self.client.get(reverse('bank-detail', kwargs={'pk': bank.pk}))
        self.assertEqual(res.status_code, 401)

    def test_admin_can_edit_bank(self):
        bank = self.create_bank()
        admin = self.create_admin()
        res = self.client.patch(reverse('bank-detail', kwargs={'pk': bank.id}), {'name': 'Test1'}, HTTP_AUTHORIZATION='Token {}'.format(admin.auth_token.key))
        self.assertEqual(res.status_code, 200)

    def test_admin_can_delete_bank(self):
        bank = self.create_bank()
        admin = self.create_admin()
        res = self.client.delete(reverse('bank-detail', kwargs={'pk': bank.id}), HTTP_AUTHORIZATION='Token {}'.format(admin.auth_token.key))
        self.assertEqual(res.status_code, 204)

    def test_users_cannot_edit_bank(self):
        bank = self.create_bank()
        user = self.create_user1()

        # Test for authorized Users
        res = self.client.patch(reverse('bank-detail', kwargs={'pk': bank.id}), {'name': 'Test1'}, HTTP_AUTHORIZATION='Token {}'.format(user.auth_token.key))
        self.assertEqual(res.status_code, 403)

        # Test for unauthorized users
        res = self.client.patch(reverse('bank-detail', kwargs={'pk': bank.id}), {'name': 'Test1'})
        self.assertEqual(res.status_code, 401)

    def test_users_cannot_delete_bank(self):
        bank = self.create_bank()
        user = self.create_user1()

        # Test for authorized Users
        res = self.client.delete(reverse('bank-detail', kwargs={'pk': bank.id}), HTTP_AUTHORIZATION='Token {}'.format(user.auth_token.key))
        self.assertEqual(res.status_code, 403)

        # Test for unauthorized Users
        res = self.client.delete(reverse('bank-detail', kwargs={'pk': bank.id}))
        self.assertEqual(res.status_code, 401)

class TestMessage(TestSetUp):
    
    def test_brand_can_view_own_messages(self):
        user = self.create_user1()
        brand = self.create_brand(user)
        message = self.create_message(brand)
        res = self.client.get(reverse('message-detail', kwargs={'pk': message.id}), HTTP_AUTHORIZATION='Token {}'.format(user.auth_token.key))
        self.assertEqual(res.status_code, 200)

    def test_brand_cannot_change_message(self):
        user = self.create_user1()
        brand = self.create_brand(user)
        message = self.create_message(brand)
        res = self.client.patch(reverse('message-detail', kwargs={'pk': message.id}), HTTP_AUTHORIZATION='Token {}'.format(user.auth_token.key))
        self.assertEqual(res.status_code, 405)

    def test_unauthenticated_brand_cannot_view_message(self):
        res = self.client.get(reverse('message-list'))
        self.assertEqual(res.status_code, 401)

    def test_brand_can_delete_message(self):
        user = self.create_user1()
        brand = self.create_brand(user)
        message = self.create_message(brand)
        res = self.client.delete(reverse('message-detail', kwargs={'pk': message.id}), HTTP_AUTHORIZATION='Token {}'.format(user.auth_token.key))
        self.assertEqual(res.status_code, 204)

    def test_unauthenticated_brand_cannot_delete_message(self):
        user = self.create_user1()
        brand = self.create_brand(user)
        message = self.create_message(brand)
        res = self.client.delete(reverse('message-detail', kwargs={'pk': message.id}))
        self.assertEqual(res.status_code, 401)

    def test_brand_cannot_delete_another_brand_message(self):
        user_1 = self.create_user1()
        user_2 = self.create_user2()
        brand_1 = self.create_brand(user_1)
        self.create_brand(user_2)
        message_1 = self.create_message(brand_1)
        res = self.client.delete(reverse('message-detail', kwargs={'pk': message_1.id}), HTTP_AUTHORIZATION='Token {}'.format(user_2.auth_token.key))
        self.assertEqual(res.status_code, 403)
    
    def test_brand_cannot_view_all_messages(self):
        user = self.create_user1()
        brand = self.create_brand(user)
        self.create_message(brand)
        res = self.client.get(reverse('message-list'), HTTP_AUTHORIZATION='Token {}'.format(user.auth_token.key))
        self.assertEqual(res.status_code, 403)

    def test_brand_cannot_view_another_brand_message(self):
        user_1 = self.create_user1()
        user_2 = self.create_user2()
        brand_1 = self.create_brand(user_1)
        self.create_brand(user_2)
        message_1 = self.create_message(brand_1)
        res = self.client.get(reverse('message-detail', kwargs={'pk': message_1.id}), HTTP_AUTHORIZATION='Token {}'.format(user_2.auth_token.key))
        self.assertEqual(res.status_code, 403)


    def test_cannot_create_message(self):
        user = self.create_user1()
        brand = self.create_brand(user)
        res = self.client.post(reverse('message-list'), {'message': 'Test message', 'status': 'payment.successful', 'brand': brand.id}, HTTP_AUTHORIZATION='Token {}'.format(user.auth_token.key))
        self.assertEqual(res.status_code, 405)

class TestAccountViewSet(TestSetUp):
    transfer_recipient = "py4paystack.routes.transfer_recipient.TransferRecipient.create"
    verification = "py4paystack.routes.verification.Verification.resolve_acct_number"
    subaccount = "py4paystack.routes.subaccount.SubAccounts.create"

    @patch(transfer_recipient, return_value=mock_transferrecipient())
    @patch(verification, return_value=mock_resolve())
    @patch(subaccount, return_value=mock_subaccount())
    def test_ordinary_users_cannot_create_account_details(self, mock_1, mock_2, mock_3):
        user_1 = self.create_user1()
        user_2 = self.create_user2()
        brand = self.create_brand(user_2)
        res = self.client.post(reverse('accounts-list'), {'brand': brand.id, 'acct_no': 1234567890, 'bank': self.create_bank().id}, HTTP_AUTHORIZATION='Token {}'.format(user_1.auth_token.key))
        self.assertEqual(res.status_code, 403)

    def test_owner_can_view_account_details(self):
        user = self.create_user1()
        brand = self.create_brand(user)
        acct = self.create_acct(brand)
        res = self.client.get(reverse('accounts-detail', kwargs={'pk': acct.id}), HTTP_AUTHORIZATION='Token {}'.format(user.auth_token.key))
        self.assertEqual(res.status_code, 200)
    
    @patch(transfer_recipient, return_value=mock_transferrecipient())
    @patch(verification, return_value=mock_resolve())
    @patch(subaccount, return_value=mock_subaccount())
    def test_brand_owner_can_create_account(self, mock_1, mock_2, mock_3):
        user = self.create_user1()
        brand = self.create_brand(user)
        res = self.client.post(reverse('accounts-list'), {'brand': brand.id, 'acct_no': 1234567890, 'bank': self.create_bank().id}, HTTP_AUTHORIZATION='Token {}'.format(user.auth_token.key))
        self.assertEqual(res.status_code, 201)

    def test_admin_can_view_account_details(self):
        admin = self.create_admin()
        user = self.create_user1()
        brand = self.create_brand(user)
        acct = self.create_acct(brand)
        res = self.client.get(reverse('accounts-detail', kwargs={'pk': acct.id}), HTTP_AUTHORIZATION='Token {}'.format(admin.auth_token.key))
        self.assertEqual(res.status_code, 200)

    def test_admin_cannot_update_account_details(self):
        admin = self.create_admin()
        user = self.create_user1()
        brand = self.create_brand(user)
        acct = self.create_acct(brand)
        res = self.client.patch(reverse('accounts-detail', kwargs={'pk': acct.id}), {'acct_no': 1234567890}, HTTP_AUTHORIZATION='Token {}'.format(admin.auth_token.key))
        self.assertEqual(res.status_code, 403)


    @patch(transfer_recipient, return_value=mock_transferrecipient())
    @patch(verification, return_value=mock_resolve())
    @patch(subaccount, return_value=mock_subaccount())
    def test_brand_owners_can_update_account_details(self, mock_1, mock_2, mock_3):
        user = self.create_user1()
        brand = self.create_brand(user)
        acct = self.create_acct(brand)
        res = self.client.patch(reverse('accounts-detail', kwargs={'pk': acct.id}), {'acct_no': 1234567890}, HTTP_AUTHORIZATION='Token {}'.format(user.auth_token.key))
        self.assertEqual(res.status_code, 200)

    def test_brand_owners_can_delete_account_details(self):
        user = self.create_user1()
        brand = self.create_brand(user)
        acct = self.create_acct(brand)
        res = self.client.delete(reverse('accounts-detail', kwargs={'pk': acct.id}), HTTP_AUTHORIZATION='Token {}'.format(user.auth_token.key))
        self.assertEqual(res.status_code, 204)

    def test_admin_cannot_delete_account_details(self):
        admin = self.create_admin()
        user = self.create_user1()
        brand = self.create_brand(user)
        acct = self.create_acct(brand)
        res = self.client.delete(reverse('accounts-detail', kwargs={'pk': acct.id}), HTTP_AUTHORIZATION='Token {}'.format(admin.auth_token.key))
        self.assertEqual(res.status_code, 403)

    def test_brand_owners_cannot_view_other_account_details(self):
        user_1 = self.create_user1()
        user_2 = self.create_user2()
        brand_1 = self.create_brand(user_1)
        self.create_brand(user_2)
        acct_1 = self.create_acct(brand_1)
        res = self.client.get(reverse('accounts-detail', kwargs={'pk': acct_1.id}), HTTP_AUTHORIZATION='Token {}'.format(user_2.auth_token.key))
        self.assertEqual(res.status_code, 404)
        
    @patch(transfer_recipient, return_value=mock_transferrecipient())
    @patch(verification, return_value=mock_resolve())
    @patch(subaccount, return_value=mock_subaccount())
    def test_cannot_create_account_details_with_empty_details(self, mock_1, mock_2, mock_3):
        user = self.create_user1()
        self.create_brand(user)
        res = self.client.post(reverse('accounts-list'), HTTP_AUTHORIZATION='Token {}'.format(user.auth_token.key))
        self.assertEqual(res.status_code, 400)

    @patch(transfer_recipient, return_value=mock_transferrecipient())
    @patch(verification, return_value=mock_resolve())
    @patch(subaccount, return_value=mock_subaccount())
    def test_cannot_create_account_details_without_authentication(self, mock_1, mock_2, mock_3):
        user = self.create_user1()
        brand = self.create_brand(user)
        res = self.client.post(reverse('accounts-list'), {'brand': brand.id, 'acct_no': 1234567890, 'bank': self.create_bank().id})
        self.assertEqual(res.status_code, 401)

class TestTransferViewSet(TestSetUp):

    transfer = "py4paystack.routes.transfers.Transfer.initiate_bulk"

    def test_admin_can_list_transfer(self):
        admin = self.create_admin()
        brand = self.create_brand(self.create_user1())
        self.create_acct(brand)
        transfer = self.create_transfer(brand)
        res = self.client.get(reverse('transfer-list'), HTTP_AUTHORIZATION='Token {}'.format(admin.auth_token.key))
        self.assertEqual(res.status_code, 200)

    def test_admin_can_retrieve_transfer(self):
        admin = self.create_admin()
        brand = self.create_brand(self.create_user1())
        self.create_acct(brand)
        transfer = self.create_transfer(brand)
        res = self.client.get(reverse('transfer-detail', kwargs={'pk': transfer.ref}), HTTP_AUTHORIZATION='Token {}'.format(admin.auth_token.key))
        self.assertEqual(res.status_code, 200)

    @patch(transfer, return_value=mock_bulk_transfer())
    def test_admin_can_transfer(self, mock):
        admin = self.create_admin()
        brand = self.create_brand(self.create_user1())
        self.create_acct(brand)
        self.create_transfer(brand)
        res = self.client.post(reverse('transfer-transfer'), HTTP_AUTHORIZATION='Token {}'.format(admin.auth_token.key))
        self.assertEqual(res.status_code, 200)

    @patch(transfer, return_value=mock_bulk_transfer())
    def test_transfer_with_2_accounts_and_2_transfers(self, mock):
        admin = self.create_admin()
        brand_1 = self.create_brand(self.create_user1())
        brand_2 = self.create_brand(self.create_user2())
        self.create_acct(brand_1)
        self.create_acct(brand_2)
        self.create_transfer(brand_1)
        self.create_transfer(brand_2)
        res = self.client.post(reverse('transfer-transfer'), HTTP_AUTHORIZATION='Token {}'.format(admin.auth_token.key))

        self.assertEqual(res.status_code, 200)

    @patch(transfer, return_value=mock_bulk_transfer())
    def test_transfer_with_2_accounts_and_1_transfers(self, mock):
        admin = self.create_admin()
        brand_1 = self.create_brand(self.create_user1())
        brand_2 = self.create_brand(self.create_user2())
        self.create_acct(brand_1)
        self.create_acct(brand_2)
        self.create_transfer(brand_1)
        res = self.client.post(reverse('transfer-transfer'), HTTP_AUTHORIZATION='Token {}'.format(admin.auth_token.key))
        self.assertEqual(res.status_code, 200)

    @patch(transfer, return_value=mock_bulk_transfer())
    def test_users_cannot_transfer(self, mock):
        user = self.create_user1()
        brand = self.create_brand(user)
        self.create_transfer(brand)
        res = self.client.post(reverse('transfer-transfer'), HTTP_AUTHORIZATION='Token {}'.format(user.auth_token.key))
        self.assertEqual(res.status_code, 403)

    @patch(transfer, return_value=mock_bulk_transfer())
    def test_cannot_transfer_without_account_details(self, mock):
        admin = self.create_admin()
        brand = self.create_brand(self.create_user1())
        self.create_transfer(brand)
        res = self.client.post(reverse('transfer-transfer'), HTTP_AUTHORIZATION='Token {}'.format(admin.auth_token.key))
        self.assertEqual(res.status_code, 404)

    def test_doesnot_transfer_on_empty_records(self):
        admin = self.create_admin()
        res = self.client.post(reverse('transfer-transfer'), HTTP_AUTHORIZATION='Token {}'.format(admin.auth_token.key))
        self.assertEqual(res.status_code, 204)

class TestReview(TestSetUp):
    
    def test_customer_can_leave_review(self):
        user = self.create_user1()
        user_2 = self.create_user2()
        product = self.create_product(user, 5)
        product.customers.add(user_2)
        product.save()
        res = self.client.post(reverse("review-list"), {"review": "gibberish", "stars": 5, "user": user_2.id, "product": product.id}, HTTP_AUTHORIZATION='Token {}'.format(user_2.auth_token.key))
        self.assertEqual(res.status_code, 201)

    def test_customer_must_be_authenticated_to_leave_review(self):
        user = self.create_user1()
        user_2 = self.create_user2()
        product = self.create_product(user, 5)
        product.customers.add(user_2)
        product.save()
        res = self.client.post(reverse("review-list"), {"review": "gibberish", "stars": 5, "user": user_2.id, "product": product.id})
        self.assertEqual(res.status_code, 401)

    def test_anyone_can_see_reviews(self):
        user = self.create_user1()
        user_2 = self.create_user2()
        product = self.create_product(user, 5)
        product.customers.add(user_2)
        product.save()
        res = self.client.get(reverse("review-list"), {"review": "gibberish", "stars": 5, "user": user_2.id, "product": product.id})
        self.assertEqual(res.status_code, 200)

    def test_reviewer_can_update_reviews(self):
        user = self.create_user1()
        review = self.create_review(user, self.create_product(user, 5))
        res = self.client.patch(reverse("review-detail", kwargs={"pk": review.id}), { "stars": 3, "review": "3 stars" }, HTTP_AUTHORIZATION="Token {}".format(user.auth_token.key))
        self.assertEqual(res.status_code, 200)

        user_2 = self.create_user2()
        res = self.client.patch(reverse("review-detail", kwargs={"pk": review.id}), { "stars": 3, "review": "3 stars" }, HTTP_AUTHORIZATION="Token {}".format(user_2.auth_token.key))
        self.assertEqual(res.status_code, 403)


    def test_only_reviewer_can_delete_review(self):
        user = self.create_user1()
        product = self.create_product(user, 5)
        review = self.create_review(user, product)
        review_2 = self.create_review(user, product)
        res = self.client.delete(reverse("review-detail", kwargs={"pk": review.id}), HTTP_AUTHORIZATION="Token {}".format(user.auth_token.key))
        self.assertEqual(res.status_code, 204)

        user_2 = self.create_user2()
        res = self.client.delete(reverse("review-detail", kwargs={"pk": review_2.id}), HTTP_AUTHORIZATION="Token {}".format(user_2.auth_token.key))
        self.assertEqual(res.status_code, 403)

class TestWebhook(TestSetUp):
    
    @patch('django.core.mail.send_mail')
    def test_handles_charge_success_with_cart(self, mock):
        user = self.create_user1()
        product = self.create_product(user, 5)
        variant = self.create_product_variant(product)
        order = self.create_order(user)
        self.client.post(reverse("user-update-cart"), { "product_variant_id": variant.id, "quantity": 4, "action": "add"}, HTTP_AUTHORIZATION="Token {}".format(user.auth_token.key))
        res = self.client.post(reverse("webhook"), mock_event_charge_success(order.ref), format='json')
        self.assertEqual(res.status_code, 200)

    @patch('django.core.mail.send_mail')
    def test_handles_charge_success_with_order_item(self, mock):
        user = self.create_user1()
        product = self.create_product(user, 5)
        variant = self.create_product_variant(product)
        order_item = self.create_order_item(variant, 3)
        order = self.create_order(user, item=order_item)
        res = self.client.post(reverse("webhook"), mock_event_charge_success(order.ref), format='json')
        self.assertEqual(res.status_code, 200)

    @patch('django.core.mail.send_mail')
    def test_handles_transfer_success(self, mock):
        brand = self.create_brand(self.create_user1())
        transfer = self.create_transfer(brand)
        res = self.client.post(reverse('webhook'), mock_event_transfer_success(transfer.ref), format='json')
        self.assertEqual(res.status_code, 200)

    @patch('django.core.mail.send_mail')
    def test_handles_transfer_failed(self, mock):
        brand = self.create_brand(self.create_user1())
        transfer = self.create_transfer(brand)
        res = self.client.post(reverse('webhook'), mock_event_transfer_failed(transfer.ref), format='json')
        self.assertEqual(res.status_code, 200)

    @patch('django.core.mail.send_mail')
    def test_handles_transfer_reversed(self, mock):
        brand = self.create_brand(self.create_user1())
        transfer = self.create_transfer(brand)
        res = self.client.post(reverse('webhook'), mock_event_transfer_reversed(transfer.ref), format='json')
        self.assertEqual(res.status_code, 200)




