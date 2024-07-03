from abc import abstractmethod

from dataclasses import dataclass


class BaseItem:
    @abstractmethod
    def to_payload(self) -> dict:
        pass


@dataclass
class DealerItem(BaseItem):
    name: str
    uid: str = ""
    email: str = ""
    phone: str = ""
    address: str = ""
    liability: int = 0
    city: str = ""
    city_uid: str = None
    delete: int = 0

    def to_payload(self) -> dict[str, int | str]:
        return {
            "delete": self.delete,
            "Name": self.name,
            "UID": self.uid,
            "Telephone": self.phone,
            "Address": self.address,
            "Liability": self.liability,
            "Email": self.email,
            "City": self.city,
            "CityUID": self.city_uid or "00000000-0000-0000-0000-000000000000",
        }


@dataclass
class SaleProductItem(BaseItem):
    title: str
    uid: str
    count: int
    price: int

    def to_payload(self):
        return {
            "title": self.title,
            "uid": self.uid,
            "count": self.count,
            "price": self.price
        }


@dataclass
class ProductMetaItem(BaseItem):
    product_uid: str
    count: int
    use_prod_uid: bool = True

    def to_payload(self):
        return {
            'prod_uid' if self.use_prod_uid else 'uid': self.product_uid,
            'count': self.count
        }
