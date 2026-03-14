# Instruções de override para Loja Integrada

1. No painel da Loja Integrada, abra **Minha Loja > Temas > Editar código**.
2. Faça backup dos arquivos atuais de layout da home e CSS do tema.
3. Substitua/mescle o markup da página inicial com o conteúdo de `backend/templates/store/index.html`.
4. Copie os estilos de `css/style.css` para o CSS customizado do tema (ou arquivo principal `theme.css`).
5. Inclua o script `js/storefront.js` no rodapé da home, depois de `js/main.js`.
6. Preserve os IDs já usados pela lógica de carrinho/produtos:
   - `cart-count`
   - `home-products`
7. Não altere rotas de checkout/carrinho/pedidos. A customização entregue atua somente na camada visual.
8. Publicar e validar em desktop e mobile.
