let produtos = [];

function cadastrarProduto() {
  const nome = document.getElementById("nome").value;
  const categoria = document.getElementById("categoria").value;
  const preco = document.getElementById("preco").value;
  const estoque = document.getElementById("estoque").value;

  if (!nome || !categoria || !preco || !estoque) {
    alert("Preencha todos os campos.");
    return;
  }

  const produto = {
    nome: nome,
    categoria: categoria,
    preco: Number(preco),
    estoque: Number(estoque)
  };

  produtos.push(produto);
  atualizarLista();
  limparCampos();
}

function atualizarLista() {
  const lista = document.getElementById("lista-produtos");
  lista.innerHTML = "";

  produtos.forEach((produto, index) => {
    lista.innerHTML += `
      <div class="produto">
        <h3>${produto.nome}</h3>
        <p><strong>Categoria:</strong> ${produto.categoria}</p>
        <p><strong>Preço:</strong> R$ ${produto.preco.toFixed(2)}</p>
        <p><strong>Estoque:</strong> ${produto.estoque}</p>
        <button onclick="venderProduto(${index})">Registrar Venda</button>
      </div>
    `;
  });
}

function venderProduto(index) {
  if (produtos[index].estoque > 0) {
    produtos[index].estoque -= 1;
    atualizarLista();
  } else {
    alert("Produto sem estoque.");
  }
}

function limparCampos() {
  document.getElementById("nome").value = "";
  document.getElementById("categoria").value = "";
  document.getElementById("preco").value = "";
  document.getElementById("estoque").value = "";
}