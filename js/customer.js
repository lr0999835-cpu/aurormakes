async function fetchCustomerSession() {
  const response = await fetch('/api/customer/session');
  return response.json();
}

function setMessage(text, isError = false) {
  const target = document.getElementById('form-message');
  if (!target) return;
  target.textContent = text;
  target.style.color = isError ? '#b00020' : '#166534';
}

function formToObject(form) {
  const data = new FormData(form);
  const obj = Object.fromEntries(data.entries());
  obj.aceita_marketing = data.get('aceita_marketing') === 'on';
  obj.is_default = data.get('is_default') === 'on';
  return obj;
}

async function handleLoginForm() {
  const form = document.getElementById('customer-login-form');
  if (!form) return;
  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    const payload = formToObject(form);
    const response = await fetch('/api/customer/login', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
    const data = await response.json();
    if (!response.ok) return setMessage(data.error || 'Não foi possível entrar.', true);
    setMessage('Login realizado com sucesso.');
    window.location.href = '/minha-conta';
  });
}

async function handleRegisterForm() {
  const form = document.getElementById('customer-register-form');
  if (!form) return;
  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    const payload = formToObject(form);
    const response = await fetch('/api/customer/register', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
    const data = await response.json();
    if (!response.ok) return setMessage(data.error || 'Não foi possível criar conta.', true);
    setMessage('Conta criada com sucesso!');
    window.location.href = '/minha-conta';
  });
}

async function loadProfileForm() {
  const form = document.getElementById('customer-profile-form');
  if (!form) return;

  const response = await fetch('/api/customer/account');
  const data = await response.json();
  if (!response.ok) return setMessage(data.error || 'Erro ao carregar perfil.', true);

  Object.entries(data).forEach(([key, value]) => {
    const field = form.querySelector(`[name="${key}"]`);
    if (!field) return;
    if (field.type === 'checkbox') {
      field.checked = Boolean(value);
    } else {
      field.value = value || '';
    }
  });

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    const payload = formToObject(form);
    const saveResponse = await fetch('/api/customer/account', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
    const saveData = await saveResponse.json();
    if (!saveResponse.ok) return setMessage(saveData.error || 'Erro ao salvar.', true);
    setMessage('Dados salvos com sucesso.');
  });
}

async function loadCustomerOrders() {
  const list = document.getElementById('customer-orders-list');
  if (!list) return;
  const response = await fetch('/api/customer/orders');
  const orders = await response.json();
  if (!response.ok) {
    list.textContent = orders.error || 'Erro ao carregar pedidos.';
    return;
  }
  if (!orders.length) {
    list.innerHTML = '<p>Você ainda não possui pedidos.</p>';
    return;
  }
  list.innerHTML = orders.map((order) => `<article class="account-card"><strong>Pedido #${order.id}</strong><p>Status do pedido: ${order.status}</p><p>Status do pagamento: ${order.payment_status || 'pendente'}</p><p>Pagamento: ${order.payment_method || '-'}</p><p>Frete: ${order.shipping_label || order.shipping_method || '-'}</p><p>Subtotal: R$ ${Number(order.subtotal || 0).toFixed(2)}</p><p>Frete: R$ ${Number(order.shipping_amount || 0).toFixed(2)}</p><p>Desconto: R$ ${Number(order.discount_amount || 0).toFixed(2)}</p><p><strong>Total: R$ ${Number(order.total).toFixed(2)}</strong></p></article>`).join('');
}

async function loadCustomerAddresses() {
  const list = document.getElementById('customer-address-list');
  const form = document.getElementById('customer-address-form');
  if (!list) return;

  async function refresh() {
    const response = await fetch('/api/customer/addresses');
    const addresses = await response.json();
    if (!response.ok) {
      list.textContent = addresses.error || 'Erro ao carregar endereços.';
      return;
    }
    list.innerHTML = !addresses.length
      ? '<p>Nenhum endereço cadastrado.</p>'
      : addresses.map((address) => `<article class="account-card"><strong>${address.endereco}, ${address.numero}</strong><p>${address.bairro} · ${address.cidade}/${address.estado}</p><p>CEP ${address.cep}</p></article>`).join('');
  }

  if (form) {
    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      const payload = formToObject(form);
      const response = await fetch('/api/customer/addresses', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
      const data = await response.json();
      if (!response.ok) return setMessage(data.error || 'Erro ao salvar endereço.', true);
      setMessage('Endereço salvo com sucesso.');
      form.reset();
      await refresh();
    });
  }

  await refresh();
}

async function initHeaderCustomerMenu() {
  const trigger = document.querySelector('[data-customer-menu-trigger]');
  const menu = document.querySelector('[data-customer-menu]');
  if (!trigger || !menu) return;

  const session = await fetchCustomerSession();
  const links = session.authenticated
    ? [
        ['Minha conta', '/minha-conta'],
        ['Meus pedidos', '/meus-pedidos'],
        ['Meus endereços', '/meus-enderecos'],
        ['Sair', '/conta/sair']
      ]
    : [
        ['Entrar', '/conta/entrar'],
        ['Criar conta', '/conta/criar']
      ];

  menu.innerHTML = links.map(([label, href]) => `<a href="${href}">${label}</a>`).join('');

  trigger.addEventListener('click', (event) => {
    event.preventDefault();
    menu.classList.toggle('is-open');
  });
  document.addEventListener('click', (event) => {
    if (!menu.contains(event.target) && !trigger.contains(event.target)) menu.classList.remove('is-open');
  });
}

document.addEventListener('DOMContentLoaded', async () => {
  await initHeaderCustomerMenu();
  await handleLoginForm();
  await handleRegisterForm();
  await loadProfileForm();
  await loadCustomerOrders();
  await loadCustomerAddresses();
});
