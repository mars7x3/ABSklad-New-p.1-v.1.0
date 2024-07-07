from typing import Collection, Iterable

from requests import Request
from requests.adapters import HTTPAdapter

from .additions import RetryWithDelay
from .base import APIClient
from .items import DealerItem, SaleProductItem, ProductMetaItem


class OneCAPIClient(APIClient):
    base_url = "http://91.211.251.134/testcrm/hs/asoi/"

    def __init__(
            self,
            username: str,
            password: str,
            retries: int = 0,
            retries_delay: int = 0,
            retries_force_statuses: Collection[int] = None,
            timeout: int = None
    ):
        self._username = username
        self._password = password

        self.timeout = timeout
        self.retries = retries
        self.retries_delay = retries_delay
        self.retries_force_statuses = retries_force_statuses

        super().__init__()
        self.__setup_session()

    @property
    def _auth(self) -> tuple[str, str]:
        return self._username.encode("utf-8"), self._password.encode("utf-8")

    def _process_request(self, request: Request) -> None:
        request.auth = self._auth

    def __setup_session(self):
        if self.timeout and self.timeout > 0:
            self._session_kwargs["timeout"] = self.timeout

        if self.retries > 0:
            retry_adapter = HTTPAdapter(
                max_retries=RetryWithDelay(
                    total=self.retries,
                    backoff_factor=1,
                    status_forcelist=self.retries_force_statuses,
                    delay=self.retries_delay,
                )
            )
            self._session.mount("http://", retry_adapter)

    def action_category(
            self,
            title: str,
            uid: str = "",
            to_delete: bool = False
    ):
        return self.post(
            "CategoryGoodsCreate",
            json={
                "NomenclatureName": "",
                "NomenclatureUID": "",
                "category_title": title,
                "category_uid": uid,
                "delete": 1 if to_delete is True else 0,
                "vendor_code": "",
                "is_product": 0
            }
        )

    def action_product(
            self,
            title: str,
            uid: str,
            category_title: str,
            category_uid: str,
            to_delete: bool = False,
            vendor_code: str = "",
    ):
        return self.post(
            "GoodsCreate",
            json={
                "NomenclatureName": title,
                "NomenclatureUID": uid,
                "CategoryName": category_title,
                "CategoryUID": category_uid,
                "delete": 1 if to_delete is True else 0,
                "vendor_code": vendor_code,
                "is_product": 1
            }
        )

    def action_dealers(self, dealers: Iterable[DealerItem]):
        return self.post("clients", json={"clients": [item.to_payload() for item in dealers]})

    def action_money_doc(
            self,
            user_uid: str,
            amount: int,
            created_at: str,
            order_type: str = "",
            cashbox_uid: str = "00000000-0000-0000-0000-000000000000",
            uid: str = None,
            to_delete: bool = False,
    ):
        return self.post(
            "CreateaPyment",
            json={
                "user_uid": user_uid,
                "amount": amount,
                "created_at": created_at,
                "order_type": order_type,
                "cashbox_uid": cashbox_uid,
                "delete": 1 if to_delete is True else 0,
                "uid": uid or "00000000-0000-0000-0000-000000000000"
            }
        )

    def action_sale(
            self,
            uid: str,
            user_uid: str,
            payment_doc_uid: str,
            created_at: str,
            city_uid: str,
            products: Iterable[SaleProductItem],
            to_delete: bool = False,
    ):
        return self.post(
            "CreateSale",
            json={
                "user_uid": user_uid,
                "created_at": created_at,
                "payment_doc_uid": payment_doc_uid,
                "cityUID": city_uid,
                "delete": 1 if to_delete is True else 0,
                "uid": uid,
                "products": [p.to_payload() for p in products]
            }
        )

    def action_stock(self, uid: str, title: str, to_delete: bool = False):
        return self.post(
            "Warehouses",
            json={
                "CategoryUID": uid,
                "title": title,
                "delete": 1 if to_delete is True else 0
            }
        )

    def action_inventory(
            self,
            uid: str,
            user_uid: str,
            created_at: str,
            city_uid: str,
            products: Iterable[ProductMetaItem],
            to_delete: bool = False,
    ):
        return self.post(
            "CreateInventory",
            json={
                'uid': uid,
                'user_uid': user_uid,
                'delete': 1 if to_delete else 0,
                'created_at': created_at,
                'cityUID': city_uid,
                'products': [p.to_payload() for p in products]
            }
        )

    def action_return_order(
            self,
            uid: str,
            return_uid: str,
            created_at: str,
            products: Iterable[ProductMetaItem],
            to_delete: bool = False,
    ):
        return self.post(
            "ReturnGoods",
            json={
                "uid_return": return_uid,
                "uid": uid,
                "delete": 1 if to_delete else 0,
                "created_at": created_at,
                "products_return": [p.to_payload() for p in products]
            }
        )
