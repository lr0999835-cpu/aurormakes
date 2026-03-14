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

function createWhatsAppMessage(order) {
  const lines = [
    "Olá! Quero finalizar meu pedido na Aurora Makes:",
    `Pedido #${order.id}`,
    ""
  ];

  order.items.forEach((item) => {
    lines.push(`• Produto: ${item.product_name}`);
    lines.push(`  Quantidade: ${item.quantity}`);
    lines.push(`  Preço unitário: ${formatPrice(item.price)}`);
    lines.push("");
  });

  lines.push(`Total do pedido: ${formatPrice(order.total)}`);
  return encodeURIComponent(lines.join("\n"));
}

async function createOrderFromCart() {
  const detailedCart = getDetailedCartItems();
  if (detailedCart.length === 0) {
    alert("Seu carrinho está vazio");
    return null;
  }

  const customer_name = window.prompt("Digite seu nome:");
  const customer_phone = window.prompt("Digite seu telefone:");
  const customer_address = window.prompt("Digite seu endereço para entrega:");

  if (!customer_name || !customer_phone || !customer_address) {
    alert("Preencha nome, telefone e endereço para criar o pedido.");
    return null;
  }

  const payload = {
    customer_name,
    customer_phone,
    customer_address,
    items: detailedCart.map((item) => ({
      product_id: item.id,
      quantity: item.quantidade
    }))
  };

  const response = await fetch("/api/orders", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.error || "Erro ao criar pedido");
  }

  saveCart([]);
  updateCartCount();
  renderCartPage();
  return data;
}

async function checkoutByWhatsApp() {
  try {
    const order = await createOrderFromCart();
    if (!order) {
      return;
    }

    const mensagem = createWhatsAppMessage(order);
    window.open(`https://wa.me/5521974803694?text=${mensagem}`, "_blank");
  } catch (error) {
    alert(error.message || "Não foi possível finalizar o pedido.");
  }
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
      <button class="checkout-btn" type="button" onclick="checkoutByWhatsApp()">Criar pedido e finalizar no WhatsApp</button>
    </div>
  `;
}

window.renderCartPage = renderCartPage;
window.removeFromCart = removeFromCart;
window.increaseCartQuantity = increaseCartQuantity;
window.decreaseCartQuantity = decreaseCartQuantity;
window.checkoutByWhatsApp = checkoutByWhatsApp;
