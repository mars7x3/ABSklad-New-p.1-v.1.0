from copy import deepcopy
from datetime import datetime

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import AccessToken

from account.models import MyUser, ManagerProfile, DealerProfile, DealerStatus, Wallet
from general_service.models import City, Stock
from order.models import MyOrder
from product.models import AsiaProduct, ProductPrice

from crm_general.manager.serializers import ManagerShortOrderSerializer, ManagerOrderSerializer


class ManagerOrderViewTests(APITestCase):
    def setUp(self):
        self.test_city = City.objects.create(
            title="test city",
            slug="test_city"
        )
        self.test_manager = MyUser.objects.create_user(
            username="test_manager_user",
            email="test_manager@gmail.com",
            password="test_manager_password",
            status="manager",
            name="Test Manager"
        )
        self.test_manager_profile = ManagerProfile.objects.create(
            user=self.test_manager,
            city=self.test_city
        )
        token = AccessToken.for_user(user=self.test_manager)
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + str(token))
        self.test_dealer = MyUser.objects.create_user(
            username="test_dealer_user",
            email="test_dealer@gmail.com",
            password="test_dealer_password",
            status="dealer",
            name="Test Dealer",
            phone="71235224525"
        )
        self.test_dealer_status = DealerStatus.objects.create(title="test")
        self.test_dealer_profile = DealerProfile.objects.create(
            user=self.test_dealer,
            city=self.test_city,
            price_city=self.test_city,
            dealer_status=self.test_dealer_status
        )
        self.test_wallet = Wallet.objects.create(
            dealer=self.test_dealer_profile,
            amount_crm=100000,
            amount_1c=100000
        )
        self.test_stock = Stock.objects.create(city=self.test_city)
        self.test_order = MyOrder.objects.create(
            author=self.test_dealer_profile,
            name="Test Order",
            gmail=self.test_dealer.email,
            phone=self.test_dealer.phone,
            stock=self.test_stock,
            price=100,
            cost_price=20,
            type_status="Баллы",
            comment="test comment"
        )

    def test_list_orders(self):
        response = self.client.get(reverse("crm_general-manager-orders-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertIn("results", data)
        self.assertIsInstance(data["results"], list)
        self.assertTrue(data["results"])
        self.assertEqual(data["results"][0], ManagerShortOrderSerializer(instance=self.test_order, many=False).data)

    def test_retrieve_order(self):
        url = reverse("crm_general-manager-orders-detail", args=[self.test_order.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), ManagerOrderSerializer(instance=self.test_order, many=False).data)

    def test_change_activity(self):
        old_active_value = deepcopy(self.test_order.is_active)
        url = reverse("crm_general-manager-orders-update-activity", args=[self.test_order.id])
        response = self.client.patch(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotEqual(response.json()["is_active"], old_active_value)

    def test_create_order(self):
        url = reverse('crm_general-manager-orders-create')
        product_1 = AsiaProduct.objects.create(
            title="Product 1",
            is_active=True
        )
        ProductPrice.objects.create(
            product=product_1,
            city=self.test_city,
            d_status=self.test_dealer_status,
            price=10
        )
        data = {
            "phone": "123456789",
            "address": "Test Address",
            "stock_id": self.test_stock.id,
            "user_id": self.test_dealer.id,
            "product_counts": {
                str(product_1.id): 2,
            },
            "type_status": "Баллы"
        }

        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        created_order = MyOrder.objects.get(id=response.data['id'])
        self.assertEqual(created_order.name, self.test_dealer.name)
        self.assertEqual(created_order.gmail, self.test_dealer.email)
        self.assertEqual(created_order.phone, "123456789")
        self.assertEqual(created_order.address, "Test Address")
        self.assertEqual(created_order.stock, self.test_stock)

        created_order_product = created_order.order_products.first()
        self.assertIsNotNone(created_order_product)
        self.assertEqual(created_order_product.title, product_1.title)
        self.assertEqual(created_order_product.count, 2)
        self.assertEqual(created_order_product.price, 10)
        self.assertEqual(created_order_product.total_price, 20)
        self.assertEqual(created_order_product.discount, 0)


class OrderFilterTests(APITestCase):
    def setUp(self):
        self.test_city = City.objects.create(
            title="test city",
            slug="test_city"
        )
        self.test_manager = MyUser.objects.create_user(
            username="test_manager_user",
            email="test_manager@gmail.com",
            password="test_manager_password",
            status="manager",
            name="Test Manager"
        )
        self.test_manager_profile = ManagerProfile.objects.create(
            user=self.test_manager,
            city=self.test_city
        )
        token = AccessToken.for_user(user=self.test_manager)
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + str(token))
        self.test_dealer = MyUser.objects.create_user(
            username="test_dealer_user",
            email="test_dealer@gmail.com",
            password="test_dealer_password",
            status="dealer",
            name="Test Dealer",
            phone="71235224525"
        )
        self.test_dealer_profile = DealerProfile.objects.create(
            user=self.test_dealer,
            city=self.test_city,
            price_city=self.test_city
        )
        self.test_stock = Stock.objects.create(city=self.test_city)
        self.url = reverse("crm_general-manager-orders-list")

    def test_success_filter_orders_by_status(self):
        for order_status, _ in MyOrder.STATUS:
            order = MyOrder.objects.create(
                author=self.test_dealer_profile,
                name="Test Order",
                gmail=self.test_dealer.email,
                phone=self.test_dealer.phone,
                stock=self.test_stock,
                price=100,
                cost_price=20,
                status=order_status,
                type_status="Баллы",
                comment="test comment"
            )
            response = self.client.get(self.url, data={"status": order_status})
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            data = response.json().get("results")
            self.assertIsInstance(data, list)
            self.assertEqual(order.id, data[0]["id"])

    def test_failure_filter_order_by_status(self):
        response = self.client.get(self.url, data={"status": "invalid_status"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json().get("results")
        self.assertIsInstance(data, list)
        self.assertFalse(data)

    def test_success_filter_orders_by_type_status(self):
        for order_status, _ in MyOrder.TYPE_STATUS:
            order = MyOrder.objects.create(
                author=self.test_dealer_profile,
                name="Test Order",
                gmail=self.test_dealer.email,
                phone=self.test_dealer.phone,
                stock=self.test_stock,
                price=100,
                cost_price=20,
                type_status=order_status,
                comment="test comment"
            )
            response = self.client.get(self.url, data={"type_status": order_status})
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            data = response.json().get("results")
            self.assertIsInstance(data, list)
            self.assertEqual(order.type_status, data[0]["type_status"])

    def test_failure_filter_order_by_type_status(self):
        response = self.client.get(self.url, data={"type_status": "invalid_type_status"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json().get("results")
        self.assertIsInstance(data, list)
        self.assertFalse(data)

    def test_success_search_order_by_name_field(self):
        order = MyOrder.objects.create(
            author=self.test_dealer_profile,
            name="Test Order",
            gmail=self.test_dealer.email,
            phone=self.test_dealer.phone,
            stock=self.test_stock,
            price=100,
            cost_price=20,
            type_status="Баллы",
            comment="test comment"
        )

        valid_search_terms = [
            "test", "Test", "Order", "O", "Ord"
        ]
        for search_term in valid_search_terms:
            valid_response = self.client.get(self.url, data={"search": search_term})
            self.assertEqual(valid_response.status_code, status.HTTP_200_OK)
            data = valid_response.json().get("results")
            self.assertIsInstance(data, list)
            self.assertIn(order.name, data[0]["name"])

    def test_failure_search_order_by_name_field(self):
        invalid_response = self.client.get(self.url, data={"search": "Some_Invalid_Search_Term"})
        self.assertEqual(invalid_response.status_code, status.HTTP_200_OK)
        invalid_data = invalid_response.json().get("results")
        self.assertIsInstance(invalid_data, list)
        self.assertFalse(invalid_data)

    def test_success_filter_order_by_start_date(self):
        order_1 = MyOrder(
            author=self.test_dealer_profile,
            name="Test Order",
            gmail=self.test_dealer.email,
            phone=self.test_dealer.phone,
            stock=self.test_stock,
            price=100,
            cost_price=20,
            type_status="Баллы",
            comment="test comment"
        )
        order_1.created_at = datetime(year=2023, day=1, month=12)
        order_1.save()

        order_2 = MyOrder(
            author=self.test_dealer_profile,
            name="Test Order",
            gmail=self.test_dealer.email,
            phone=self.test_dealer.phone,
            stock=self.test_stock,
            price=100,
            cost_price=20,
            type_status="Баллы",
            comment="test comment"
        )
        order_2.created_at = datetime(year=2023, day=21, month=12)
        order_2.save()
        response = self.client.get(self.url, data={"start_date": "2023-12-20"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json().get("results")
        self.assertIsInstance(data, list)
        self.assertTrue(data)
        self.assertEqual(1, len(data))

    def test_failure_filter_order_by_start_date(self):
        order_1 = MyOrder(
            author=self.test_dealer_profile,
            name="Test Order",
            gmail=self.test_dealer.email,
            phone=self.test_dealer.phone,
            stock=self.test_stock,
            price=100,
            cost_price=20,
            type_status="Баллы",
            comment="test comment"
        )
        order_1.created_at = datetime(year=2023, day=1, month=12)
        order_1.save()

        order_2 = MyOrder(
            author=self.test_dealer_profile,
            name="Test Order",
            gmail=self.test_dealer.email,
            phone=self.test_dealer.phone,
            stock=self.test_stock,
            price=100,
            cost_price=20,
            type_status="Баллы",
            comment="test comment"
        )
        order_2.created_at = datetime(year=2023, day=21, month=12)
        order_2.save()
        response = self.client.get(self.url, data={"start_date": "2023-12-22"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json().get("results")
        self.assertIsInstance(data, list)
        self.assertFalse(data)

    def test_success_filter_order_by_end_date(self):
        order_1 = MyOrder.objects.create(
            author=self.test_dealer_profile,
            name="Test Order",
            gmail=self.test_dealer.email,
            phone=self.test_dealer.phone,
            stock=self.test_stock,
            price=100,
            cost_price=20,
            type_status="Баллы",
            comment="test comment"
        )
        order_1.created_at = datetime(year=2023, day=1, month=12)
        order_1.save()

        order_2 = MyOrder.objects.create(
            author=self.test_dealer_profile,
            name="Test Order",
            gmail=self.test_dealer.email,
            phone=self.test_dealer.phone,
            stock=self.test_stock,
            price=100,
            cost_price=20,
            type_status="Баллы",
            comment="test comment"
        )
        order_2.created_at = datetime(year=2023, day=21, month=12)
        order_2.save()
        response = self.client.get(self.url, data={"end_date": "2023-12-20"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json().get("results")
        self.assertIsInstance(data, list)
        self.assertEqual(1, len(data))

    def test_failure_filter_order_by_end_date(self):
        order_1 = MyOrder(
            author=self.test_dealer_profile,
            name="Test Order",
            gmail=self.test_dealer.email,
            phone=self.test_dealer.phone,
            stock=self.test_stock,
            price=100,
            cost_price=20,
            type_status="Баллы",
            comment="test comment"
        )
        order_1.created_at = datetime(year=2023, day=1, month=12)
        order_1.save()

        order_2 = MyOrder(
            author=self.test_dealer_profile,
            name="Test Order",
            gmail=self.test_dealer.email,
            phone=self.test_dealer.phone,
            stock=self.test_stock,
            price=100,
            cost_price=20,
            type_status="Баллы",
            comment="test comment"
        )
        order_2.created_at = datetime(year=2023, day=21, month=12)
        order_2.save()
        response = self.client.get(self.url, data={"end_date": "2023-11-22"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json().get("results")
        self.assertIsInstance(data, list)
        self.assertFalse(data)
