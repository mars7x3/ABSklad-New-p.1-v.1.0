from django.contrib.auth import get_user_model
from rest_framework.reverse import reverse
from rest_framework.test import APITestCase

from account.models import DealerProfile


class TestDealerStore(APITestCase):
    BASE_URL_NAME = 'dealer-store-crud'

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="test_user",
            password="test_pwd",
            email="test_user@example.com",
            status="dealer"
        )
        DealerProfile.objects.create(
            user=self.user,
            city_id=1,
            name="bla bla",
            address="bla bla",
            dealer_status_id=1,
            price_city_id=1
        )
        self.client.force_authenticate(user=self.user)

    def tearDown(self):
        self.client.force_authenticate(user=None)
        self.user.delete()

    def test_create_store_success(self):
        url = reverse(self.BASE_URL_NAME + '-list')
        response = self.client.post(url, {"city": 1}, format='json')
        self.assertEqual(201, response.status_code, response.json())

