const CART_STORAGE_KEY = "aurora_makes_cart";
const WHATSAPP_NUMBER = "5521974803694";

function formatPrice(value) {
  return value.toLocaleString("pt-BR", {
    style: "currency",
    currency: "BRL"
  });
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
  return CATALOGO_PRODUTOS.find((produto) => produto.id === Number(productId));
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

function renderProductCard(product) {
  return `
    <article class="card" role="button" tabindex="0" onclick="addToCart(${product.id})" onkeypress="if(event.key === 'Enter'){ addToCart(${product.id}); }">
      <img src="${product.imagem}" alt="${product.nome}">
      <h3>${product.nome}</h3>
      <p class="price">${formatPrice(product.preco)}</p>
      <button type="button" onclick="event.stopPropagation(); addToCart(${product.id})">Adicionar ao carrinho</button>
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

window.addToCart = addToCart;

document.addEventListener("DOMContentLoaded", () => {
  updateCartCount();
  renderHomeProducts();
  renderProductsPage();

  if (typeof renderCartPage === "function") {
    renderCartPage();
  }
});
