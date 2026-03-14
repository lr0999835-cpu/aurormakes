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
    lines.push(
      `• ${item.nome} | Quantidade: ${item.quantidade} | Preço: ${formatPrice(item.preco)} | Subtotal: ${formatPrice(item.subtotal)}`
    );
  });

  lines.push("");
  lines.push(`Total: ${formatPrice(total)}`);

  return encodeURIComponent(lines.join("\n"));
}

function checkoutByWhatsApp() {
  const detailedCart = getDetailedCartItems();

  if (detailedCart.length === 0) {
    alert("Seu carrinho está vazio");
    return;
  }

  const total = detailedCart.reduce((sum, item) => sum + item.subtotal, 0);
  const mensagem = createWhatsAppMessage(detailedCart, total);

  window.open(`https://wa.me/${WHATSAPP_NUMBER}?text=${mensagem}`, "_blank");
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

  const total = detailedCart.reduce((sum, item) => sum + item.subtotal, 0);

  cartContainer.innerHTML = `
    ${detailedCart
      .map(
        (item) => `
      <article class="cart-item">
        <img src="${item.imagem}" alt="${item.nome}">
        <div>
          <h3>${item.nome}</h3>
          <p>Quantidade: ${item.quantidade}</p>
          <p>Preço: ${formatPrice(item.preco)}</p>
          <div class="cart-item-controls">
            <button class="qty-btn" type="button" onclick="decreaseCartQuantity(${item.id})">-</button>
            <button class="qty-btn" type="button" onclick="increaseCartQuantity(${item.id})">+</button>
            <button class="remove-btn" type="button" onclick="removeFromCart(${item.id})">Remover</button>
          </div>
        </div>
        <strong>${formatPrice(item.subtotal)}</strong>
      </article>
    `
      )
      .join("")}

    <div class="checkout-box">
      <p><strong>Total:</strong> ${formatPrice(total)}</p>
      <button class="checkout-btn" type="button" onclick="checkoutByWhatsApp()">Finalizar pedido no WhatsApp</button>
    </div>
  `;
}

window.renderCartPage = renderCartPage;
window.removeFromCart = removeFromCart;
window.increaseCartQuantity = increaseCartQuantity;
window.decreaseCartQuantity = decreaseCartQuantity;
window.checkoutByWhatsApp = checkoutByWhatsApp;
