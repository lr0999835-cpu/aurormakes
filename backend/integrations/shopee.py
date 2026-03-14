"""Placeholder de integração Shopee.

Não realiza chamadas reais sem credenciais/API.
"""

from integrations.channels import ChannelService


class ShopeeService(ChannelService):
    def __init__(self, credentials=None):
        super().__init__(channel_name="shopee")
        self.credentials = credentials or {}

    def is_ready(self):
        required = ["partner_id", "shop_id", "access_token"]
        return all(self.credentials.get(key) for key in required)

    def import_orders(self):
        if not self.is_ready():
            return []
        return []
