# Aurora Makes

Aurora Makes agora roda como **loja única via Flask + SQLite**.

## O que mudou
- A vitrine da loja foi unificada no Flask (porta 5000).
- As páginas `/`, `/index.html`, `/produtos.html` e `/carrinho.html` são renderizadas pelo Flask.
- Produtos da loja vêm da API (`/api/products`) e banco SQLite.
- Carrinho continua em `localStorage` e checkout via WhatsApp continua ativo.
- Checkout agora cria pedido real no banco antes de abrir o WhatsApp.
- Camada operacional adicionada: pedidos, itens do pedido, movimentação de estoque, dashboard e páginas administrativas.

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
- Produtos: `http://127.0.0.1:5000/produtos.html`
- Carrinho: `http://127.0.0.1:5000/carrinho.html`
- Admin dashboard: `http://127.0.0.1:5000/admin/dashboard`
- Admin pedidos: `http://127.0.0.1:5000/admin/orders`
- Admin estoque: `http://127.0.0.1:5000/admin/stock`
- Admin produtos: `http://127.0.0.1:5000/admin/products`

> Não usar mais porta 5500 para a loja.

## API operacional
- `POST /api/orders` cria pedido a partir do carrinho.
- `GET /api/orders` lista pedidos.
- `PUT /api/orders/<id>/status` atualiza status.
- `GET /api/dashboard` métricas operacionais.
- `GET /api/stock/low` alerta de estoque baixo.
- `GET /api/products` produtos para a vitrine.

## Fluxo operacional
1. Cliente adiciona itens no carrinho.
2. Checkout cria pedido e itens do pedido no banco.
3. Estoque é baixado automaticamente e gera histórico em `stock_movements`.
4. Admin gerencia status do pedido e ajustes de estoque.
5. Dashboard mostra vendas, receita, lucro estimado, produtos vendidos e alertas.

## Estrutura principal
- `backend/app.py`: app Flask, rotas da loja e static assets
- `backend/database.py`: criação das tabelas SQLite
- `backend/services.py`: regras de produtos, pedidos, estoque e dashboard
- `backend/routes/products.py`: API de produtos
- `backend/routes/operations.py`: API operacional
- `backend/routes/admin.py`: painel admin (dashboard, pedidos, estoque, produtos)
- `backend/templates/store/*`: páginas da loja unificada
- `backend/templates/admin/*`: páginas administrativas
