function removeFromCart(productId) {
  const cart = getCart().filter((item) => item.id !== Number(productId));
  saveCart(cart);
  renderCartPage();
  updateCartCount();
}

function updateCartQuantity(productId, amount) {
  const cart = getCart();
  const item = cart.find((cartItem) => cartItem.id === Number(productId));

  if (!item) {
    return;
  }

  item.quantidade += amount;

  if (item.quantidade <= 0) {
    removeFromCart(productId);
    return;
  }

  saveCart(cart);
  renderCartPage();
  updateCartCount();
}

function createWhatsAppMessage(cartItems, total) {
  const lines = ["Olá! Quero finalizar meu pedido na Aurora Makes:", ""];

  cartItems.forEach((item) => {
    lines.push(`- ${item.nome} (x${item.quantidade}) - ${formatPrice(item.subtotal)}`);
  });

  lines.push("");
  lines.push(`Total do pedido: ${formatPrice(total)}`);

  return encodeURIComponent(lines.join("\n"));
}

function checkoutByWhatsApp() {
  const cart = getCart();

  if (cart.length === 0) {
    alert("Seu carrinho está vazio.");
    return;
  }

  const detailedCart = cart
    .map((item) => {
      const produto = findProductById(item.id);
      if (!produto) {
        return null;
      }

      return {
        ...produto,
        quantidade: item.quantidade,
        subtotal: produto.preco * item.quantidade
      };
    })
    .filter(Boolean);

  const total = detailedCart.reduce((sum, item) => sum + item.subtotal, 0);
  const mensagem = createWhatsAppMessage(detailedCart, total);

  window.open(`https://wa.me/${WHATSAPP_NUMBER}?text=${mensagem}`, "_blank");
}

function renderCartPage() {
  const cartContainer = document.getElementById("cart-content");

  if (!cartContainer) {
    return;
  }

  const cart = getCart();

  if (cart.length === 0) {
    cartContainer.innerHTML = `
      <div class="empty-box">
        <p>Seu carrinho está vazio no momento.</p>
        <a class="btn" href="produtos.html">Ir para produtos</a>
      </div>
    `;
    return;
  }

  const detailedCart = cart
    .map((item) => {
      const produto = findProductById(item.id);
      if (!produto) {
        return null;
      }

      return {
        ...produto,
        quantidade: item.quantidade,
        subtotal: produto.preco * item.quantidade
      };
    })
    .filter(Boolean);

  const total = detailedCart.reduce((sum, item) => sum + item.subtotal, 0);

  cartContainer.innerHTML = `
    ${detailedCart
      .map(
        (item) => `
      <article class="cart-item">
        <img src="${item.imagem}" alt="${item.nome}">
        <div>
          <h3>${item.nome}</h3>
          <p>${formatPrice(item.preco)} cada</p>
          <div class="cart-item-controls">
            <button class="qty-btn" onclick="updateCartQuantity(${item.id}, -1)">-</button>
            <strong>${item.quantidade}</strong>
            <button class="qty-btn" onclick="updateCartQuantity(${item.id}, 1)">+</button>
            <button class="remove-btn" onclick="removeFromCart(${item.id})">Remover</button>
          </div>
        </div>
        <strong>${formatPrice(item.subtotal)}</strong>
      </article>
    `
      )
      .join("")}

    <div class="checkout-box">
      <p><strong>Total:</strong> ${formatPrice(total)}</p>
      <button class="checkout-btn" onclick="checkoutByWhatsApp()">Finalizar pedido no WhatsApp</button>
    </div>
  `;
}

renderCartPage();
