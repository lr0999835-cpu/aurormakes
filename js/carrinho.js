const CHECKOUT_STATE = {
  step: 1,
  cep: "",
  selectedShippingId: "",
  shippingOptions: [],
  shippingLoading: false,
  shippingError: "",
  couponCode: "",
  discount: 0,
  paymentMethod: "pix",
  email: "",
  fullName: "",
  phone: "",
  address: "",
  number: "",
  complement: "",
  district: "",
  city: "",
  state: "",
  reference: "",
  receiveNews: false,
  cardName: "",
  cardNumber: "",
  cardExpiry: "",
  cardCvv: "",
  installments: "1",
  customerLoaded: false,
  customerLoggedIn: false,
  customerAddresses: [],
  selectedAddressId: "new"
};

const BRAZIL_TIMEZONE = "America/Sao_Paulo";
const PAYMENT_GATEWAY = "mercadopago";
let PAYMENT_CONFIG = { gateway: PAYMENT_GATEWAY, mercado_pago_public_key: "", checkout_login_required: false };
let MERCADO_PAGO_CLIENT = null;



async function loadPaymentConfig() {
  try {
    const response = await fetch('/api/payments/config');
    const data = await response.json();
    if (response.ok && data) {
      PAYMENT_CONFIG = data;
      if (window.MercadoPago && data.mercado_pago_public_key) {
        MERCADO_PAGO_CLIENT = new window.MercadoPago(data.mercado_pago_public_key, { locale: 'pt-BR' });
      }
    }
  } catch (_error) {
    PAYMENT_CONFIG = { gateway: PAYMENT_GATEWAY, mercado_pago_public_key: '' };
  }
}

async function buildCardToken() {
  if (CHECKOUT_STATE.paymentMethod !== 'cartao') return null;
  if (!MERCADO_PAGO_CLIENT) {
    throw new Error('Pagamento com cartão indisponível no momento. Configure MERCADO_PAGO_PUBLIC_KEY.');
  }

  const [expMonth, expYear] = CHECKOUT_STATE.cardExpiry.split('/');
  const payload = {
    cardNumber: CHECKOUT_STATE.cardNumber.replace(/\s/g, ''),
    cardholderName: CHECKOUT_STATE.cardName.trim(),
    cardExpirationMonth: expMonth,
    cardExpirationYear: expYear,
    securityCode: CHECKOUT_STATE.cardCvv,
    identificationType: 'CPF',
    identificationNumber: '00000000000'
  };
  const tokenData = await MERCADO_PAGO_CLIENT.createCardToken(payload);
  return {
    token: tokenData?.id || '',
    payment_method_id: tokenData?.payment_method_id || 'visa',
    installments: Number(CHECKOUT_STATE.installments || '1'),
    document_type: 'CPF',
    document_number: '00000000000'
  };
}

function removeFromCart(productId) { removeProductFromCart(productId); updateCartCount(); renderCartPage(); }
function increaseCartQuantity(productId) { changeProductQuantity(productId, 1); updateCartCount(); renderCartPage(); }
function decreaseCartQuantity(productId) { changeProductQuantity(productId, -1); updateCartCount(); renderCartPage(); }

function getSelectedShipping() {
  return CHECKOUT_STATE.shippingOptions.find((option) => option.id === CHECKOUT_STATE.selectedShippingId) || null;
}

function getShippingPrice() {
  return getSelectedShipping()?.shipping_price || 0;
}

function calculateDiscount(subtotal) {
  const hasCoupon = CHECKOUT_STATE.couponCode.trim().toUpperCase() === "PRIMEIRA10";
  if (hasCoupon) {
    return subtotal * 0.1;
  }
  if (CHECKOUT_STATE.paymentMethod === "pix") {
    return subtotal * 0.05;
  }
  return 0;
}

function getOrderTotals() {
  const subtotal = calculateCartTotal();
  const shipping = getShippingPrice();
  const discount = calculateDiscount(subtotal);
  const total = Math.max(0, subtotal + shipping - discount);
  return { subtotal, shipping, discount, total };
}

function normalizeCep(value) {
  return value.replace(/\D/g, "").slice(0, 8);
}

function formatCep(value) {
  const digits = normalizeCep(value);
  if (digits.length <= 5) return digits;
  return `${digits.slice(0, 5)}-${digits.slice(5)}`;
}

async function calculateShippingByCep() {
  const cep = normalizeCep(CHECKOUT_STATE.cep);
  if (cep.length !== 8) {
    alert("Informe um CEP válido com 8 números.");
    return;
  }

  CHECKOUT_STATE.cep = formatCep(cep);
  CHECKOUT_STATE.shippingLoading = true;
  CHECKOUT_STATE.shippingError = "";
  renderCartPage();

  try {
    const { subtotal } = getOrderTotals();
    const detailedCart = getDetailedCartItems();
    const response = await fetch("/api/shipping/quotes", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        cep,
        subtotal,
        items: detailedCart.map((item) => ({ product_id: item.id, quantity: item.quantidade }))
      })
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data?.error || "Não foi possível calcular o frete.");
    }

    CHECKOUT_STATE.shippingOptions = Array.isArray(data.quotes) ? data.quotes : [];
    if (!CHECKOUT_STATE.shippingOptions.length) {
      throw new Error("Nenhum método de envio disponível para este CEP.");
    }
    const stillExists = CHECKOUT_STATE.shippingOptions.some((option) => option.id === CHECKOUT_STATE.selectedShippingId);
    CHECKOUT_STATE.selectedShippingId = stillExists
      ? CHECKOUT_STATE.selectedShippingId
      : CHECKOUT_STATE.shippingOptions[0].id;
  } catch (error) {
    CHECKOUT_STATE.shippingOptions = [];
    CHECKOUT_STATE.selectedShippingId = "";
    CHECKOUT_STATE.shippingError = error.message || "Não foi possível calcular o frete.";
  } finally {
    CHECKOUT_STATE.shippingLoading = false;
    renderCartPage();
  }
}

function moveToStep(nextStep) {
  CHECKOUT_STATE.step = Math.min(7, Math.max(1, nextStep));
  renderCartPage();
}

function handleCheckoutInput(field, value, type = "text") {
  const normalized = type === "checkbox" ? Boolean(value) : value;
  if (field === "cep") {
    CHECKOUT_STATE[field] = formatCep(normalized);
    return;
  }
  CHECKOUT_STATE[field] = normalized;
}

function handleShippingSelection(id) {
  CHECKOUT_STATE.selectedShippingId = id;
  renderCartPage();
}

function handlePaymentSelection(paymentMethod) {
  CHECKOUT_STATE.paymentMethod = paymentMethod;
  if (paymentMethod !== "cartao") {
    CHECKOUT_STATE.cardName = "";
    CHECKOUT_STATE.cardNumber = "";
    CHECKOUT_STATE.cardExpiry = "";
    CHECKOUT_STATE.cardCvv = "";
    CHECKOUT_STATE.installments = "1";
  }
  renderCartPage();
}

function formatCardNumber(value) {
  const digits = String(value || "").replace(/\D/g, "").slice(0, 16);
  return digits.replace(/(.{4})/g, "$1 ").trim();
}

function formatCardExpiry(value) {
  const digits = String(value || "").replace(/\D/g, "").slice(0, 4);
  if (digits.length <= 2) return digits;
  return `${digits.slice(0, 2)}/${digits.slice(2)}`;
}

function formatCardCvv(value) {
  return String(value || "").replace(/\D/g, "").slice(0, 4);
}

function buildPaymentPayload(totals) {
  const now = new Date().toLocaleString("sv-SE", { timeZone: BRAZIL_TIMEZONE }).replace(" ", "T");
  const payload = {
    payment_method: CHECKOUT_STATE.paymentMethod,
    payment_status: "pendente",
    payment_amount: totals.total,
    payment_gateway: PAYMENT_GATEWAY,
    transaction_id: "",
    payment_payload: {
      timezone: BRAZIL_TIMEZONE,
      customer_message: "Pagamento aguardando confirmação.",
    },
    created_at: now,
    updated_at: now,
  };

  if (CHECKOUT_STATE.paymentMethod === "pix") {
    payload.payment_payload.pix = {
      qr_code: "",
      copy_paste: "",
      discount_amount: totals.discount,
      confirmation_message: "Após confirmar o pedido, você verá o QR Code e o código Copia e Cola.",
    };
  }

  if (!["pix", "cartao", "boleto"].includes(CHECKOUT_STATE.paymentMethod)) {
    throw new Error("Selecione uma forma de pagamento válida para continuar.");
  }

  if (CHECKOUT_STATE.paymentMethod === "cartao") {
    payload.payment_payload.card = {
      holder_name: CHECKOUT_STATE.cardName.trim(),
      masked_number: formatCardNumber(CHECKOUT_STATE.cardNumber).replace(/\d(?=\d{4})/g, "•"),
      expiry: CHECKOUT_STATE.cardExpiry,
      installments: Number(CHECKOUT_STATE.installments || "1"),
    };
  }

  if (CHECKOUT_STATE.paymentMethod === "boleto") {
    payload.payment_payload.boleto = {
      barcode: "",
      boleto_url: "",
      instructions: "Boleto será gerado após confirmação e pode levar até 2 dias úteis para compensar.",
    };
  }

  return payload;
}

function applyCoupon() {
  CHECKOUT_STATE.couponCode = (document.getElementById("coupon-input")?.value || "").trim();
  renderCartPage();
}

function applyAddressData(address) {
  if (!address) {
    return;
  }

  CHECKOUT_STATE.cep = formatCep(address.cep || "");
  CHECKOUT_STATE.address = address.endereco || "";
  CHECKOUT_STATE.number = address.numero || "";
  CHECKOUT_STATE.complement = address.complemento || "";
  CHECKOUT_STATE.district = address.bairro || "";
  CHECKOUT_STATE.city = address.cidade || "";
  CHECKOUT_STATE.state = (address.estado || "").toUpperCase();
  CHECKOUT_STATE.reference = address.referencia || "";
}

function handleAddressSelection(addressId) {
  CHECKOUT_STATE.selectedAddressId = addressId;
  if (addressId === "new") {
    CHECKOUT_STATE.address = "";
    CHECKOUT_STATE.number = "";
    CHECKOUT_STATE.complement = "";
    CHECKOUT_STATE.district = "";
    CHECKOUT_STATE.city = "";
    CHECKOUT_STATE.state = "";
    CHECKOUT_STATE.reference = "";
    CHECKOUT_STATE.cep = "";
    CHECKOUT_STATE.shippingOptions = [];
    CHECKOUT_STATE.selectedShippingId = "";
    CHECKOUT_STATE.shippingError = "";
    renderCartPage();
    return;
  }

  const selected = CHECKOUT_STATE.customerAddresses.find((address) => String(address.id) === String(addressId));
  if (!selected) {
    renderCartPage();
    return;
  }

  applyAddressData(selected);
  CHECKOUT_STATE.shippingOptions = [];
  CHECKOUT_STATE.selectedShippingId = "";
  CHECKOUT_STATE.shippingError = "";
  renderCartPage();
}

function getCustomerAddressData() {
  return {
    cep: normalizeCep(CHECKOUT_STATE.cep),
    street: CHECKOUT_STATE.address.trim(),
    number: CHECKOUT_STATE.number.trim(),
    complement: CHECKOUT_STATE.complement.trim(),
    district: CHECKOUT_STATE.district.trim(),
    city: CHECKOUT_STATE.city.trim(),
    state: CHECKOUT_STATE.state.trim().toUpperCase(),
    reference: CHECKOUT_STATE.reference.trim()
  };
}

function formatAddressPayload() {
  const parts = [
    `${CHECKOUT_STATE.address}, ${CHECKOUT_STATE.number}`,
    CHECKOUT_STATE.complement,
    CHECKOUT_STATE.district,
    `${CHECKOUT_STATE.city} - ${CHECKOUT_STATE.state}`,
    `CEP ${CHECKOUT_STATE.cep}`,
    CHECKOUT_STATE.reference ? `Referência: ${CHECKOUT_STATE.reference}` : ""
  ].filter(Boolean);
  return parts.join(" | ");
}

function isValidEmail(value) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(String(value || "").trim());
}

function validateBeforeStep(step) {
  if (step >= 2) {
    const hasContact = CHECKOUT_STATE.email && CHECKOUT_STATE.fullName && CHECKOUT_STATE.phone;
    if (!hasContact) {
      alert("Preencha e-mail, nome completo e telefone para continuar.");
      return false;
    }

    if (!isValidEmail(CHECKOUT_STATE.email)) {
      alert("Informe um e-mail válido para continuar.");
      return false;
    }

    if (String(CHECKOUT_STATE.phone || "").replace(/\D/g, "").length < 10) {
      alert("Informe um telefone válido com DDD.");
      return false;
    }
  }

  if (step >= 3 && CHECKOUT_STATE.paymentMethod === "cartao") {
    const validCard = CHECKOUT_STATE.cardName.trim() && CHECKOUT_STATE.cardNumber.replace(/\D/g, "").length >= 13 && CHECKOUT_STATE.cardExpiry.length === 5 && CHECKOUT_STATE.cardCvv.length >= 3;
    if (!validCard) {
      alert("Preencha os dados do cartão para continuar com o pagamento.");
      return false;
    }
  }

  if (step >= 3) {
    const hasAddress = CHECKOUT_STATE.cep && CHECKOUT_STATE.address && CHECKOUT_STATE.number && CHECKOUT_STATE.district && CHECKOUT_STATE.city && CHECKOUT_STATE.state;
    if (!hasAddress) {
      alert("Preencha os dados de entrega para avançar ao pagamento.");
      return false;
    }

    if (normalizeCep(CHECKOUT_STATE.cep).length !== 8) {
      alert("Informe um CEP válido no formato 00000-000.");
      return false;
    }

    if (!CHECKOUT_STATE.selectedShippingId) {
      alert("Selecione um método de frete.");
      return false;
    }
  }

  return true;
}

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

  if (!validateBeforeStep(3)) {
    throw new Error("Preencha os dados obrigatórios para finalizar.");
  }

  const { subtotal, shipping, discount } = getOrderTotals();
  const selectedShipping = getSelectedShipping();
  const payment = buildPaymentPayload({ subtotal, shipping, discount, total: Math.max(0, subtotal + shipping - discount) });

  const payload = {
    customer_id: CHECKOUT_STATE.customerLoggedIn ? Number((window.__CUSTOMER_SESSION__ && window.__CUSTOMER_SESSION__.customer && window.__CUSTOMER_SESSION__.customer.id) || 0) || undefined : undefined,
    customer_name: CHECKOUT_STATE.fullName.trim(),
    customer_phone: CHECKOUT_STATE.phone.trim(),
    customer_email: CHECKOUT_STATE.email.trim(),
    customer_address: formatAddressPayload(),
    source: "aurora_makes",
    payment_method: CHECKOUT_STATE.paymentMethod,
    subtotal,
    shipping_amount: shipping,
    discount_amount: discount,
    shipping_method: selectedShipping?.method_code || selectedShipping?.method_name || "",
    shipping_quote_id: selectedShipping?.id || "",
    shipping_eta: selectedShipping?.shipping_eta || "",
    shipping_label: selectedShipping?.shipping_label || selectedShipping?.method_name || "",
    customer_address_data: getCustomerAddressData(),
    payment,
    items: detailedCart.map((item) => ({
      product_id: item.id,
      quantity: item.quantidade
    }))
  };

  if (!["pix", "cartao", "boleto"].includes(CHECKOUT_STATE.paymentMethod)) {
    throw new Error("Selecione uma forma de pagamento válida para continuar.");
  }

  if (CHECKOUT_STATE.paymentMethod === "cartao") {
    payload.card = await buildCardToken();
  }

  const response = await fetch("/api/checkout", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });

  const data = await response.json();
  if (!response.ok) {
    throw new Error(data?.error || "Não foi possível finalizar o pedido");
  }

  return data;
}

async function checkoutNow() {
  try {
    const order = await createOrderFromCart();
    saveCart([]);
    updateCartCount();
    CHECKOUT_STATE.step = 7;
    renderCartPage();
    const instructions = document.getElementById("checkout-instructions");
    if (instructions) instructions.textContent = buildPaymentInstructions(order);
  } catch (error) {
    alert(error.message || "Não foi possível finalizar o pedido.");
  }
}

function renderStepIndicator() {
  const labels = ["Carrinho", "Contato", "Entrega", "Frete", "Pagamento", "Confirmação", "Pagamento"];
  return `<ol class="checkout-steps">${labels.map((label, index) => {
    const stepNumber = index + 1;
    const stateClass = CHECKOUT_STATE.step === stepNumber ? "is-active" : CHECKOUT_STATE.step > stepNumber ? "is-done" : "";
    return `<li class="${stateClass}"><span>${stepNumber}</span><strong>${label}</strong></li>`;
  }).join("")}</ol>`;
}

function renderShippingOptions() {
  if (CHECKOUT_STATE.shippingLoading) {
    return '<p class="checkout-hint">Consultando opções de frete para o seu CEP...</p>';
  }

  if (CHECKOUT_STATE.shippingError) {
    return `<p class="checkout-hint">${CHECKOUT_STATE.shippingError}</p>`;
  }

  if (!CHECKOUT_STATE.shippingOptions.length) {
    return '<p class="checkout-hint">Informe o CEP e clique em <strong>Calcular frete</strong> para visualizar os métodos.</p>';
  }

  return `<div class="shipping-options">${CHECKOUT_STATE.shippingOptions.map((option) => `
    <label class="shipping-option ${CHECKOUT_STATE.selectedShippingId === option.id ? "selected" : ""}">
      <input type="radio" name="shipping-method" ${CHECKOUT_STATE.selectedShippingId === option.id ? "checked" : ""} onchange="handleShippingSelection('${option.id}')" />
      <div>
        <p><strong>${option.method_name}</strong> ${option.badge ? `<span class="badge">${option.badge}</span>` : ""}</p>
        <small>${option.shipping_eta || "Prazo sob consulta"}</small>
      </div>
      <strong>${formatPrice(option.shipping_price || 0)}</strong>
    </label>
  `).join("")}</div>`;
}

function renderCustomerAddressSelector() {
  if (!CHECKOUT_STATE.customerLoggedIn || !CHECKOUT_STATE.customerAddresses.length) {
    return "";
  }

  return `
    <div class="saved-address-box">
      <p>Endereços salvos</p>
      <select onchange="handleAddressSelection(this.value)">
        ${CHECKOUT_STATE.customerAddresses.map((address) => `<option value="${address.id}" ${String(CHECKOUT_STATE.selectedAddressId) === String(address.id) ? "selected" : ""}>${address.endereco}, ${address.numero} · ${address.bairro}</option>`).join("")}
        <option value="new" ${CHECKOUT_STATE.selectedAddressId === "new" ? "selected" : ""}>Cadastrar novo endereço</option>
      </select>
    </div>
  `;
}

function renderPaymentPanel() {
  const optionCard = (method, title, description) => `
    <label class="payment-option ${CHECKOUT_STATE.paymentMethod === method ? "selected" : ""}">
      <input type="radio" name="payment-method" ${CHECKOUT_STATE.paymentMethod === method ? "checked" : ""} onchange="handlePaymentSelection('${method}')" />
      <div class="payment-option-content">
        <strong>${title}</strong>
        <small>${description}</small>
      </div><span class="payment-chevron">›</span>
    </label>
  `;

  let dynamicPanel = '<p class="checkout-hint">Selecione a forma de pagamento para continuar.</p>';
  if (CHECKOUT_STATE.paymentMethod === "pix") {
    const totals = getOrderTotals();
    dynamicPanel = `<div class="payment-note payment-note-pix"><strong>Pagamento via PIX</strong><p>Após confirmar o pedido, exibiremos o QR Code e o código copia e cola para pagamento instantâneo.</p><div class="pix-preview"><div class="pix-qr-placeholder">QR Code do PIX</div><div><p><strong>Código Copia e Cola</strong></p><code>Será gerado após a confirmação do pedido.</code><p class="checkout-hint">Confirmação automática em poucos segundos após o pagamento.</p></div></div><p class="pix-discount-inline">Ou ${formatPrice(Math.max(0, totals.total - totals.subtotal * 0.05))} com Pix</p></div>`;
  }
  if (!["pix", "cartao", "boleto"].includes(CHECKOUT_STATE.paymentMethod)) {
    throw new Error("Selecione uma forma de pagamento válida para continuar.");
  }

  if (CHECKOUT_STATE.paymentMethod === "cartao") {
    dynamicPanel = `
      <div class="grid-2 payment-fields">
        <label>Nome no cartão<input value="${CHECKOUT_STATE.cardName}" oninput="handleCheckoutInput('cardName', this.value)"></label>
        <label>Número do cartão<input value="${CHECKOUT_STATE.cardNumber}" maxlength="19" inputmode="numeric" placeholder="0000 0000 0000 0000" oninput="handleCheckoutInput('cardNumber', formatCardNumber(this.value))"></label>
        <label>Validade (MM/AA)<input value="${CHECKOUT_STATE.cardExpiry}" maxlength="5" inputmode="numeric" placeholder="MM/AA" oninput="handleCheckoutInput('cardExpiry', formatCardExpiry(this.value))"></label>
        <label>CVV<input value="${CHECKOUT_STATE.cardCvv}" maxlength="4" inputmode="numeric" placeholder="000" oninput="handleCheckoutInput('cardCvv', formatCardCvv(this.value))"></label>
        <label>Parcelas
          <select onchange="handleCheckoutInput('installments', this.value)">
            ${[1, 2, 3, 4, 5, 6].map((installment) => `<option value="${installment}" ${CHECKOUT_STATE.installments === String(installment) ? "selected" : ""}>${installment}x ${installment === 1 ? "sem juros" : "no cartão"}</option>`).join("")}
          </select>
        </label>
      </div>`;
  }
  if (CHECKOUT_STATE.paymentMethod === "boleto") {
    dynamicPanel = '<div class="payment-note"><strong>Boleto bancário</strong><p>O boleto será gerado após a confirmação e poderá levar até 2 dias úteis para compensação.</p></div>';
  }

  return `<section class="checkout-card"><h3>Pagamento</h3><div class="payment-options">${
    optionCard("pix", "PIX", "Aprovação imediata · QR Code e Copia e Cola") +
    optionCard("cartao", "Cartão de crédito", "Parcelamento em até 6x") +
    optionCard("boleto", "Boleto bancário", "Pagamento à vista com compensação")
  }</div>${dynamicPanel}</section>`;
}

function renderStepContent(detailedCart, totals) {
  const step = CHECKOUT_STATE.step;

  if (step === 1) {
    if (PAYMENT_CONFIG.checkout_login_required && !CHECKOUT_STATE.customerLoggedIn) {
      return `
      <div class="checkout-card cart-panel">
        <h3>Seu carrinho</h3>
        <p class="checkout-hint">Para finalizar sua compra, entre na sua conta.</p>
        <div class="checkout-actions">
          <a class="checkout-btn" href="/conta/entrar">Entrar para finalizar</a>
        </div>
      </div>`;
    }

    return `
      <div class="checkout-card cart-panel">
        <h3>Seu carrinho</h3>
        <div class="cart-list">${detailedCart.map((item) => `
          <article class="cart-item">
            <img src="${item.imagem}" alt="${item.nome}">
            <div class="cart-item-body">
              <h4>${item.nome}</h4>
              <p class="unit-price">${formatPrice(item.preco)} por unidade</p>
              <div class="cart-item-controls">
                <button class="qty-btn" type="button" onclick="decreaseCartQuantity(${item.id})">−</button>
                <span>${item.quantidade}</span>
                <button class="qty-btn" type="button" onclick="increaseCartQuantity(${item.id})">+</button>
                <button class="remove-btn" type="button" onclick="removeFromCart(${item.id})">Remover</button>
              </div>
            </div>
            <strong>${formatPrice(item.subtotal)}</strong>
          </article>`).join("")}
        </div>
        <div class="totals-inline">
          <div><span>Subtotal</span><strong>${formatPrice(totals.subtotal)}</strong></div>
          <div><span>Frete</span><strong>${totals.shipping ? formatPrice(totals.shipping) : "A calcular"}</strong></div>
          <div><span>Desconto</span><strong>− ${formatPrice(totals.discount)}</strong></div>
          <div class="total"><span>Total</span><strong>${formatPrice(totals.total)}</strong></div>
        </div>
        <div class="checkout-actions">
          <button class="checkout-btn" type="button" onclick="if (validateBeforeStep(2)) moveToStep(2)">Iniciar compra</button>
        </div>
      </div>`;
  }

  if (step === 2) {
    return `
      <section class="checkout-card">
        <h3>Contato</h3>
        ${CHECKOUT_STATE.customerLoggedIn ? '<p class="checkout-hint">Dados preenchidos com sua conta. Você pode editar antes de continuar.</p>' : '<p class="checkout-hint">Preencha seus dados para avançar para pagamento.</p>'}
        <div class="grid-2">
          <label>Nome completo<input value="${CHECKOUT_STATE.fullName}" oninput="handleCheckoutInput('fullName', this.value)"></label>
          <label>E-mail<input type="email" value="${CHECKOUT_STATE.email}" oninput="handleCheckoutInput('email', this.value)"></label>
          <label>Telefone<input value="${CHECKOUT_STATE.phone}" oninput="handleCheckoutInput('phone', this.value)"></label>
        </div>
        <label class="checkbox-line"><input type="checkbox" ${CHECKOUT_STATE.receiveNews ? "checked" : ""} onchange="handleCheckoutInput('receiveNews', this.checked, 'checkbox')">Receber ofertas e novidades por e-mail</label>
      </section>

      <section class="checkout-card">
        <h3>Entrega</h3>
        ${renderCustomerAddressSelector()}
        <div class="grid-2">
          <label>CEP<input value="${CHECKOUT_STATE.cep}" maxlength="9" placeholder="00000-000" oninput="handleCheckoutInput('cep', this.value)"></label>
          <div class="checkout-inline-actions">
            <button class="checkout-btn-outline" type="button" onclick="calculateShippingByCep()">Calcular frete</button>
            <a href="https://buscacepinter.correios.com.br/app/endereco/index.php" target="_blank" rel="noreferrer">Não sei meu CEP</a>
          </div>
          <label>Endereço<input value="${CHECKOUT_STATE.address}" oninput="handleCheckoutInput('address', this.value)"></label>
          <label>Número<input value="${CHECKOUT_STATE.number}" oninput="handleCheckoutInput('number', this.value)"></label>
          <label>Complemento<input value="${CHECKOUT_STATE.complement}" oninput="handleCheckoutInput('complement', this.value)"></label>
          <label>Bairro<input value="${CHECKOUT_STATE.district}" oninput="handleCheckoutInput('district', this.value)"></label>
          <label>Cidade<input value="${CHECKOUT_STATE.city}" oninput="handleCheckoutInput('city', this.value)"></label>
          <label>Estado<input value="${CHECKOUT_STATE.state}" maxlength="2" oninput="handleCheckoutInput('state', this.value.toUpperCase())"></label>
          <label class="full-width">Referência<input value="${CHECKOUT_STATE.reference}" oninput="handleCheckoutInput('reference', this.value)"></label>
        </div>
        <h4>Métodos de envio</h4>
        ${renderShippingOptions()}
        <div class="checkout-actions">
          <button class="checkout-btn-outline" type="button" onclick="moveToStep(1)">Voltar</button>
          <button class="checkout-btn-primary" type="button" onclick="if (validateBeforeStep(2)) moveToStep(3)">Continuar para entrega</button>
        </div>
      </section>`;
  }

  if (step === 3) {
    return `
      <section class="checkout-card">
        <h3>Seleção de frete</h3>
        ${renderShippingOptions()}
        <div class="checkout-actions">
          <button class="checkout-btn-outline" type="button" onclick="moveToStep(2)">Voltar</button>
          <button class="checkout-btn-primary" type="button" onclick="if (validateBeforeStep(3)) moveToStep(4)">Continuar para pagamento</button>
        </div>
      </section>
    `;
  }

  if (step === 4) {
    return `
      ${renderPaymentPanel()}
      <div class="checkout-actions">
        <button class="checkout-btn-outline" type="button" onclick="moveToStep(3)">Voltar</button>
        <button class="checkout-btn-primary" type="button" onclick="if (validateBeforeStep(3)) moveToStep(5)">Revisar pedido</button>
      </div>
    `;
  }

  if (step === 5) {
    const selectedShipping = getSelectedShipping();
    return `
      <section class="checkout-card">
        <h3>Confirmação do pedido</h3>
        <p class="checkout-hint">Confira os dados de contato, entrega, frete e pagamento antes de concluir.</p>
        <p><strong>Contato:</strong> ${CHECKOUT_STATE.fullName} · ${CHECKOUT_STATE.email} · ${CHECKOUT_STATE.phone}</p>
        <p><strong>Entrega:</strong> ${formatAddressPayload()}</p>
        <p><strong>Frete:</strong> ${selectedShipping ? `${selectedShipping.method_name} (${selectedShipping.shipping_eta})` : "Não selecionado"}</p>
        <p><strong>Pagamento:</strong> ${CHECKOUT_STATE.paymentMethod}</p>
        <div class="checkout-actions">
          <button class="checkout-btn-outline" type="button" onclick="moveToStep(4)">Voltar</button>
          <button class="checkout-btn" type="button" onclick="moveToStep(6)">Confirmar e iniciar pagamento</button>
        </div>
      </section>
    `;
  }

  if (step === 6) {
    return `
      <section class="checkout-card">
        <h3>Iniciar pagamento</h3>
        <p class="checkout-hint">Ao confirmar, o pedido será criado e o pagamento será iniciado no método escolhido.</p>
        <div class="checkout-actions">
          <button class="checkout-btn-outline" type="button" onclick="moveToStep(5)">Voltar</button>
          <button class="checkout-btn" type="button" onclick="checkoutNow()">Criar pedido e pagar</button>
        </div>
        <pre id="checkout-instructions" class="checkout-response"></pre>
      </section>
    `;
  }

  return `
    <section class="checkout-card">
      <h3>Pagamento iniciado</h3>
      <pre id="checkout-instructions" class="checkout-response"></pre>
    </section>
  `;
}

function renderCartPage() {
  const cartContainer = document.getElementById("cart-content");
  if (!cartContainer) return;

  const detailedCart = getDetailedCartItems();
  if (!detailedCart.length) {
    cartContainer.innerHTML = `<div class="empty-box"><p>Seu carrinho está vazio</p><a class="btn" href="produtos.html">Ir para produtos</a></div>`;
    return;
  }

  const totals = getOrderTotals();
  const pixTotal = Math.max(0, totals.total - totals.subtotal * 0.05);

  cartContainer.innerHTML = `
    ${renderStepIndicator()}
    <div class="checkout-layout">
      <section class="checkout-main">
        ${renderStepContent(detailedCart, totals)}
      </section>

      <aside class="checkout-summary">
        <div class="checkout-card summary-card">
          <h3>Resumo do pedido</h3>
          <div class="summary-products">${detailedCart.map((item) => `<div><img src="${item.imagem}" alt="${item.nome}"><p>${item.nome}<br><small>Qtd. ${item.quantidade}</small></p><strong>${formatPrice(item.subtotal)}</strong></div>`).join("")}</div>
          <label>Adicionar cupom de desconto
            <div class="coupon-inline">
              <input id="coupon-input" value="${CHECKOUT_STATE.couponCode}" placeholder="Ex.: PRIMEIRA10">
              <button type="button" class="checkout-btn-outline" onclick="applyCoupon()">Aplicar</button>
            </div>
          </label>
          <dl class="summary-totals">
            <div><dt>Subtotal</dt><dd>${formatPrice(totals.subtotal)}</dd></div>
            <div><dt>Frete</dt><dd>${totals.shipping ? formatPrice(totals.shipping) : "A calcular"}</dd></div>
            <div><dt>Desconto</dt><dd>− ${formatPrice(totals.discount)}</dd></div>
            <div class="total"><dt>Total</dt><dd>${formatPrice(totals.total)}</dd></div>
          </dl>
          <p class="pix-discount">Ou ${formatPrice(pixTotal)} com Pix</p>
        </div>
      </aside>
    </div>
  `;
}

async function preloadCustomerData() {
  try {
    const sessionResponse = await fetch("/api/customer/session");
    if (!sessionResponse.ok) {
      CHECKOUT_STATE.customerLoaded = true;
      return;
    }

    const session = await sessionResponse.json();
    window.__CUSTOMER_SESSION__ = session;
    CHECKOUT_STATE.customerLoggedIn = Boolean(session.authenticated);

    if (!CHECKOUT_STATE.customerLoggedIn) {
      CHECKOUT_STATE.customerLoaded = true;
      return;
    }

    const accountResponse = await fetch("/api/customer/account");
    if (accountResponse.ok) {
      const account = await accountResponse.json();
      CHECKOUT_STATE.fullName = account.nome_completo || CHECKOUT_STATE.fullName;
      CHECKOUT_STATE.email = account.email || CHECKOUT_STATE.email;
      CHECKOUT_STATE.phone = account.telefone || CHECKOUT_STATE.phone;
      CHECKOUT_STATE.receiveNews = Boolean(account.aceita_marketing);
    }

    const addressesResponse = await fetch("/api/customer/addresses");
    if (addressesResponse.ok) {
      const addresses = await addressesResponse.json();
      CHECKOUT_STATE.customerAddresses = Array.isArray(addresses) ? addresses : [];
      if (CHECKOUT_STATE.customerAddresses.length) {
        const defaultAddress = CHECKOUT_STATE.customerAddresses.find((address) => Boolean(address.is_default)) || CHECKOUT_STATE.customerAddresses[0];
        CHECKOUT_STATE.selectedAddressId = String(defaultAddress.id);
        applyAddressData(defaultAddress);
      }
    }
  } catch (error) {
    console.warn("Não foi possível pré-carregar dados da conta:", error);
  } finally {
    CHECKOUT_STATE.customerLoaded = true;
    renderCartPage();
  }
}

window.renderCartPage = renderCartPage;
window.removeFromCart = removeFromCart;
window.increaseCartQuantity = increaseCartQuantity;
window.decreaseCartQuantity = decreaseCartQuantity;
window.checkoutNow = checkoutNow;
window.calculateShippingByCep = calculateShippingByCep;
window.moveToStep = moveToStep;
window.handleCheckoutInput = handleCheckoutInput;
window.handleShippingSelection = handleShippingSelection;
window.handlePaymentSelection = handlePaymentSelection;
window.applyCoupon = applyCoupon;
window.handleAddressSelection = handleAddressSelection;

document.addEventListener("DOMContentLoaded", async () => {
  await loadPaymentConfig();
  preloadCustomerData();
});
