# Aurora Makes

Aurora Makes roda como **loja + operação via Flask + SQLite**, agora preparada para operação **multicanal**.

## O que mudou nesta etapa (multicanal ready)
- Pedidos agora suportam origem (`aurora_makes`, `shopee`, `marketplace`, `manual`) e campos de pagamento/envio.
- Produtos agora possuem identificação interna (`sku`, `barcode`, `supplier_reference`).
- Novo mapeamento de produto por canal em `product_channels`.
- Estoque continua central por produto, mas movimentações agora registram `source` e `reference_id`.
- Admin ganhou:
  - filtros por origem/status em pedidos
  - detalhes completos do pedido
  - rota de impressão operacional (`/admin/orders/<id>/print`)
  - tela de canais (`/admin/channels`)
  - tela de integrações (`/admin/integrations`)
  - histórico de movimentações de estoque no painel
  - dashboard com métricas por origem
- Arquitetura pronta para integração futura real em `backend/integrations/`.

## Requisitos
- Python 3.10+
- pip

## Como rodar localmente (porta 5000)
```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
pip install -r requirements.txt
python backend/app.py
```

Acesse:
- Loja: `http://127.0.0.1:5000/`
- Admin dashboard: `http://127.0.0.1:5000/admin/dashboard`
- Admin pedidos: `http://127.0.0.1:5000/admin/orders`
- Admin estoque: `http://127.0.0.1:5000/admin/stock`
- Admin produtos: `http://127.0.0.1:5000/admin/products`
- Admin canais: `http://127.0.0.1:5000/admin/channels`
- Admin integrações: `http://127.0.0.1:5000/admin/integrations`

## Estrutura de dados (SQLite)
### Novos campos em `orders`
- `source`
- `external_order_id`
- `payment_status`
- `payment_method`
- `shipping_method`
- `shipping_tracking_code`
- `shipping_label_url`
- `shipping_status`
- `internal_notes`

### Novos campos em `products`
- `sku`
- `barcode`
- `supplier_reference`

### Novos campos em `stock_movements`
- `source`
- `reference_id`

### Nova tabela
`product_channels`
- `id`
- `product_id`
- `channel_name`
- `external_product_id`
- `external_sku`
- `is_active`
- `created_at`

## API operacional
- `POST /api/orders` cria pedido e aceita dados de origem/pagamento/envio.
- `GET /api/orders` lista pedidos.
- `PUT /api/orders/<id>/status` atualiza status operacional.
- `GET /api/dashboard` retorna métricas (incluindo por origem).
- `GET /api/stock/low` retorna alerta de baixo estoque.
- `GET /api/products` lista produtos da vitrine.

## Integrações futuras
Este projeto **não simula integração Shopee sem credenciais reais**.

Foram adicionados placeholders:
- `backend/integrations/channels.py`
- `backend/integrations/shopee.py`

Esses serviços servem como base para:
- importação de pedidos externos
- sincronização de produtos
- sincronização de estoque

## Fluxo multicanal
1. Pedido entra com uma `source`.
2. O estoque central é reduzido igualmente, independente da origem.
3. A baixa gera `stock_movements` com `source` e `reference_id`.
4. O admin acompanha pedido, pagamento, envio e impressão operacional.
5. Produtos podem ser vinculados às listagens externas em `/admin/channels`.
