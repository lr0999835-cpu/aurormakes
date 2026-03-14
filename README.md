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


## Gestão de acesso (multiempresa)
### Funcionalidades
- Gestão de empresas: criar, editar, ativar/desativar em `/admin/empresas` (somente `super_admin`).
- Gestão de usuários: criar, editar, ativar/desativar, resetar senha e vincular à empresa em `/admin/usuarios`.
- Gestão de papéis/permissões em `/admin/permissoes`.
- Regras de isolamento por tenant aplicadas no backend:
  - `super_admin` gerencia todas as empresas.
  - `company_admin` gerencia usuários apenas da própria empresa.
  - usuários de empresa não conseguem operar em outra empresa.
- Senhas armazenadas com hash (`werkzeug.security.generate_password_hash`).

### Roles suportadas
- `super_admin`
- `company_admin`
- `operator`
- `viewer`


### Credenciais administrativas padrão
Após subir a aplicação (ou executar o bootstrap), estas credenciais são garantidas no banco:
- `company`: `aurora-makes`
- `email`: `admin@auroramakes.com`
- `password`: `admin123`
- `permission`: `super_admin`

> Observação: se o usuário já existir, a senha é resetada para `admin123` durante `init_db`.

### Seed / bootstrap
Na inicialização (`init_db`) o sistema cria automaticamente:
- empresa padrão `Aurora Makes` (`slug=aurora-makes`)
- usuário admin padrão para a empresa

Para provisionamento seguro e idempotente do primeiro super administrador, use:
```bash
python backend/scripts/bootstrap_super_admin.py
```

Esse comando garante que:
- a empresa `Aurora Makes` (`aurora-makes`) exista e esteja ativa;
- o usuário `admin@auroramakes.com` exista na empresa correta;
- o usuário esteja `active` e com role `super_admin`;
- a senha informada no script seja armazenada com hash (`werkzeug.security.generate_password_hash`).

Para preservar o hash existente (sem resetar senha), execute:
```bash
python backend/scripts/bootstrap_super_admin.py --no-reset-password
```


### Como criar novos usuários no futuro
Use o painel em `/admin/usuarios` com um usuário que tenha permissão `users:write` (`company_admin` ou `super_admin`):
1. Selecione a empresa (`company_id`) alvo.
2. Informe `username`, `email`, `password` e `role`.
3. O backend salva a senha com hash via `werkzeug.security.generate_password_hash`.

Também é possível criar via SQL/seed preenchendo `users.company_id`, `users.email`, `users.role` e `users.password_hash` (nunca salvar senha em texto puro).
