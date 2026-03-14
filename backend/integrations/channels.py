"""Serviços base para operação multicanal.

Este módulo define interfaces simples para futuras integrações reais.
"""


class ChannelService:
    def __init__(self, channel_name):
        self.channel_name = channel_name

    def import_orders(self):
        """Futuro: importar pedidos de marketplace para a tabela orders."""
        return []

    def sync_products(self):
        """Futuro: sincronizar produtos internos com o canal externo."""
        return []

    def sync_stock(self):
        """Futuro: enviar estoque central para o canal externo."""
        return []
