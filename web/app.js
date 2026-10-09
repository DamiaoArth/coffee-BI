"use strict";
const $ = (q, root = document) => root.querySelector(q);
const esc = (x) =>
  String(x ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
const currency = (x) =>
  Number(x || 0).toLocaleString("pt-BR", {
    style: "currency",
    currency: "BRL",
  });
const today = () => {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
};
const dateLabel = (x) =>
  x
    ? new Date(`${String(x).slice(0, 10)}T12:00:00`).toLocaleDateString("pt-BR")
    : "—";
const paths = {
  dashboard:
    '<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>',
  products: '<path d="m12 3 9 5v9l-9 5-9-5V8zM3 8l9 5 9-5M12 13v9M7 5l10 6"/>',
  sales: '<path d="M6 3h12v18l-3-2-3 2-3-2-3 2zM9 7h6M9 11h6M9 15h3"/>',
  purchases: '<path d="M3 3h2l3 13h11l2-9H6M9 20h.01M18 20h.01"/>',
  transactions: '<path d="M3 6h18v14H3zM3 6l15-3v3M15 12h6v4h-6z"/>',
  employees:
    '<circle cx="9" cy="7" r="3"/><path d="M3 21v-4a6 6 0 0 1 12 0v4M16 4a3 3 0 0 1 0 6M18 13a5 5 0 0 1 3 4v4"/>',
  trend: '<path d="m3 17 6-6 4 4 8-10M15 5h6v6"/>',
};
const icon = (n) =>
  `<svg class="icon" viewBox="0 0 24 24" aria-hidden="true">${paths[n] || paths.products}</svg>`;
const resources = {
  products: {
    title: "Produtos",
    description:
      "Seu catálogo organizado. Preços, custos e estoque sempre à vista.",
    create: "Novo produto",
    sort: "nome",
    cols: [
      ["id", "ID"],
      ["nome", "Produto"],
      ["categoria", "Categoria"],
      ["preco_venda", "Preço de venda"],
      ["custo_unitario", "Custo"],
      ["estoque_atual", "Estoque"],
      ["ativo", "Status"],
    ],
  },
  sales: {
    title: "Vendas",
    description: "Acompanhe os pedidos e registre novas vendas com segurança.",
    create: "Registrar venda",
    sort: "id",
    cols: [
      ["id", "Pedido"],
      ["data", "Data"],
      ["metodo_pagamento", "Pagamento"],
      ["valor_total", "Total"],
    ],
  },
  purchases: {
    title: "Compras",
    description: "Organize seus fornecedores e mantenha o estoque abastecido.",
    create: "Registrar compra",
    sort: "id",
    cols: [
      ["id", "Compra"],
      ["data", "Data"],
      ["fornecedor", "Fornecedor"],
      ["metodo_pagamento", "Pagamento"],
      ["valor_total", "Total"],
    ],
  },
  transactions: {
    title: "Financeiro",
    description:
      "Entradas e saídas avulsas para acompanhar o caixa da cafeteria.",
    create: "Nova transação",
    sort: "id",
    cols: [
      ["id", "ID"],
      ["descricao", "Descrição"],
      ["data", "Data"],
      ["categoria", "Categoria"],
      ["tipo", "Tipo"],
      ["valor", "Valor"],
    ],
  },
  employees: {
    title: "Equipe",
    description: "Pessoas que fazem parte da sua cafeteria.",
    create: "Novo funcionário",
    sort: "id",
    cols: [
      ["id", "ID"],
      ["nome", "Nome"],
      ["cargo", "Cargo"],
      ["email", "E-mail"],
      ["data_admissao", "Admissão"],
      ["ativo", "Status"],
    ],
  },
};
let user = null,
  route = "dashboard",
  listState = {},
  rows = [],
  loadVersion = 0,
  onSave = null,
  saving = false,
  toastTimer;
const isAdmin = () => user?.nivel_acesso === "admin";
async function api(path, options = {}) {
  const response = await fetch(`/api${path}`, {
    credentials: "same-origin",
    ...options,
    headers: { "Content-Type": "application/json", ...options.headers },
  });
  if (response.status === 204) return null;
  const data = await response
    .json()
    .catch(() => ({ detail: "Resposta inválida do servidor." }));
  if (!response.ok) {
    if (response.status === 401 && !path.includes("/auth/login")) showLogin();
    let message = data.detail;
    if (Array.isArray(message))
      message = message
        .map((e) => `${e.loc.slice(1).join(" → ")}: ${e.msg}`)
        .join("\n");
    throw new Error(message || "Não foi possível concluir a operação.");
  }
  return data;
}
function toast(message) {
  clearTimeout(toastTimer);
  $("#toast").textContent = message;
  $("#toast").hidden = false;
  toastTimer = setTimeout(() => ($("#toast").hidden = true), 4500);
}
function showLogin() {
  loadVersion++;
  user = null;
  $("#app-shell").hidden = true;
  $("#login-screen").hidden = false;
  $("#modal").close();
  $("#login-form").reset();
}
function startApp(data) {
  user = data;
  $("#login-screen").hidden = true;
  $("#app-shell").hidden = false;
  $("#username").textContent = data.username;
  $("#user-role").textContent = isAdmin() ? "Administrador" : "Caixa";
  $("#user-avatar").textContent = data.username[0].toUpperCase();
  $("#navigation").innerHTML = [
    "dashboard",
    "products",
    "sales",
    ...(isAdmin() ? ["purchases", "transactions", "employees"] : []),
  ]
    .map(
      (n) =>
        `<a href="#${n}" data-route="${n}">${icon(n)}${n === "dashboard" ? "Visão geral" : resources[n].title}</a>`,
    )
    .join("");
  navigate();
}
function navigate() {
  if (!user) return;
  route = location.hash.slice(1) || "dashboard";
  if (route !== "dashboard" && !resources[route]) route = "dashboard";
  if (!isAdmin() && ["employees", "purchases", "transactions"].includes(route))
    route = "dashboard";
  document.querySelectorAll("nav a").forEach((a) => {
    a.classList.toggle("active", a.dataset.route === route);
    a.setAttribute(
      "aria-current",
      a.dataset.route === route ? "page" : "false",
    );
  });
  const title = route === "dashboard" ? "Visão geral" : resources[route].title;
  $("#page-title").textContent = title;
  $("#breadcrumb").textContent = title;
  $("#eyebrow").textContent =
    route === "dashboard"
      ? "SEU NEGÓCIO, EM PERSPECTIVA"
      : "GESTÃO DA CAFETERIA";
  $("#page-description").textContent =
    route === "dashboard"
      ? "Tudo o que você precisa saber para cuidar do próximo passo."
      : resources[route].description;
  if (route === "dashboard") dashboard();
  else {
    listState = {
      page: 1,
      size: 10,
      sort: resources[route].sort,
      direction: resources[route].sort === "nome" ? "asc" : "desc",
      q: "",
      active: "",
    };
    renderList();
  }
}
async function dashboard() {
  ++loadVersion;
  $("#page-actions").innerHTML =
    `<form id="period-form" class="date-filter"><label>De<input type="date" name="start" value="${today().slice(0, 8)}01" required></label><label>Até<input type="date" name="end" value="${today()}" required></label><button class="secondary" type="submit">Aplicar</button></form>`;
  const load = async () => {
    const own = ++loadVersion;
    $("#content").innerHTML =
      '<div class="loading">Carregando os resultados…</div>';
    try {
      const query = new URLSearchParams(new FormData($("#period-form")));
      const data = await api(`/dashboard?${query}`);
      if (own !== loadVersion || route !== "dashboard") return;
      renderDashboard(data);
    } catch (e) {
      if (own === loadVersion)
        $("#content").innerHTML =
          `<div class="empty"><strong>Não foi possível carregar</strong>${esc(e.message)}</div>`;
    }
  };
  $("#period-form").addEventListener("submit", (e) => {
    e.preventDefault();
    load();
  });
  await load();
}
function renderDashboard(d) {
  const stats = [
    [
      "Faturamento",
      currency(d.revenue),
      `${d.sales_count} vendas no período`,
      "trend",
    ],
    ["Ticket médio", currency(d.ticket), "Valor médio por pedido", "sales"],
    [
      "Produtos ativos",
      d.products_count,
      "Seu catálogo em movimento",
      "products",
    ],
    [
      isAdmin() ? "Saldo de caixa" : "Estoque baixo",
      isAdmin() ? currency(d.cash_balance) : d.low_stock.length,
      isAdmin()
        ? "Vendas + entradas − compras − saídas"
        : "Produtos que precisam de reposição",
      "transactions",
    ],
  ];
  $("#content").innerHTML =
    `<div class="stats">${stats.map((s) => `<article class="stat"><div class="stat-label">${s[0]}${icon(s[3])}</div><div class="stat-value">${s[1]}</div><div class="stat-note">${esc(s[2])}</div></article>`).join("")}</div>${d.low_stock.length ? `<div class="alert-banner"><div><strong>${d.low_stock.length} produto(s) precisam da sua atenção</strong>Confira os níveis de estoque e planeje a reposição.</div><a class="button" href="#products">Ver estoque →</a></div>` : ""}<div class="dashboard-grid"><article class="card"><div class="card-header"><div><h3>Evolução das vendas</h3><p>Faturamento diário no período selecionado</p></div><span class="badge">Receita</span></div><div class="card-body"><div id="revenue-chart"></div><p id="chart-tip" class="chart-tip">Passe o cursor ou use Tab nos pontos para ver os valores.</p></div></article><article class="card"><div class="card-header"><div><h3>Formas de pagamento</h3><p>Como seus clientes preferem pagar</p></div></div><div class="card-body">${
      d.payments.length
        ? d.payments
            .sort((a, b) => b.total - a.total)
            .map(
              (p) =>
                `<div class="bar-row"><div class="bar-label"><span>${esc(p.name)}</span><strong>${currency(p.total)}</strong></div><div class="bar-track"><div class="bar-fill" style="width:${d.revenue ? Math.max(0, Math.min(100, (p.total / d.revenue) * 100)) : 0}%"></div></div></div>`,
            )
            .join("")
        : '<div class="empty"><strong>O primeiro pedido vem aí</strong>Registre uma venda para acompanhar os pagamentos.</div>'
    }</div></article></div><article class="card"><div class="card-header"><div><h3>Estoque que merece atenção</h3><p>Produtos no mínimo ou sem estoque</p></div><a href="#products" class="muted">Ver catálogo →</a></div><div class="table-wrap"><table><thead><tr><th>Produto</th><th>Categoria</th><th>Disponível</th><th>Mínimo</th><th>Status</th></tr></thead><tbody>${
      d.low_stock
        .slice(0, 8)
        .map(
          (p) =>
            `<tr><td><strong>${esc(p.nome)}</strong></td><td>${esc(p.categoria)}</td><td>${p.estoque_atual} ${esc(p.unidade)}</td><td>${p.estoque_minimo} ${esc(p.unidade)}</td><td><span class="badge ${p.estoque_atual ? "warn" : "off"}">${p.estoque_atual ? "Estoque baixo" : "Sem estoque"}</span></td></tr>`,
        )
        .join("") ||
      '<tr><td colspan="5" class="empty">Tudo em dia. Nenhum produto abaixo do estoque mínimo.</td></tr>'
    }</tbody></table></div></article>`;
  drawChart(d.series);
}
let chartData = null;
function drawChart(series) {
  chartData = series;
  const w = Math.max(320, $("#revenue-chart").clientWidth),
    h = 245,
    left = 65,
    top = 18,
    bottom = 205,
    right = w - 25,
    max = Math.max(1, ...series.map((p) => p.total)) * 1.15;
  const point = (p, i) => [
    left + ((right - left) * i) / Math.max(1, series.length - 1),
    bottom - ((bottom - top) * p.total) / max,
  ];
  const points = series.map(point);
  const line = points.map((p) => p.join(",")).join(" ");
  const ticks = [0, 0.25, 0.5, 0.75, 1]
    .map(
      (t) =>
        `<line class="gridline" x1="${left}" x2="${right}" y1="${bottom - (bottom - top) * t}" y2="${bottom - (bottom - top) * t}"/><text x="${left - 10}" y="${bottom - (bottom - top) * t + 4}" text-anchor="end">${Math.round(max * t).toLocaleString("pt-BR")}</text>`,
    )
    .join("");
  const labels = [0, Math.floor((series.length - 1) / 2), series.length - 1]
    .filter((x, i, a) => a.indexOf(x) === i)
    .map(
      (i) =>
        `<text x="${points[i][0]}" y="232" text-anchor="middle">${dateLabel(series[i].data).slice(0, 5)}</text>`,
    )
    .join("");
  $("#revenue-chart").innerHTML =
    `<svg class="chart" viewBox="0 0 ${w} ${h}" role="img" aria-label="Gráfico de receita diária em reais"><defs><linearGradient id="area" x1="0" y1="0" x2="0" y2="1"><stop stop-color="#2c7a58" stop-opacity=".16"/><stop offset="1" stop-color="#2c7a58" stop-opacity="0"/></linearGradient></defs>${ticks}<polygon points="${left},${bottom} ${line} ${points.at(-1)[0]},${bottom}" fill="url(#area)"/><polyline points="${line}" fill="none" stroke="#367b59" stroke-width="2.5"/>${points.map((p, i) => `<circle class="chart-point" cx="${p[0]}" cy="${p[1]}" r="3" tabindex="0" data-index="${i}" aria-label="${dateLabel(series[i].data)}: ${currency(series[i].total)}"><title>${dateLabel(series[i].data)}: ${currency(series[i].total)}</title></circle>`).join("")}${labels}</svg>`;
  document.querySelectorAll(".chart-point").forEach((p) => {
    const show = () =>
      ($("#chart-tip").textContent =
        `${dateLabel(series[p.dataset.index].data)} · ${currency(series[p.dataset.index].total)}`);
    p.addEventListener("mouseenter", show);
    p.addEventListener("focus", show);
  });
}
function renderList() {
  const cfg = resources[route];
  $("#page-actions").innerHTML =
    `<button id="export" class="secondary">↓ Exportar CSV</button>${isAdmin() || route === "sales" ? `<button id="new-item" class="primary">+ ${cfg.create}</button>` : ""}`;
  $("#content").innerHTML =
    `<article class="card"><div class="toolbar"><div class="search"><input id="search" type="search" placeholder="Buscar ${route === "products" ? "produto" : route === "employees" ? "funcionário" : route === "transactions" ? "descrição" : "por ID"}…" aria-label="Buscar registros"></div>${route === "products" ? '<select id="active-filter" aria-label="Status dos produtos"><option value="">Todos os status</option><option value="true">Ativos</option><option value="false">Inativos</option></select>' : ""}<span id="record-count" class="muted"></span></div><div id="data-table"></div></article>`;
  let debounce;
  $("#search").addEventListener("input", (e) => {
    listState.q = e.target.value;
    listState.page = 1;
    clearTimeout(debounce);
    const searchRoute = route;
    debounce = setTimeout(() => {
      if (route === searchRoute && $("#data-table")) loadList();
    }, 200);
  });
  $("#active-filter")?.addEventListener("change", (e) => {
    listState.active = e.target.value;
    listState.page = 1;
    loadList();
  });
  $("#new-item")?.addEventListener("click", () => openEditor());
  $("#export").addEventListener("click", exportCSV);
  loadList();
}
function listQuery(page = listState.page) {
  return new URLSearchParams({
    page,
    page_size: listState.size,
    sort: listState.sort,
    direction: listState.direction,
    q: listState.q,
    ...(listState.active !== "" ? { active: listState.active } : {}),
  });
}
async function loadList() {
  const own = ++loadVersion,
    current = route;
  $("#data-table").innerHTML =
    '<div class="loading">Carregando registros…</div>';
  try {
    const d = await api(`/${current}?${listQuery()}`);
    if (own !== loadVersion || current !== route) return;
    if (d.total && (d.page - 1) * d.page_size >= d.total) {
      listState.page = Math.ceil(d.total / d.page_size);
      return loadList();
    }
    rows = d.items;
    $("#record-count").textContent = `${d.total} registro(s)`;
    renderTable(d);
  } catch (e) {
    if (own === loadVersion)
      $("#data-table").innerHTML =
        `<div class="empty"><strong>Não foi possível carregar</strong>${esc(e.message)}<p><button class="secondary" id="retry">Tentar novamente</button></p></div>`;
    $("#retry")?.addEventListener("click", loadList);
  }
}
function cell(row, key) {
  if (["preco_venda", "custo_unitario", "valor_total", "valor"].includes(key))
    return currency(row[key]);
  if (key === "ativo")
    return `<span class="badge ${row.ativo ? "" : "off"}">${row.ativo ? "Ativo" : "Inativo"}</span>`;
  if (key === "nome")
    return `<strong>${esc(row.nome)}</strong>${route === "products" ? `<small>${esc(row.unidade)} · #${row.id}</small>` : ""}`;
  if (key === "estoque_atual")
    return `<span class="badge ${!row.estoque_atual ? "off" : row.estoque_atual <= row.estoque_minimo ? "warn" : ""}">${row.estoque_atual} ${esc(row.unidade)}</span>`;
  if (key === "data" || key === "data_admissao") return dateLabel(row[key]);
  if (key === "tipo")
    return `<span class="badge ${row.tipo === "entrada" ? "" : "warn"}">${esc(row.tipo)}</span>`;
  return esc(row[key] || "—");
}
function renderTable(d) {
  const cfg = resources[route],
    pages = Math.max(1, Math.ceil(d.total / d.page_size));
  $("#data-table").innerHTML =
    `<div class="table-wrap"><table><thead><tr>${cfg.cols.map(([k, l]) => `<th aria-sort="${listState.sort === k ? (listState.direction === "asc" ? "ascending" : "descending") : "none"}"><button data-sort="${k}">${l} ${listState.sort === k ? (listState.direction === "asc" ? "↑" : "↓") : "↕"}</button></th>`).join("")}<th>Ações</th></tr></thead><tbody>${rows.map((row) => `<tr>${cfg.cols.map(([k]) => `<td>${cell(row, k)}</td>`).join("")}<td><div class="actions">${["sales", "purchases"].includes(route) ? `<button data-view="${row.id}">Detalhes</button>` : isAdmin() ? `<button data-edit="${row.id}">Editar</button>` : ""}${isAdmin() ? `<button class="danger" data-delete="${row.id}">${["sales", "purchases"].includes(route) ? "Cancelar" : ["products", "employees"].includes(route) ? "Desativar" : "Excluir"}</button>` : ""}</div></td></tr>`).join("") || `<tr><td colspan="${cfg.cols.length + 1}" class="empty"><strong>Nenhum registro encontrado</strong>${listState.q ? "Tente outra busca." : "Comece cadastrando o primeiro registro."}</td></tr>`}</tbody></table></div><div class="pagination"><span>${d.total ? (d.page - 1) * d.page_size + 1 : 0}–${Math.min(d.page * d.page_size, d.total)} de ${d.total} registros</span><div class="pagination-controls"><label for="page-size">Por página</label><select id="page-size">${[10, 25, 50, 100].map((n) => `<option ${n === listState.size ? "selected" : ""}>${n}</option>`).join("")}</select><button id="prev-page" ${d.page <= 1 ? "disabled" : ""} aria-label="Página anterior">←</button><span>Página ${d.page} de ${pages}</span><button id="next-page" ${d.page >= pages ? "disabled" : ""} aria-label="Próxima página">→</button></div></div>`;
  document.querySelectorAll("[data-sort]").forEach(
    (b) =>
      (b.onclick = () => {
        listState.direction =
          listState.sort === b.dataset.sort && listState.direction === "asc"
            ? "desc"
            : "asc";
        listState.sort = b.dataset.sort;
        listState.page = 1;
        loadList();
      }),
  );
  $("#page-size").onchange = (e) => {
    listState.size = Number(e.target.value);
    listState.page = 1;
    loadList();
  };
  $("#prev-page").onclick = () => {
    listState.page--;
    loadList();
  };
  $("#next-page").onclick = () => {
    listState.page++;
    loadList();
  };
  document
    .querySelectorAll("[data-edit]")
    .forEach(
      (b) =>
        (b.onclick = () =>
          openEditor(rows.find((r) => r.id === Number(b.dataset.edit)))),
    );
  document
    .querySelectorAll("[data-view]")
    .forEach(
      (b) =>
        (b.onclick = () =>
          showDetails(rows.find((r) => r.id === Number(b.dataset.view)))),
    );
  document
    .querySelectorAll("[data-delete]")
    .forEach(
      (b) =>
        (b.onclick = () =>
          confirmDelete(rows.find((r) => r.id === Number(b.dataset.delete)))),
    );
}
async function exportCSV() {
  const current = route,
    cfg = resources[current],
    query = listQuery(1);
  const button = $("#export");
  button.disabled = true;
  try {
    let data = [],
      page = 1,
      total = 1;
    while (data.length < total) {
      query.set("page", page++);
      query.set("page_size", 100);
      const d = await api(`/${current}?${query}`);
      data.push(...d.items);
      total = d.total;
      if (!d.items.length) break;
    }
    const quote = (x) =>
      '"' +
      String(x ?? "")
        .replace(/^[=+@\-]/, "'")
        .replaceAll('"', '""') +
      '"';
    const csv =
      "\uFEFF" +
      [
        cfg.cols.map((c) => quote(c[1])).join(";"),
        ...data.map((r) => cfg.cols.map(([k]) => quote(r[k])).join(";")),
      ].join("\r\n");
    const url = URL.createObjectURL(
        new Blob([csv], { type: "text/csv;charset=utf-8" }),
      ),
      link = document.createElement("a");
    link.href = url;
    link.download = `coffee-bi-${current}.csv`;
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  } catch (e) {
    toast(e.message);
  } finally {
    button.disabled = false;
  }
}
const field = (name, label, value = "", type = "text", attrs = "") =>
  `<label>${label}<input name="${name}" type="${type}" value="${esc(value)}" ${attrs}></label>`;
const select = (name, label, options, value) =>
  `<label>${label}<select name="${name}">${options.map((o) => `<option value="${esc(o)}" ${o === value ? "selected" : ""}>${esc(o)}</option>`).join("")}</select></label>`;
function openModal(title, body, handler, label = "Salvar") {
  onSave = handler;
  $("#editor-form").reset();
  $("#modal-title").textContent = title;
  $("#form-fields").innerHTML = body;
  $("#form-error").textContent = "";
  $("#save-button").textContent = label;
  $("#save-button").hidden = !handler;
  $("#save-button").disabled = false;
  if (!$("#modal").open) $("#modal").showModal();
}
async function openEditor(row = null) {
  const current = route;
  if (["sales", "purchases"].includes(current)) return openMovement(current);
  if (row && current === "products") {
    try {
      row = await api(`/products/${row.id}`);
    } catch (error) {
      return toast(error.message);
    }
    if (route !== current) return;
  }
  let fields = "";
  if (current === "products")
    fields = `${field("nome", "Nome do produto", row?.nome || "", "text", 'required maxlength="200"')}${select("categoria", "Categoria", [...new Set(["café", "bebida", "lanche", "insumo", "sobremesa", "outro", row?.categoria].filter(Boolean))], row?.categoria || "café")}${field("preco_venda", "Preço de venda (R$)", row?.preco_venda ?? "", "number", 'min="0" step="0.01" required')}${field("custo_unitario", "Custo unitário (R$)", row?.custo_unitario ?? 0, "number", 'min="0" step="0.01" required')}${field("estoque_atual", "Estoque atual", row?.estoque_atual ?? 0, "number", 'min="0" step="1" required')}${field("estoque_minimo", "Estoque mínimo", row?.estoque_minimo ?? 0, "number", 'min="0" step="1" required')}${select("unidade", "Unidade", [...new Set(["un", "ml", "l", "g", "kg", "cx", row?.unidade].filter(Boolean))], row?.unidade || "un")}<label class="checkbox"><input name="ativo" type="checkbox" ${!row || row.ativo ? "checked" : ""}>Produto ativo</label>`;
  if (current === "employees")
    fields = `${field("nome", "Nome completo", row?.nome || "", "text", 'required maxlength="200"')}${field("cargo", "Cargo", row?.cargo || "", "text", 'required maxlength="100"')}${field("email", "E-mail", row?.email || "", "email", 'maxlength="200"')}${field("telefone", "Telefone", row?.telefone || "", "tel", 'maxlength="20"')}${field("data_admissao", "Data de admissão", row?.data_admissao || today(), "date", "required")}<label class="checkbox"><input name="ativo" type="checkbox" ${!row || row.ativo ? "checked" : ""}>Funcionário ativo</label>`;
  if (current === "transactions")
    fields = `${field("descricao", "Descrição", row?.descricao || "", "text", 'required maxlength="200"')}${select("tipo", "Tipo", ["entrada", "saída"], row?.tipo || "saída")}${field("valor", "Valor (R$)", row?.valor || "", "number", 'min="0.01" step="0.01" required')}${field("data", "Data", row?.data || today(), "date", "required")}${field("categoria", "Categoria", row?.categoria || "", "text", 'required maxlength="50"')}`;
  openModal(
    row ? "Editar registro" : resources[current].create,
    `<div class="form-grid">${fields}</div>`,
    async () => {
      const form = $("#editor-form"),
        data = Object.fromEntries(new FormData(form));
      if (current === "products") {
        for (const k of ["estoque_atual", "estoque_minimo"])
          data[k] = Number(data[k]);
        data.ativo = form.elements.ativo.checked;
      }
      if (current === "employees") {
        data.ativo = form.elements.ativo.checked;
        data.email = data.email || null;
        data.telefone = data.telefone || null;
      }
      await api(`/${current}${row ? "/" + row.id : ""}`, {
        method: row ? "PUT" : "POST",
        headers:
          current === "products" && row
            ? { "If-Match": String(row.version) }
            : {},
        body: JSON.stringify(data),
      });
      $("#modal").close();
      toast(row ? "Alterações salvas." : "Registro cadastrado com sucesso.");
      if (route === current) {
        listState.page = 1;
        await loadList();
      }
    },
  );
}
async function openMovement(current) {
  const version = loadVersion;
  let products = [];
  try {
    let page = 1,
      total = 1;
    while (products.length < total) {
      const d = await api(`/products?active=true&page_size=100&page=${page++}`);
      products.push(...d.items);
      total = d.total;
      if (!d.items.length) break;
    }
  } catch (e) {
    return toast(e.message);
  }
  if (route !== current || version !== loadVersion) return;
  if (!products.length)
    return toast("Cadastre um produto ativo antes de registrar a operação.");
  const purchase = current === "purchases";
  openModal(
    resources[current].create,
    `<div class="form-grid">${field("data", "Data", today(), "date", "required")}${select("metodo_pagamento", "Pagamento", ["Pix", "Dinheiro", "Cartão de crédito", "Cartão de débito", "Transferência"], "Pix")}${purchase ? field("fornecedor", "Fornecedor", "", "text", 'required maxlength="200"') : ""}<label class="wide">Observações<textarea name="observacoes" maxlength="2000"></textarea></label></div><h3 style="margin-top:24px">Itens ${purchase ? "da compra" : "do pedido"}</h3><div id="cart-lines"></div><button type="button" id="add-line" class="secondary">+ Adicionar item</button><div class="cart-total"><span>Total estimado</span><strong id="cart-total">R$ 0,00</strong></div>`,
    async () => {
      const data = Object.fromEntries(new FormData($("#editor-form")));
      delete data.product;
      delete data.quantity;
      delete data.price;
      data.itens = [...document.querySelectorAll(".item-line")].map((line) => ({
        id_produto: Number($("select", line).value),
        quantidade: Number($("[name=quantity]", line).value),
        preco_unitario: $("[name=price]", line).value,
      }));
      await api(`/${current}`, { method: "POST", body: JSON.stringify(data) });
      $("#modal").close();
      toast(
        purchase
          ? "Compra registrada. Estoque atualizado."
          : "Venda registrada. Estoque atualizado.",
      );
      if (route === current) await loadList();
    },
    purchase ? "Registrar compra" : "Concluir venda",
  );
  const total = () => {
    $("#cart-total").textContent = currency(
      [...document.querySelectorAll(".item-line")].reduce(
        (sum, line) =>
          sum +
          Number($("[name=quantity]", line).value) *
            Number($("[name=price]", line).value),
        0,
      ),
    );
  };
  const add = () => {
    const line = document.createElement("div");
    line.className = "item-line";
    line.innerHTML = `<label>Produto<select name="product">${products.map((p) => `<option value="${p.id}">${esc(p.nome)} (${p.estoque_atual} ${esc(p.unidade)})</option>`).join("")}</select></label>${field("quantity", "Qtd.", 1, "number", 'required min="1" step="1"')}${field("price", "Preço R$", purchase ? products[0].custo_unitario : products[0].preco_venda, "number", 'required min="0" step="0.01"')}<button type="button" class="icon-button" aria-label="Remover item">×</button>`;
    $("#cart-lines").append(line);
    $("select", line).onchange = (e) => {
      const p = products.find((p) => p.id === Number(e.target.value));
      $("[name=price]", line).value = purchase
        ? p.custo_unitario
        : p.preco_venda;
      total();
    };
    line.oninput = total;
    $("button", line).onclick = () => {
      line.remove();
      total();
    };
    total();
  };
  $("#add-line").onclick = add;
  add();
}
function confirmDelete(row) {
  const current = route;
  const inactive = ["products", "employees"].includes(current),
    movement = ["sales", "purchases"].includes(current);
  const verb = inactive ? "Desativar" : movement ? "Cancelar" : "Excluir";
  openModal(
    `${verb} registro #${row.id}`,
    `<p class="confirm-text">${inactive ? "O registro ficará inativo e seu histórico será preservado." : movement ? "O movimento será cancelado e o estoque será ajustado. Compras com estoque já consumido não podem ser canceladas." : "A transação será excluída do financeiro."}</p><strong>${esc(row.nome || row.descricao || row.fornecedor || `Pedido #${row.id}`)}</strong>`,
    async () => {
      await api(`/${current}/${row.id}`, { method: "DELETE" });
      $("#modal").close();
      toast("Operação concluída.");
      if (route === current) await loadList();
    },
    `${verb} registro`,
  );
}
function showDetails(row) {
  openModal(
    `Detalhes #${row.id}`,
    `<div class="detail-list"><div><span>Data</span><strong>${dateLabel(row.data)}</strong></div><div><span>Pagamento</span><strong>${esc(row.metodo_pagamento)}</strong></div>${row.fornecedor ? `<div><span>Fornecedor</span><strong>${esc(row.fornecedor)}</strong></div>` : ""}${row.itens.map((i) => `<div><span>${esc(i.produto_nome)}<br><small>${i.quantidade} × ${currency(i.preco_unitario)}</small></span><strong>${currency(i.subtotal)}</strong></div>`).join("")}<div><strong>Total</strong><strong>${currency(row.valor_total)}</strong></div>${row.observacoes ? `<p class="muted">${esc(row.observacoes)}</p>` : ""}</div>`,
    null,
  );
}
$("#editor-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  if (!onSave || saving) return;
  saving = true;
  $("#save-button").disabled = true;
  $("#form-error").textContent = "";
  $("#close-modal").disabled = true;
  $("#cancel-modal").disabled = true;
  try {
    await onSave();
  } catch (error) {
    $("#form-error").textContent = error.message;
  } finally {
    saving = false;
    $("#save-button").disabled = false;
    $("#close-modal").disabled = false;
    $("#cancel-modal").disabled = false;
  }
});
$("#close-modal").onclick = $("#cancel-modal").onclick = () => {
  if (!saving) $("#modal").close();
};
$("#modal").addEventListener("cancel", (e) => {
  if (saving) e.preventDefault();
});
$("#login-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const button = $("button", e.target);
  button.disabled = true;
  $("#login-error").textContent = "";
  try {
    const data = Object.fromEntries(new FormData(e.target));
    startApp(
      await api("/auth/login", { method: "POST", body: JSON.stringify(data) }),
    );
  } catch (error) {
    $("#login-error").textContent = error.message;
  } finally {
    button.disabled = false;
  }
});
$("#logout").onclick = async () => {
  try {
    await api("/auth/logout", { method: "POST" });
    showLogin();
  } catch (e) {
    toast(e.message);
  }
};
$("#mobile-logout").onclick = () => $("#logout").click();
window.addEventListener("hashchange", navigate);
let resizeTimer;
window.addEventListener("resize", () => {
  clearTimeout(resizeTimer);
  resizeTimer = setTimeout(() => {
    if (route === "dashboard" && chartData && $("#revenue-chart"))
      drawChart(chartData);
  }, 100);
});
api("/auth/me").then(startApp).catch(showLogin);
