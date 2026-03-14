from dataclasses import dataclass


@dataclass
class Product:
    id: int
    name: str
    category: str
    description: str
    price: float
    cost: float
    stock: int
    image_url: str
    is_active: bool
    created_at: str

    @classmethod
    def from_row(cls, row):
        return cls(
            id=row["id"],
            name=row["name"],
            category=row["category"],
            description=row["description"],
            price=float(row["price"]),
            cost=float(row["cost"]),
            stock=int(row["stock"]),
            image_url=row["image_url"],
            is_active=bool(row["is_active"]),
            created_at=row["created_at"],
        )

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "description": self.description,
            "price": self.price,
            "cost": self.cost,
            "stock": self.stock,
            "image_url": self.image_url,
            "is_active": self.is_active,
            "created_at": self.created_at,
        }


@dataclass
class Order:
    id: int
    customer_name: str
    customer_phone: str
    customer_address: str
    total: float
    status: str
    created_at: str

    @classmethod
    def from_row(cls, row):
        return cls(
            id=row["id"],
            customer_name=row["customer_name"],
            customer_phone=row["customer_phone"],
            customer_address=row["customer_address"],
            total=float(row["total"]),
            status=row["status"],
            created_at=row["created_at"],
        )

    def to_dict(self):
        return {
            "id": self.id,
            "customer_name": self.customer_name,
            "customer_phone": self.customer_phone,
            "customer_address": self.customer_address,
            "total": self.total,
            "status": self.status,
            "created_at": self.created_at,
        }
