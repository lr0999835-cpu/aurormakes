function removeFromCart(productId) {
  removeProductFromCart(productId);
  updateCartCount();
  renderCartPage();
}

function increaseCartQuantity(productId) {
  changeProductQuantity(productId, 1);
  updateCartCount();
  renderCartPage();
}

function decreaseCartQuantity(productId) {
  changeProductQuantity(productId, -1);
  updateCartCount();
  renderCartPage();
}

function createWhatsAppMessage(cartItems, total) {
  const lines = ["Olá! Quero finalizar meu pedido na Aurora Makes:", ""];

  cartItems.forEach((item) => {
    lines.push(`• Produto: ${item.nome}`);
    lines.push(`  Quantidade: ${item.quantidade}`);
    lines.push(`  Preço unitário: ${formatPrice(item.preco)}`);
    lines.push(`  Total do item: ${formatPrice(item.subtotal)}`);
    lines.push("");
  });

  lines.push(`Total do pedido: ${formatPrice(total)}`);

  return encodeURIComponent(lines.join("\n"));
}

function checkoutByWhatsApp() {
  const detailedCart = getDetailedCartItems();

  if (detailedCart.length === 0) {
    alert("Seu carrinho está vazio");
    return;
  }

  const total = calculateCartTotal();
  const mensagem = createWhatsAppMessage(detailedCart, total);

  window.open(`${WHATSAPP_URL}?text=${mensagem}`, "_blank");
}

function renderCartPage() {
  const cartContainer = document.getElementById("cart-content");

  if (!cartContainer) {
    return;
  }

  const detailedCart = getDetailedCartItems();

  if (detailedCart.length === 0) {
    cartContainer.innerHTML = `
      <div class="empty-box">
        <p>Seu carrinho está vazio</p>
        <a class="btn" href="produtos.html">Ir para produtos</a>
      </div>
    `;
    return;
  }

  const total = calculateCartTotal();

  cartContainer.innerHTML = `
    <div class="cart-list">
      ${detailedCart
        .map(
          (item) => `
        <article class="cart-item">
          <img src="${item.imagem}" alt="${item.nome}">
          <div>
            <h3>${item.nome}</h3>
            <p>Quantidade: ${item.quantidade}</p>
            <p>Preço unitário: ${formatPrice(item.preco)}</p>
            <p>Total do item: <strong>${formatPrice(item.subtotal)}</strong></p>
            <div class="cart-item-controls">
              <button class="qty-btn" type="button" onclick="decreaseCartQuantity(${item.id})">-</button>
              <button class="qty-btn" type="button" onclick="increaseCartQuantity(${item.id})">+</button>
              <button class="remove-btn" type="button" onclick="removeFromCart(${item.id})">Remover</button>
            </div>
          </div>
        </article>
      `
        )
        .join("")}
    </div>

    <div class="checkout-box">
      <p><strong>Total do pedido:</strong> ${formatPrice(total)}</p>
      <button class="checkout-btn" type="button" onclick="checkoutByWhatsApp()">Finalizar pedido no WhatsApp</button>
    </div>
  `;
}

window.renderCartPage = renderCartPage;
window.removeFromCart = removeFromCart;
window.increaseCartQuantity = increaseCartQuantity;
window.decreaseCartQuantity = decreaseCartQuantity;
window.checkoutByWhatsApp = checkoutByWhatsApp;
