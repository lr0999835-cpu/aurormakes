function removeFromCart(productId) { removeProductFromCart(productId); updateCartCount(); renderCartPage(); }
function increaseCartQuantity(productId) { changeProductQuantity(productId, 1); updateCartCount(); renderCartPage(); }
function decreaseCartQuantity(productId) { changeProductQuantity(productId, -1); updateCartCount(); renderCartPage(); }

function buildPaymentInstructions(order) {
  const payment = order.payment || {};
  if (payment.payment_method === "pix") {
    return `Pedido #${order.id} criado!\n\nPIX copia e cola:\n${payment.pix_copy_paste || "Aguardando geração"}`;
  }
  if (payment.payment_method === "boleto") {
    return `Pedido #${order.id} criado!\n\nLinha digitável:\n${payment.boleto_barcode || "Aguardando geração"}\n\nBoleto: ${payment.boleto_url || "indisponível"}`;
  }
  if (payment.payment_method === "cartao") {
    return payment.status === "aprovado" || payment.status === "pago"
      ? `Pagamento no cartão aprovado para o pedido #${order.id}.`
      : `Pagamento no cartão recusado para o pedido #${order.id}. Tente novamente com outro cartão.`;
  }
  return `Pedido #${order.id} criado com sucesso.`;
}

async function createOrderFromCart() {
  const detailedCart = getDetailedCartItems();
  if (!detailedCart.length) throw new Error("Seu carrinho está vazio");

  const customer_name = document.getElementById("checkout-name")?.value?.trim();
  const customer_phone = document.getElementById("checkout-phone")?.value?.trim();
  const customer_address = document.getElementById("checkout-address")?.value?.trim();
  const payment_method = document.getElementById("checkout-payment-method")?.value || "pix";

  if (!customer_name || !customer_phone || !customer_address) {
    throw new Error("Preencha nome, telefone e endereço para continuar.");
  }

  const payload = {
    customer_name,
    customer_phone,
    customer_address,
    source: "aurora_makes",
    payment_method,
    items: detailedCart.map((item) => ({ product_id: item.id, quantity: item.quantidade })),
  };

  const response = await fetch("/api/checkout", {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-Device-Type": window.matchMedia("(max-width: 768px)").matches ? "mobile" : "desktop" },
    body: JSON.stringify(payload),
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "Erro ao criar pedido");

  saveCart([]); updateCartCount(); renderCartPage();
  return data;
}

async function checkoutNow() {
  try {
    const order = await createOrderFromCart();
    alert(buildPaymentInstructions(order));
    const instructions = document.getElementById("checkout-instructions");
    if (instructions) instructions.textContent = buildPaymentInstructions(order);
  } catch (error) { alert(error.message || "Não foi possível finalizar o pedido."); }
}

function renderCartPage() {
  const cartContainer = document.getElementById("cart-content");
  if (!cartContainer) return;
  const detailedCart = getDetailedCartItems();
  if (!detailedCart.length) {
    cartContainer.innerHTML = `<div class="empty-box"><p>Seu carrinho está vazio</p><a class="btn" href="produtos.html">Ir para produtos</a></div>`;
    return;
  }
  const subtotal = calculateCartTotal();
  const shipping = 0;
  const discount = 0;
  const total = subtotal + shipping - discount;

  cartContainer.innerHTML = `
    <div class="cart-list">${detailedCart.map((item) => `
      <article class="cart-item">
        <img src="${item.imagem}" alt="${item.nome}">
        <div>
          <h3>${item.nome}</h3><p>Quantidade: ${item.quantidade}</p><p>Preço unitário: ${formatPrice(item.preco)}</p>
          <p>Total do item: <strong>${formatPrice(item.subtotal)}</strong></p>
          <div class="cart-item-controls">
            <button class="qty-btn" type="button" onclick="decreaseCartQuantity(${item.id})">-</button>
            <button class="qty-btn" type="button" onclick="increaseCartQuantity(${item.id})">+</button>
            <button class="remove-btn" type="button" onclick="removeFromCart(${item.id})">Remover</button>
          </div>
        </div>
      </article>`).join("")}</div>

    <div class="checkout-box">
      <p><strong>Subtotal:</strong> ${formatPrice(subtotal)}</p>
      <p><strong>Frete:</strong> ${formatPrice(shipping)}</p>
      <p><strong>Desconto:</strong> ${formatPrice(discount)}</p>
      <p><strong>Total final:</strong> ${formatPrice(total)}</p>
      <input id="checkout-name" placeholder="Nome completo" />
      <input id="checkout-phone" placeholder="Telefone" />
      <input id="checkout-address" placeholder="Endereço de entrega" />
      <select id="checkout-payment-method">
        <option value="pix">PIX</option>
        <option value="cartao">Cartão de crédito</option>
        <option value="boleto">Boleto bancário</option>
      </select>
      <button class="checkout-btn" type="button" onclick="checkoutNow()">Confirmar pedido e pagar</button>
      <pre id="checkout-instructions" style="white-space:pre-wrap;font-size:.85rem;"></pre>
    </div>`;
}

window.renderCartPage = renderCartPage;
window.removeFromCart = removeFromCart;
window.increaseCartQuantity = increaseCartQuantity;
window.decreaseCartQuantity = decreaseCartQuantity;
window.checkoutNow = checkoutNow;
