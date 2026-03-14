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
    sku: str
    barcode: str
    supplier_reference: str
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
            sku=row["sku"] or "",
            barcode=row["barcode"] or "",
            supplier_reference=row["supplier_reference"] or "",
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
            "sku": self.sku,
            "barcode": self.barcode,
            "supplier_reference": self.supplier_reference,
            "is_active": self.is_active,
            "created_at": self.created_at,
        }


@dataclass
class Order:
    id: int
    customer_name: str
    customer_phone: str
    customer_address: str
    customer_id: int
    total: float
    status: str
    source: str
    external_order_id: str
    payment_status: str
    payment_method: str
    subtotal: float
    shipping_amount: float
    discount_amount: float
    transaction_id: str
    approved_at: str
    cancelled_at: str
    shipping_method: str
    shipping_tracking_code: str
    shipping_label_url: str
    shipping_status: str
    internal_notes: str
    created_at: str

    @classmethod
    def from_row(cls, row):
        return cls(
            id=row["id"],
            customer_name=row["customer_name"],
            customer_phone=row["customer_phone"],
            customer_address=row["customer_address"],
            customer_id=int(row["customer_id"] or 0) if "customer_id" in row.keys() else 0,
            total=float(row["total"]),
            status=row["status"],
            source=row["source"] or "aurora_makes",
            external_order_id=row["external_order_id"] or "",
            payment_status=row["payment_status"] or "pending",
            payment_method=row["payment_method"] or "",
            subtotal=float(row["subtotal"] if "subtotal" in row.keys() else row["total"]),
            shipping_amount=float(row["shipping_amount"] if "shipping_amount" in row.keys() else 0),
            discount_amount=float(row["discount_amount"] if "discount_amount" in row.keys() else 0),
            transaction_id=row["transaction_id"] if "transaction_id" in row.keys() else "",
            approved_at=row["approved_at"] if "approved_at" in row.keys() else "",
            cancelled_at=row["cancelled_at"] if "cancelled_at" in row.keys() else "",
            shipping_method=row["shipping_method"] or "",
            shipping_tracking_code=row["shipping_tracking_code"] or "",
            shipping_label_url=row["shipping_label_url"] or "",
            shipping_status=row["shipping_status"] or "pending",
            internal_notes=row["internal_notes"] or "",
            created_at=row["created_at"],
        )

    def to_dict(self):
        return {
            "id": self.id,
            "customer_name": self.customer_name,
            "customer_phone": self.customer_phone,
            "customer_address": self.customer_address,
            "customer_id": self.customer_id,
            "total": self.total,
            "status": self.status,
            "source": self.source,
            "external_order_id": self.external_order_id,
            "payment_status": self.payment_status,
            "payment_method": self.payment_method,
            "subtotal": self.subtotal,
            "shipping_amount": self.shipping_amount,
            "discount_amount": self.discount_amount,
            "transaction_id": self.transaction_id,
            "approved_at": self.approved_at,
            "cancelled_at": self.cancelled_at,
            "shipping_method": self.shipping_method,
            "shipping_tracking_code": self.shipping_tracking_code,
            "shipping_label_url": self.shipping_label_url,
            "shipping_status": self.shipping_status,
            "internal_notes": self.internal_notes,
            "created_at": self.created_at,
        }
