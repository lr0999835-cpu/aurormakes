# Premium storefront architecture plan (Loja Integrada-safe)

## 1) Frontend architecture plan
- A customização foi mantida na camada de **apresentação da vitrine** (home/header/nav/footer + estilos + JS progressivo).
- IDs nativos usados por lógica de carrinho/vitrine foram preservados: `cart-count` e `home-products`.
- Nenhuma rota, endpoint, fluxo de checkout/pagamento/pedidos foi alterado.
- O mega menu foi implementado como componente isolado (`.mega-item`, `.mega-dropdown`) sem mexer em loops dinâmicos da plataforma.
- O render de produtos continua centralizado no JS existente (`js/main.js`), com atualização apenas textual da linha de urgência.

## 2) File structure
- `backend/templates/store/index.html`: estrutura premium da home para integração com tema.
- `index.html`: espelho da home para preview local.
- `css/style.css`: design system (tokens), header, mega menu, hero, categorias, shelf e footer.
- `js/storefront.js`: interações progressivas (hero slider, mega menu, drawer mobile e carrosséis).
- `js/main.js`: mantém lógica de catálogo/carrinho; ajusta linha de urgência no card.
- `docs/loja-integrada-theme-override.md`: passo a passo de injeção segura no tema.

## 3) HTML / 4) CSS / 5) JS
Implementação completa entregue diretamente em:
- HTML: `backend/templates/store/index.html`
- CSS: `css/style.css`
- JS: `js/storefront.js`

## 6) Theme integration notes
1. Injetar o HTML da home usando `backend/templates/store/index.html`.
2. Injetar CSS consolidado de `css/style.css` no arquivo de estilo do tema.
3. Carregar scripts na ordem: `js/produtos.js`, `js/main.js`, `js/storefront.js`.
4. Preservar IDs nativos (`cart-count`, `home-products`) e links de carrinho/conta.
5. Não substituir templates de checkout, pagamento, pedidos e conta.

## 7) Safety checklist
- [x] Checkout intacto (não modificado).
- [x] Pagamento intacto (não modificado).
- [x] Conta/login intactos (apenas botões visuais no header).
- [x] Fluxo de pedidos intacto (sem alteração de API/rotas).
- [x] Lógica de listagem/carrinho preservada (integração dinâmica mantida).
