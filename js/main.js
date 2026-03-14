const CART_STORAGE_KEY = "aurora_makes_cart";
const WHATSAPP_NUMBER = "5511999999999"; // Troque para o número da sua loja

function formatPrice(value) {
  return value.toLocaleString("pt-BR", {
    style: "currency",
    currency: "BRL"
  });
}

function getCart() {
  const cartData = localStorage.getItem(CART_STORAGE_KEY);
  return cartData ? JSON.parse(cartData) : [];
}

function saveCart(cart) {
  localStorage.setItem(CART_STORAGE_KEY, JSON.stringify(cart));
}

function findProductById(productId) {
  return CATALOGO_PRODUTOS.find((produto) => produto.id === Number(productId));
}

function updateCartCount() {
  const countElement = document.getElementById("cart-count");
  if (!countElement) {
    return;
  }

  const cart = getCart();
  const totalItems = cart.reduce((sum, item) => sum + item.quantidade, 0);
  countElement.textContent = totalItems;
}

function addToCart(productId) {
  const cart = getCart();
  const itemIndex = cart.findIndex((item) => item.id === Number(productId));

  if (itemIndex >= 0) {
    cart[itemIndex].quantidade += 1;
  } else {
    cart.push({ id: Number(productId), quantidade: 1 });
  }

  saveCart(cart);
  updateCartCount();
  alert("Produto adicionado ao carrinho!");
}

function renderProductCard(product) {
  return `
    <article class="card">
      <img src="${product.imagem}" alt="${product.nome}">
      <h3>${product.nome}</h3>
      <p class="price">${formatPrice(product.preco)}</p>
      <button onclick="addToCart(${product.id})">Adicionar ao carrinho</button>
    </article>
  `;
}

function renderHomeProducts() {
  const homeContainer = document.getElementById("home-products");
  if (!homeContainer) {
    return;
  }

  const destaques = CATALOGO_PRODUTOS.slice(0, 3);
  homeContainer.innerHTML = destaques.map(renderProductCard).join("");
}

function renderProductsPage() {
  const productsContainer = document.getElementById("lista-produtos");
  if (!productsContainer) {
    return;
  }

  productsContainer.innerHTML = CATALOGO_PRODUTOS.map(renderProductCard).join("");
}

updateCartCount();
renderHomeProducts();
renderProductsPage();
