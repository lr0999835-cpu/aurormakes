# Aurora Makes

Aurora Makes agora roda com **frontend estático + backend Flask + SQLite**.

## Requisitos
- Python 3.10+
- pip

## Como rodar localmente
```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
pip install -r requirements.txt
python backend/app.py
```

Acesse:
- Loja: `http://localhost:5000/`
- Produtos: `http://localhost:5000/produtos.html`
- Carrinho: `http://localhost:5000/carrinho.html`
- Admin produtos: `http://localhost:5000/admin/products`
- Admin estoque: `http://localhost:5000/admin/stock`

## Estrutura principal
- `backend/app.py`: inicialização Flask e rotas principais
- `backend/database.py`: conexão e criação da tabela SQLite
- `backend/services.py`: regras de negócio de produtos
- `backend/routes/products.py`: API REST `/api/products`
- `backend/routes/admin.py`: telas administrativas

## Deploy (Render, Railway, VPS)
Use comando de start:
```bash
python backend/app.py
```

Opcionalmente configure variáveis:
- `AURORA_DB_PATH` (caminho do banco SQLite)
- `FLASK_DEBUG` (`0` em produção)
- `SECRET_KEY`
