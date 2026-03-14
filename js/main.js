const CART_STORAGE_KEY = "aurora_makes_cart";
const WHATSAPP_URL = "https://wa.me/5521974803694";

let catalogoProdutos = [];

function formatPrice(value) {
  return value.toLocaleString("pt-BR", {
    style: "currency",
    currency: "BRL"
  });
}

function normalizeProduct(product) {
  return {
    id: Number(product.id),
    nome: product.name || product.nome,
    preco: Number(product.price ?? product.preco ?? 0),
    imagem: product.image_url || product.imagem || "images/hero-makeup.svg",
    estoque: Number(product.stock ?? 0),
    ativo: product.is_active !== false
  };
}

async function carregarProdutos() {
  try {
    const response = await fetch("/api/products");

    if (!response.ok) {
      throw new Error("Falha ao carregar API de produtos");
    }

    const data = await response.json();
    catalogoProdutos = data.map(normalizeProduct).filter((produto) => produto.ativo);
  } catch (error) {
    console.warn("Usando produtos fallback:", error);
    catalogoProdutos = (window.PRODUTOS_FALLBACK || []).map(normalizeProduct);
  }
}

function getCart() {
  const cartData = localStorage.getItem(CART_STORAGE_KEY);

  if (!cartData) {
    return [];
  }

  try {
    const parsed = JSON.parse(cartData);

    if (!Array.isArray(parsed)) {
      return [];
    }

    return parsed
      .map((item) => ({
        id: Number(item.id),
        quantidade: Number(item.quantidade)
      }))
      .filter((item) => Number.isInteger(item.id) && item.quantidade > 0);
  } catch {
    return [];
  }
}

function saveCart(cart) {
  localStorage.setItem(CART_STORAGE_KEY, JSON.stringify(cart));
}

function findProductById(productId) {
  return catalogoProdutos.find((produto) => produto.id === Number(productId));
}

function addProductToCart(productId) {
  const cart = getCart();
  const itemIndex = cart.findIndex((item) => item.id === Number(productId));

  if (itemIndex >= 0) {
    cart[itemIndex].quantidade += 1;
  } else {
    cart.push({ id: Number(productId), quantidade: 1 });
  }

  saveCart(cart);
  return cart;
}

function removeProductFromCart(productId) {
  const updatedCart = getCart().filter((item) => item.id !== Number(productId));
  saveCart(updatedCart);
  return updatedCart;
}

function changeProductQuantity(productId, amount) {
  const cart = getCart();
  const item = cart.find((cartItem) => cartItem.id === Number(productId));

  if (!item) {
    return cart;
  }

  item.quantidade += Number(amount);

  const updatedCart = cart.filter((cartItem) => cartItem.quantidade > 0);
  saveCart(updatedCart);
  return updatedCart;
}

function getDetailedCartItems() {
  return getCart()
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
}

function calculateCartTotal() {
  return getDetailedCartItems().reduce((sum, item) => sum + item.subtotal, 0);
}

function updateCartCount() {
  const countElement = document.getElementById("cart-count");

  if (!countElement) {
    return;
  }

  const totalItems = getCart().reduce((sum, item) => sum + item.quantidade, 0);
  countElement.textContent = totalItems;
}

function addToCart(productId) {
  addProductToCart(productId);
  updateCartCount();

  if (typeof renderCartPage === "function") {
    renderCartPage();
  }
}

function createProductCardElement(product) {
  const card = document.createElement("article");
  card.className = "card";
  card.setAttribute("role", "button");
  card.setAttribute("tabindex", "0");

  const installmentPrice = product.preco / 6;
  const stockWarning = product.estoque <= 5 ? `<p class="stock-warning">Atenção, última peça!</p>` : "";

  card.innerHTML = `
    <img src="${product.imagem}" alt="${product.nome}" class="card-image" loading="lazy">
    <div class="card-content">
      <h3>${product.nome}</h3>
      <p class="price">${formatPrice(product.preco)}</p>
      <p class="installments">ou 6x de ${formatPrice(installmentPrice)} sem juros</p>
      ${stockWarning}
      <button type="button">Adicionar ao carrinho</button>
    </div>
  `;

  const addButton = card.querySelector("button");

  card.addEventListener("click", () => {
    addToCart(product.id);
  });

  card.addEventListener("keydown", (event) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      addToCart(product.id);
    }
  });

  addButton.addEventListener("click", (event) => {
    event.stopPropagation();
    addToCart(product.id);
  });

  return card;
}

function renderProducts(targetId, products) {
  const container = document.getElementById(targetId);

  if (!container) {
    return;
  }

  container.innerHTML = "";
  products.forEach((product) => {
    container.appendChild(createProductCardElement(product));
  });
}

function renderHomeProducts() {
  const destaques = catalogoProdutos.slice(0, 10);
  renderProducts("home-products", destaques);
}

function renderProductsPage() {
  renderProducts("lista-produtos", catalogoProdutos);
}

window.addToCart = addToCart;
window.WHATSAPP_URL = WHATSAPP_URL;

document.addEventListener("DOMContentLoaded", async () => {
  await carregarProdutos();

  updateCartCount();
  renderHomeProducts();
  renderProductsPage();

  if (typeof renderCartPage === "function") {
    renderCartPage();
  }
});
