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
