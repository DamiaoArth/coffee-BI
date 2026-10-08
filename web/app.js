
/**
 * Coffee BI SPA — sem bibliotecas de front adicionais.
 * Navegação via History API, cache por recurso, deduplicação de requests,
 * revalidação discreta e skeletons por tipo de conteúdo.
 */
const root = document.querySelector('#root');
const toastNode = document.querySelector('#toast');
const state = { user:null, csrf:'', path:location.pathname, cache:new Map(),
  inflight:new Map(), modal:null, cart:[], cartMode:'sale', error:null,
  search:'', days:30, loginBusy:false, showPassword:false };
const ICONS = {
  dashboard:'<rect x="3" y="3" width="7" height="7" rx="2"/><rect x="14" y="3" width="7" height="7" rx="2"/><rect x="3" y="14" width="7" height="7" rx="2"/><rect x="14" y="14" width="7" height="7" rx="2"/>',
  intelligence:'<path d="M4 19V9"/><path d="M10 19V5"/><path d="M16 19v-7"/><path d="M22 19H2"/>',
  sales:'<path d="M6 2h12l1 5H5l1-5Z"/><path d="M5 7v14h14V7"/><path d="M9 11h6"/>',
  products:'<path d="m12 3 8 4.5v9L12 21l-8-4.5v-9L12 3Z"/><path d="m4.5 7.8 7.5 4.3 7.5-4.3"/><path d="M12 12.1V21"/>',
  purchases:'<path d="M3 5h2l2.2 9.2a2 2 0 0 0 2 1.5h7.6a2 2 0 0 0 2-1.6L20 8H6"/><circle cx="10" cy="20" r="1"/><circle cx="17" cy="20" r="1"/>',
  finance:'<rect x="3" y="5" width="18" height="14" rx="3"/><path d="M3 10h18"/><path d="M8 15h2"/>',
  team:'<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
  coffee:'<path d="M4 8h13v6a6 6 0 0 1-6 6H10a6 6 0 0 1-6-6V8Z"/><path d="M17 10h2a3 3 0 0 1 0 6h-2"/><path d="M7 3v2"/><path d="M11 3v2"/>',
  trend:'<path d="m3 17 6-6 4 4 8-9"/><path d="M15 6h6v6"/>',
  receipt:'<path d="M6 3h12v18l-3-2-3 2-3-2-3 2V3Z"/><path d="M9 8h6"/><path d="M9 12h6"/>',
  ticket:'<path d="M3 8a2 2 0 0 0 0 4v5h18v-5a2 2 0 0 0 0-4V5H3v3Z"/><path d="M13 5v12"/>',
  box:'<path d="m12 3 8 4.5v9L12 21l-8-4.5v-9L12 3Z"/><path d="m4.5 7.8 7.5 4.3 7.5-4.3"/>',
  arrowDown:'<path d="M12 3v18"/><path d="m7 16 5 5 5-5"/>',
  arrowUp:'<path d="M12 21V3"/><path d="m7 8 5-5 5 5"/>',
  wallet:'<path d="M3 7h16a2 2 0 0 1 2 2v9H5a2 2 0 0 1-2-2V7Z"/><path d="M3 7V5a2 2 0 0 1 2-2h12v4"/><path d="M16 12h5"/>',
  plus:'<path d="M12 5v14"/><path d="M5 12h14"/>',
  edit:'<path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L8 18l-4 1 1-4 11.5-11.5Z"/>',
  trash:'<path d="M3 6h18"/><path d="M8 6V4h8v2"/><path d="M19 6l-1 15H6L5 6"/><path d="M10 11v5"/><path d="M14 11v5"/>',
  logout:'<path d="M10 17l5-5-5-5"/><path d="M15 12H3"/><path d="M14 3h5a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-5"/>',
  close:'<path d="m6 6 12 12"/><path d="m18 6-12 12"/>',
  search:'<circle cx="11" cy="11" r="7"/><path d="m20 20-4-4"/>',
  alert:'<path d="M12 3 2.5 20h19L12 3Z"/><path d="M12 9v5"/><path d="M12 17h.01"/>',
  check:'<path d="m5 12 4 4L19 6"/>',
  arrowRight:'<path d="M5 12h14"/><path d="m14 7 5 5-5 5"/>',
  user:'<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>',
};
const icon = (name,size=18,extra='') => '<svg class="icon '+extra+'" width="'+size+'" height="'+size+'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'+(ICONS[name]||ICONS.dashboard)+'</svg>';
const pages = [
  ['dashboard','Visão geral','dashboard','/dashboard'],
  ['bi','Inteligência','intelligence','/bi'],
  ['sales','Vendas','sales','/sales'],
  ['products','Produtos','products','/products'],
  ['purchases','Compras','purchases','/purchases'],
  ['finance','Financeiro','finance','/finance'],
  ['team','Equipe','team','/team'],
];
const manager = () => !!state.user && ['admin','Gerente'].includes(state.user.role);
const admin = () => !!state.user && state.user.role === 'admin';
const available = () => pages.filter(([key]) => key!=='team' || admin()).filter(([key]) =>
    !['bi','purchases','finance','products'].includes(key) || key==='products' || manager());
const esc = value => String(value ?? '').replace(/[&<>"']/g, char =>
    ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
const money = value => new Intl.NumberFormat('pt-BR',{style:'currency',currency:'BRL'}).format(Number(value)||0);
const number = value => new Intl.NumberFormat('pt-BR').format(Number(value)||0);
const shortDate = value => { if (!value) return '—'; const [y,m,d]=String(value).split('-'); return y&&m&&d ? d+'/'+m+'/'+y : '—'; };
const today = () => new Date().toLocaleDateString('sv-SE');
const tag = (text, variant='') => '<span class="tag '+variant+'">'+esc(text)+'</span>';
const empty = (title, description='Ainda não há registros neste período.') =>
  '<div class="empty"><div class="empty-icon">'+icon('coffee',22)+'</div><strong>'+esc(title)+'</strong><p>'+esc(description)+'</p></div>';
function toast(message) {
  toastNode.textContent = message;
  toastNode.classList.add('visible');
  clearTimeout(toastNode._timer);
  toastNode._timer = setTimeout(()=>toastNode.classList.remove('visible'),3400);
}
async function request(path, options={}) {
  const method = options.method || 'GET';
  const headers = {'Accept':'application/json', ...(options.body?{'Content-Type':'application/json'}:{}),...(options.headers||{})};
  if (!['GET','HEAD'].includes(method) && !path.endsWith('/auth/login') && state.csrf) headers['X-CSRF-Token'] = state.csrf;
  let response;
  try {
    response = await fetch('/api'+path,{credentials:'same-origin',...options,method,headers});
  } catch (error) { throw new Error('Sem conexão com o servidor. Confira sua rede.'); }
  const result = await response.json().catch(()=>({}));
  if(!response.ok) {
    if(response.status===401 && !path.endsWith('/auth/login')) {
      state.user=null; state.csrf=''; state.cache.clear(); render();
    }
    let detail = result.detail;
    if (Array.isArray(detail)) detail = detail.map(x => x.msg).join(', ');
    throw new Error(typeof detail==='string'?detail:'Não foi possível concluir a operação.');
  }
  return result;
}
function cached(key, loader, ttl=45000) {
  const hit=state.cache.get(key);
  if (hit && Date.now()-hit.when<ttl) return Promise.resolve(hit.value);
  if (state.inflight.has(key)) return state.inflight.get(key);
  const running=loader().then(value=>{state.cache.set(key,{when:Date.now(),value});return value;})
  .finally(()=>state.inflight.delete(key));
  state.inflight.set(key,running);
  return running;
}
function dataFor(key) {
  const endpoint={finance:'transactions',team:'employees'}[key] || key;
  const path=key==='dashboard'||key==='bi'?'/'+key+'?days='+state.days : '/'+endpoint;
  return cached(key+(key==='dashboard'||key==='bi'?':'+state.days:''),()=>request(path));
}
function invalidate(...keys) {
  for(const k of [...state.cache.keys()]) if(keys.some(x=>k.startsWith(x))) state.cache.delete(k);
}
function navMarkup() {
  return available().map(([key,label,iconName,url])=>
    '<button class="nav-link '+(state.path===url?'active':'')+'" data-nav="'+url+'" aria-current="'+(state.path===url?'page':'false')+'">'+icon(iconName,18,'nav-icon')+'<span>'+label+'</span></button>').join('');
}
function layout() {
  const initials=(state.user.username||'U').slice(0,2).toUpperCase();
  return '<div class="app-shell"><header class="topbar"><div class="top-primary">'+
    '<a href="/dashboard" class="brand" data-nav="/dashboard" aria-label="Coffee BI">'+
      '<span class="brand-mark">'+icon('coffee',20)+'</span><span class="brand-name">Coffee <b>BI</b></span></a>'+
    '<nav class="topnav" aria-label="Navegação principal"><div class="nav-track">'+navMarkup()+'</div></nav>'+
    '<div class="top-actions"><div class="profile-summary"><span class="avatar">'+esc(initials)+'</span><span class="profile-copy"><strong>'+esc(state.user.username)+'</strong><small>'+esc(state.user.role)+'</small></span></div>'+
    '<button class="btn btn-ghost btn-icon" data-action="logout" title="Sair" aria-label="Sair">'+icon('logout',18)+'</button></div></div>'+
    '<nav class="mobile-nav" aria-label="Navegação móvel">'+navMarkup()+'</nav></header>'+
    '<main id="content" class="workspace" tabindex="-1"></main></div><div id="modal-host"></div>';
}
function pageHead(kicker,title,subtitle,actions='') {
  return '<div class="page-top"><div class="page-title"><div class="section-label">'+esc(kicker)+'</div><h1>'+esc(title)+'</h1><p>'+esc(subtitle)+'</p></div>'+
    '<div class="head-actions">'+actions+'</div></div>';
}
function periodSelect() {
  return '<select class="select" id="days" aria-label="Período de análise">'+
    [[7,'Últimos 7 dias'],[30,'Últimos 30 dias'],[90,'Últimos 90 dias'],[365,'Últimos 12 meses']]
    .map(([days,label])=>'<option value="'+days+'" '+(state.days===days?'selected':'')+'>'+label+'</option>').join('')+'</select>';
}
function stat(label,value,iconName,foot,tone='green') {
  return '<article class="stat-card"><header><span class="stat-label">'+esc(label)+'</span><span class="stat-ico tone-'+tone+'">'+icon(iconName,19)+'</span></header>'+
  '<div class="stat-value">'+esc(value)+'</div><div class="stat-foot"><span class="status-dot"></span>'+esc(foot)+'</div></article>';
}
function panel(title,subtitle,content) {
  return '<section class="panel"><div class="panel-header"><div><h2>'+esc(title)+'</h2><span class="panel-sub">'+esc(subtitle)+'</span></div></div>'+
  '<div class="panel-body">'+content+'</div></section>';
}
function skeleton(type) {
  // Cada seção mantém a anatomia visual do conteúdo real durante a primeira consulta.
  const stats='<div class="stats-grid loading-screen">'+Array(4).fill('<div class="stat-card"><div class="skeleton stat-skeleton"></div></div>').join('')+'</div>';
  const chart=panel('Carregando indicadores','Sincronizando dados','<div class="skeleton chart-skeleton"></div>');
  const tableRows=Array(6).fill('<div class="skeleton row-skeleton"></div>').join('');
  const records=panel('Carregando registros','Buscando informações',tableRows);
  const widget=panel('Carregando informações','',Array(3).fill('<div class="skeleton group-skeleton" style="height:42px;margin-bottom:14px"></div>').join(''));
  if(type==='dashboard'||type==='bi')return stats+'<div class="grid-main">'+chart+widget+'</div><div class="grid-two">'+widget+widget+'</div>';
  if(type==='products')return '<div class="panel"><div class="skeleton header-skeleton"></div><div class="skeleton group-skeleton" style="height:42px;margin-bottom:18px;max-width:360px"></div>'+tableRows+'</div>';
  if(type==='sales')return stats+records;
  if(type==='purchases')return '<div class="grid-two">'+widget+widget+'</div>'+records;
  if(type==='finance')return stats+records;
  if(type==='team')return '<div class="panel"><div class="skeleton header-skeleton"></div>'+
   Array(5).fill('<div style="display:flex;align-items:center;gap:16px;margin-bottom:15px"><div class="skeleton circle-skeleton"></div><div class="skeleton" style="height:18px;flex:1"></div><div class="skeleton pill-skeleton"></div></div>').join('')+'</div>';
  return records;
}
function lineChart(series) {
  if (!series?.length) return empty('Sem vendas no período','Registre uma venda para começar a visualizar seu faturamento.');
  const w=760,h=280,left=58,right=18,top=18,bottom=34;
  const vals=series.map(s=>Number(s.total)), rawMax=Math.max(...vals,1), max=Math.ceil(rawMax/100)*100 || 100;
  const x=i=>left+(i/Math.max(1,series.length-1))*(w-left-right);
  const y=v=>top+(1-v/max)*(h-top-bottom);
  const pts=vals.map((v,i)=>x(i).toFixed(1)+','+y(v).toFixed(1)).join(' ');
  const area=left+','+(h-bottom)+' '+pts+' '+x(vals.length-1)+','+(h-bottom);
  const guides=[0,.25,.5,.75,1].map(r=>{
    const gy=y(max*r),value=max*r;
    return '<g><line x1="'+left+'" x2="'+(w-right)+'" y1="'+gy+'" y2="'+gy+'" class="chart-grid"/><text x="'+(left-10)+'" y="'+(gy+4)+'" text-anchor="end" class="chart-label">'+esc(money(value).replace(',00',''))+'</text></g>';
  }).join('');
  const dots=vals.map((v,i)=>'<circle cx="'+x(i)+'" cy="'+y(v)+'" r="4" class="chart-dot"><title>'+esc(shortDate(series[i].data))+': '+esc(money(v))+'</title></circle>').join('');
  return '<div class="chart"><svg viewBox="0 0 '+w+' '+h+'" role="img" aria-label="Evolução do faturamento no período">'+
    '<defs><linearGradient id="fillChart" x1="0" y1="0" x2="0" y2="1"><stop class="chart-stop-a" stop-opacity=".26"/><stop offset="1" class="chart-stop-b" stop-opacity="0"/></linearGradient></defs>'+
    guides+'<polygon points="'+area+'" fill="url(#fillChart)"/><polyline points="'+pts+'" class="chart-line" fill="none"/>'+dots+
    '<text x="'+left+'" y="'+(h-7)+'" class="chart-date">'+esc(shortDate(series[0].data))+'</text>'+
    '<text x="'+(w-right)+'" y="'+(h-7)+'" text-anchor="end" class="chart-date">'+esc(shortDate(series[series.length-1].data))+'</text>'+
    '</svg></div>';
}
function bars(items,labelKey,valueKey,formatter=number) {
  if (!items?.length) return empty('Nenhum registro para comparar');
  const highest=Math.max(...items.map(item=>Number(item[valueKey])),1);
  return '<div class="mini-list">'+items.map((item,index)=>'<div class="list-line">'+
   '<span class="rank">'+(index+1)+'</span><div style="flex:1;min-width:0">'+
   '<div style="display:flex;gap:9px;align-items:center"><span class="list-name">'+esc(item[labelKey])+'</span>'+
   '<span class="list-value">'+esc(formatter(item[valueKey]))+'</span></div>'+
   '<div class="bar-track"><div class="bar-fill" style="width:'+Math.max(2,Number(item[valueKey])/highest*100)+'%"></div></div>'+
   '</div></div>').join('')+'</div>';
}
function table(headers,items) {
  return '<div class="table-wrap"><table><thead><tr>'+headers.map(h=>'<th>'+esc(h)+'</th>').join('')+
    '</tr></thead><tbody>'+items.join('')+'</tbody></table></div>';
}
function dashboardView(d,bi=false) {
  const actions=periodSelect();
  const header=pageHead(bi?'ANÁLISE GERENCIAL':'SEU ESPAÇO DE TRABALHO',
    bi?'Inteligência de negócio':'Visão geral',
    bi?'Indicadores do negócio para decisões baseadas em dados.':'Uma visão completa da operação da sua cafeteria.',actions);
  const stats='<div class="stats-grid">'+stat('Faturamento',money(d.faturamento),'trend','Período selecionado','green')+
    stat('Total de vendas',number(d.vendas),'receipt','Vendas registradas','blue')+
    stat('Ticket médio',money(d.ticket_medio),'ticket','Valor médio por pedido','orange')+
    stat('Produtos ativos',number(d.produtos_ativos),'box','Itens no catálogo','purple')+'</div>';
  const trends=panel('Evolução das vendas','Receita por dia',lineChart(d.serie));
  const top=panel('Mais vendidos','Ranking de produtos',bars(d.top_produtos,'nome','quantidade'));
  const methods=panel('Formas de pagamento','Distribuição de receitas',bars(d.pagamentos,'nome','total',money));
  const low=panel('Alertas de estoque','Itens que precisam de reposição',d.estoque_baixo.length?
    '<div class="mini-list">'+d.estoque_baixo.map(p=>'<div class="list-line"><span class="rank rank-alert">'+icon('alert',15)+'</span>'+
    '<span class="list-name">'+esc(p.nome)+'</span>'+tag(p.estoque_atual+' '+p.unidade,'warn')+'</div>').join('')+'</div>':
    empty('Estoque sob controle','Nenhum produto está abaixo do mínimo.'));
  const biStats=bi?'<div class="stats-grid">'+stat('Compras',money(d.compras),'purchases','Custos registrados','orange')+
    stat('Outras entradas',money(d.entradas),'arrowUp','Lançamentos financeiros','green')+
    stat('Outras saídas',money(d.saidas),'arrowDown','Lançamentos financeiros','red')+
    stat('Saldo operacional',money(d.saldo_operacional),'wallet','Receitas menos saídas','blue')+'</div>':'';
  return header+stats+biStats+'<div class="grid-main">'+trends+top+'</div><div class="grid-two">'+methods+low+'</div>';
}
function productsView(data) {
  const rows=data.filter(p=>[p.nome,p.categoria].some(x=>x?.toLowerCase().includes(state.search.toLowerCase())))
    .map(p=>'<tr><td><strong>'+esc(p.nome)+'</strong></td><td>'+esc(p.categoria)+'</td><td>'+money(p.preco_venda)+'</td>'+
      '<td>'+esc(p.estoque_atual)+' '+esc(p.unidade)+'</td><td>'+tag(p.estoque_atual<=p.estoque_minimo?'Baixo':'Disponível',p.estoque_atual<=p.estoque_minimo?'warn':'')+'</td>'+
      '<td>'+(manager()?'<button class="btn btn-secondary btn-sm" data-action="edit-product" data-id="'+p.id+'">'+icon('edit',15)+'<span>Editar</span></button>':'—')+'</td></tr>');
  return pageHead('CATÁLOGO','Produtos & estoque','Gerencie preços, categorias e quantidades com atualização imediata.',
    manager()?'<button class="btn btn-primary" data-action="new-product">'+icon('plus',16)+'<span>Novo produto</span></button>':'')+
    panel('Seu catálogo',data.length+' produtos ativos',
     '<div class="toolbar"><label class="search-box" for="search">'+icon('search',17)+'<input id="search" placeholder="Buscar produto ou categoria..." aria-label="Buscar produtos" value="'+esc(state.search)+'"></label></div>'+
     (rows.length?table(['Produto','Categoria','Preço de venda','Em estoque','Situação','Ações'],rows):
       empty('Nenhum produto encontrado','Cadastre produtos para começar a operar.')));
}
function salesView(rows) {
  const items=rows.map(s=>'<tr><td><strong>#'+s.id+'</strong></td><td>'+shortDate(s.data)+'</td>'+
   '<td>'+esc(s.hora)+'</td><td>'+esc(s.metodo_pagamento)+'</td><td>'+esc(s.itens.reduce((n,x)=>n+x.quantidade,0))+'</td>'+
   '<td><strong>'+money(s.valor_total)+'</strong></td></tr>');
  const total=rows.reduce((sum,s)=>sum+Number(s.valor_total),0);
  return pageHead('OPERAÇÃO','Vendas','Registre pedidos e acompanhe todas as vendas realizadas.',
   '<button class="btn btn-primary" data-action="new-sale">'+icon('plus',16)+'<span>Registrar venda</span></button>')+
   '<div class="stats-grid">'+stat('Vendas recentes',number(rows.length),'receipt','Últimos 300 registros','blue')+
   stat('Total da listagem',money(total),'trend','Receita bruta listada','green')+'</div>'+
   panel('Histórico de vendas','Registros mais recentes',items.length?
    table(['Número','Data','Horário','Pagamento','Itens','Total'],items):
    empty('Nenhuma venda ainda','Clique em Registrar venda para efetuar seu primeiro pedido.'));
}
function purchasesView(rows) {
  const items=rows.map(c=>'<tr><td><strong>#'+c.id+'</strong></td><td>'+shortDate(c.data)+'</td>'+
   '<td>'+esc(c.fornecedor)+'</td><td>'+esc(c.metodo_pagamento)+'</td>'+
   '<td>'+esc(c.itens.reduce((n,x)=>n+x.quantidade,0))+'</td><td><strong>'+money(c.valor_total)+'</strong></td></tr>');
  return pageHead('SUPRIMENTOS','Compras','Controle a entrada de mercadorias e custos de aquisição.',
     '<button class="btn btn-primary" data-action="new-purchase">'+icon('plus',16)+'<span>Nova compra</span></button>')+
    panel('Histórico de compras','Últimos pedidos aos fornecedores',items.length?
      table(['Número','Data','Fornecedor','Pagamento','Itens','Total'],items):empty('Sem compras registradas'));
}
function financeView(rows) {
  const inc=rows.filter(x=>x.tipo==='entrada').reduce((n,x)=>n+Number(x.valor),0);
  const out=rows.filter(x=>x.tipo==='saída').reduce((n,x)=>n+Number(x.valor),0);
  const items=rows.map(t=>'<tr><td>'+shortDate(t.data)+'</td><td><strong>'+esc(t.descricao)+'</strong></td>'+
  '<td>'+esc(t.categoria)+'</td><td>'+tag(t.tipo,t.tipo==='saída'?'bad':'')+'</td>'+
  '<td><strong>'+money(t.valor)+'</strong></td><td><button class="btn btn-danger btn-sm" data-action="delete-transaction" data-id="'+t.id+'">'+icon('trash',15)+'<span>Excluir</span></button></td></tr>');
  return pageHead('CONTROLE FINANCEIRO','Financeiro','Lançamentos avulsos de entrada e saída de caixa.',
   '<button class="btn btn-primary" data-action="new-transaction">'+icon('plus',16)+'<span>Novo lançamento</span></button>')+
   '<div class="stats-grid">'+stat('Entradas',money(inc),'arrowUp','Lançamentos avulsos','green')+
   stat('Saídas',money(out),'arrowDown','Lançamentos avulsos','red')+
   stat('Saldo',money(inc-out),'wallet','Entradas menos saídas','blue')+'</div>'+
   panel('Extrato','Últimos 500 lançamentos',items.length?
      table(['Data','Descrição','Categoria','Tipo','Valor','Ações'],items):empty('Sem lançamentos no extrato'));
}
function teamView(rows) {
  const items=rows.map(f=>'<tr><td><strong>'+esc(f.nome)+'</strong></td><td>'+esc(f.cargo)+'</td>'+
    '<td>'+esc(f.email||'—')+'</td><td>'+esc(f.telefone||'—')+'</td>'+
    '<td>'+tag(f.ativo?'Ativo':'Inativo',f.ativo?'':'warn')+'</td>'+
    '<td><button class="btn btn-secondary btn-sm" data-action="edit-employee" data-id="'+f.id+'">'+icon('edit',15)+'<span>Editar</span></button></td></tr>');
  return pageHead('PESSOAS','Equipe','Cadastre funcionários e gerencie permissões de acesso.',
    '<button class="btn btn-secondary" data-action="new-user">'+icon('user',16)+'<span>Criar acesso</span></button><button class="btn btn-primary" data-action="new-employee">'+icon('plus',16)+'<span>Novo funcionário</span></button>')+
    panel('Colaboradores',rows.length+' registros',items.length?
      table(['Nome','Cargo','E-mail','Telefone','Situação','Ações'],items):empty('Nenhum funcionário cadastrado'));
}
function pageKey() {
  const match=available().find(([, , ,url])=>url===state.path);
  return match?match[0]:'dashboard';
}
function render() {
  if(!state.user) {root.innerHTML=loginView();return;}
  root.innerHTML=layout();
  paintPage();
}
function paintPage() {
  if(!state.user) return;
  const key=pageKey();
  const host=document.querySelector('#content');
  if(!host) return;
  const ck=key+(key==='dashboard'||key==='bi'?':'+state.days:'');
  const cachedData=state.cache.get(ck);
  if(cachedData) {showPage(key,cachedData.value);return;}
  host.innerHTML=pageHead('COFFEE BI',key==='bi'?'Inteligência':key==='dashboard'?'Visão geral':available().find(x=>x[0]===key)?.[1]||'Carregando',
    'Preparando os dados da sua cafeteria...')+skeleton(key);
  dataFor(key).then(data=>{
    if(pageKey()===key && (key!=='dashboard'&&key!=='bi'||ck.endsWith(':'+state.days))) showPage(key,data);
  }).catch(e=>{if(pageKey()===key){host.innerHTML=pageHead('COFFEE BI','Erro ao carregar','Não foi possível obter esta página.')+
    panel('Falha de carregamento','Confira a conexão','<p>'+esc(e.message)+'</p><button class="btn btn-primary" data-action="retry">Tentar novamente</button>');}});
}
function showPage(key,data) {
  const host=document.querySelector('#content');
  if(!host)return;
  const fn={dashboard:()=>dashboardView(data),bi:()=>dashboardView(data,true),products:()=>productsView(data),
    sales:()=>salesView(data),purchases:()=>purchasesView(data),finance:()=>financeView(data),team:()=>teamView(data)};
  host.innerHTML=fn[key]?.() || '';
}
function loginView() {
  return '<div class="auth"><section class="auth-art"><div class="brand brand-inverse"><span class="brand-mark">'+icon('coffee',21)+'</span><span class="brand-name">Coffee <b>BI</b></span></div>'+
  '<div class="auth-copy"><span class="eyebrow">Gestão inteligente para cafeterias</span>'+
  '<h1>Operação clara.<br><em>Decisões melhores.</em></h1><p>Vendas, estoque, compras, caixa e indicadores em uma experiência única, rápida e simples de operar.</p>'+
  '<div class="auth-preview"><div class="preview-card">'+icon('dashboard',20)+'<div><small>Visibilidade</small><strong>360°</strong><i>Operação centralizada</i></div></div>'+
  '<div class="preview-card">'+icon('intelligence',20)+'<div><small>Inteligência</small><strong>BI</strong><i>Dados para decidir</i></div></div></div></div>'+
  '<footer>COFFEE BI · GESTÃO & INTELIGÊNCIA</footer></section>'+
  '<section class="auth-form-wrap"><div class="auth-panel"><span class="login-chip">'+icon('coffee',15)+' Coffee BI</span>'+
  '<h2>Bem-vindo de volta</h2><p class="muted">Entre para acessar a operação da sua cafeteria.</p>'+
  (state.error?'<div class="login-error" role="alert">'+esc(state.error)+'</div>':'')+
  '<form id="login-form"><div class="field"><label for="username">Usuário</label>'+
  '<input id="username" name="username" autocomplete="username" required placeholder="Digite seu usuário" maxlength="100"></div>'+
  '<div class="field"><label for="password">Senha</label><div class="password-row">'+
  '<input id="password" name="password" autocomplete="current-password" type="'+(state.showPassword?'text':'password')+'" required placeholder="Digite sua senha">'+
  '<button type="button" class="pass-toggle" data-action="toggle-password" aria-label="Mostrar ou ocultar senha">'+(state.showPassword?'Ocultar':'Mostrar')+'</button>'+
  '</div></div><button type="submit" class="btn btn-primary btn-login" '+(state.loginBusy?'disabled':'')+'>'+
  (state.loginBusy?'Entrando...':'Entrar no Coffee BI '+icon('arrowRight',17))+'</button></form>'+
  '<p class="login-note">Acesso protegido por sessão segura. Somente usuários autorizados.</p></div></section></div>';
}
function field(name,label,value='',type='text',attrs='',optional=false) {
  return '<div class="field"><label for="fld-'+name+'">'+esc(label)+'</label>'+
   '<input id="fld-'+name+'" name="'+name+'" type="'+type+'" value="'+esc(value)+'" '+attrs+(optional?'':' required')+'></div>';
}
function selectField(name,label,options,selected='') {
  return '<div class="field"><label for="fld-'+name+'">'+esc(label)+'</label>'+
    '<select name="'+name+'" id="fld-'+name+'">'+options.map(opt=>'<option value="'+esc(opt)+'" '+(opt===selected?'selected':'')+'>'+esc(opt)+'</option>').join('')+'</select></div>';
}
function modal(title,body,submitLabel='Salvar',formName='') {
  state.modal={title,body,submitLabel,formName}; drawModal();
}
function drawModal() {
  const host=document.querySelector('#modal-host');
  if(!host||!state.modal)return;
  host.innerHTML='<div class="modal-backdrop" role="presentation"><section class="modal" role="dialog" aria-modal="true" aria-labelledby="modal-title">'+
    '<div class="modal-head"><div><span class="modal-kicker">Coffee BI</span><h2 id="modal-title">'+esc(state.modal.title)+'</h2></div><button class="btn btn-ghost btn-icon" data-action="close-modal" aria-label="Fechar">'+icon('close',18)+'</button></div>'+
    '<form id="dialog-form" data-form="'+esc(state.modal.formName)+'">'+state.modal.body+
    '<div class="modal-actions"><button type="button" class="btn btn-secondary" data-action="close-modal">Cancelar</button>'+
    '<button class="btn btn-primary" type="submit">'+esc(state.modal.submitLabel)+'</button></div></form></section></div>';
  host.querySelector('input,select,button')?.focus();
}
function closeModal() {state.modal=null; state.cart=[];document.querySelector('#modal-host')?.replaceChildren();}
function productForm(existing) {
  const p=existing||{};
  modal(existing?'Editar produto':'Novo produto','<input type="hidden" name="id" value="'+esc(p.id||'')+'">'+
   '<div class="modal-grid">'+field('nome','Nome do produto',p.nome||'')+
   field('categoria','Categoria',p.categoria||'')+
   field('preco_venda','Preço de venda (R$)',p.preco_venda??0,'number','step="0.01" min="0"')+
   field('custo_unitario','Custo (R$)',p.custo_unitario??0,'number','step="0.01" min="0"')+
   field('estoque_atual','Estoque atual',p.estoque_atual??0,'number','step="1" min="0"')+
   field('estoque_minimo','Estoque mínimo',p.estoque_minimo??0,'number','step="1" min="0"')+
   field('unidade','Unidade',p.unidade||'un')+'</div>','Salvar produto','product');
}
function cartForm(mode) {
  state.cartMode=mode;
  const label=mode==='purchase'?'Compra':'Venda';
  modal('Registrar '+label.toLowerCase(),(mode==='purchase'?field('fornecedor','Fornecedor'):'')+
   selectField('metodo_pagamento','Forma de pagamento',['pix','dinheiro','cartão de crédito','cartão de débito','transferência','boleto'])+
   field('data','Data',today(),'date')+
   '<div class="field"><label>Adicionar itens</label><div class="inline-fields">'+
   '<div class="field"><label for="item-product">Produto</label><select id="item-product" aria-label="Produto"></select></div>'+
   '<div class="field"><label for="item-qty">Qtd.</label><input id="item-qty" type="number" min="1" value="1"></div>'+
   (mode==='purchase'?'<div class="field"><label for="item-price">Custo (R$)</label><input id="item-price" type="number" step=".01" min="0" value="0"></div>':'<div style="align-self:end"><button class="btn btn-secondary" type="button" data-action="cart-add">Adicionar</button></div>')+
   '</div></div>'+(mode==='purchase'?'<button class="btn btn-secondary" type="button" data-action="cart-add">Adicionar item</button>':'')+
   '<div id="cart-area"></div>','Finalizar '+label.toLowerCase(),mode);
  dataFor('products').then(products=>{
    const sel=document.querySelector('#item-product');
    if(sel)sel.innerHTML=products.map(p=>'<option value="'+p.id+'">'+esc(p.nome)+' · '+money(p.preco_venda)+'</option>').join('');
  }).catch(e=>toast(e.message));
  updateCart();
}
function updateCart() {
  const node=document.querySelector('#cart-area');
  if(!node)return;
  if(!state.cart.length){node.innerHTML='<div class="cart"><span class="muted">Nenhum item adicionado</span></div>';return;}
  const products=state.cache.get('products')?.value||[];
  node.innerHTML='<div class="cart">'+state.cart.map((item,i)=>{
    const p=products.find(x=>x.id===item.id_produto);
    return '<div class="cart-row"><span>'+esc(p?.nome||'Produto')+' · '+item.quantidade+' × '+money(item.preco_unitario)+'</span>'+
       '<button type="button" class="btn-link danger-link" data-action="cart-remove" data-id="'+i+'">Remover</button></div>';
  }).join('')+'<div class="cart-row" style="border-top:1px solid #e0e9e3;padding-top:10px"><strong>Total</strong><strong>'+
  money(state.cart.reduce((x,item)=>x+item.quantidade*item.preco_unitario,0))+'</strong></div></div>';
}
function transactionForm() {
  modal('Novo lançamento',selectField('tipo','Tipo',['entrada','saída'])+
   field('descricao','Descrição')+field('categoria','Categoria')+
   field('valor','Valor (R$)','0','number','step=".01" min=".01"')+
   field('data','Data',today(),'date'),'Registrar lançamento','transaction');
}
function employeeForm(existing) {
  const p=existing||{};
  modal(existing?'Editar funcionário':'Novo funcionário',
    '<input type="hidden" name="id" value="'+esc(p.id||'')+'">'+
    field('nome','Nome completo',p.nome||'')+
    selectField('cargo','Cargo',['funcionario','Gerente','admin'],p.cargo||'funcionario')+
    '<div class="modal-grid">'+field('email','E-mail',p.email||'','email','',true)+
    field('telefone','Telefone',p.telefone||'','text','',true)+'</div>'+
    selectField('ativo','Status',['true','false'],String(p.ativo??true)),
    'Salvar funcionário','employee');
}
function newUserForm() {
  modal('Criar acesso ao sistema',field('nome_usuario','Nome de usuário')+
    field('senha','Senha (mínimo 10 caracteres)','','password','minlength="10" autocomplete="new-password"')+
    selectField('nivel_acesso','Permissão',['funcionario','Gerente','admin']),
    'Criar usuário','user');
}
function navigate(url,replace=false) {
  if(state.path===url)return;
  const allowed=available().find(x=>x[3]===url);
  if(!allowed)url='/dashboard';
  state.path=url;state.search='';
  if(replace)history.replaceState({},'',url);else history.pushState({},'',url);
  render();
  document.querySelector('#content')?.focus({preventScroll:true});
  window.scrollTo({top:0,behavior:'instant'});
}
async function mutate(path,method,data,keys,success) {
  await request(path,{method,body:data?JSON.stringify(data):undefined});
  invalidate(...keys);
  closeModal();
  toast(success);
  paintPage();
}
document.addEventListener('click',async e=>{
  const nav=e.target.closest('[data-nav]');
  if(nav){e.preventDefault();navigate(nav.dataset.nav);return;}
  if(e.target.classList.contains('modal-backdrop')){closeModal();return;}
  const btn=e.target.closest('[data-action]');
  if(!btn)return;
  const action=btn.dataset.action;
  try{
    if(action==='close-modal'){closeModal();return;}
    if(action==='toggle-password'){state.showPassword=!state.showPassword;const p=document.querySelector('#password');if(p){p.type=state.showPassword?'text':'password';btn.textContent=state.showPassword?'Ocultar':'Mostrar';p.focus();}return;}
    if(action==='logout'){await request('/auth/logout',{method:'POST'});state.user=null;state.csrf='';state.cache.clear();history.replaceState({},'','/');render();return;}
    if(action==='retry'){invalidate(pageKey());paintPage();return;}
    if(action==='new-product'){productForm();return;}
    if(action==='edit-product'){productForm((await dataFor('products')).find(x=>x.id===Number(btn.dataset.id)));return;}
    if(action==='new-sale'){cartForm('sale');return;}
    if(action==='new-purchase'){cartForm('purchase');return;}
    if(action==='new-transaction'){transactionForm();return;}
    if(action==='new-employee'){employeeForm();return;}
    if(action==='edit-employee'){employeeForm((await dataFor('team')).find(x=>x.id===Number(btn.dataset.id)));return;}
    if(action==='new-user'){newUserForm();return;}
    if(action==='cart-remove'){state.cart.splice(Number(btn.dataset.id),1);updateCart();return;}
    if(action==='cart-add'){
      const id=Number(document.querySelector('#item-product')?.value);
      const quantity=Number(document.querySelector('#item-qty')?.value);
      const p=(await dataFor('products')).find(x=>x.id===id);
      const price=state.cartMode==='purchase'?Number(document.querySelector('#item-price')?.value):p?.preco_venda;
      if(!p||!Number.isInteger(quantity)||quantity<1||!Number.isFinite(price)||price<0)throw new Error('Confira o produto, quantidade e preço.');
      state.cart.push({id_produto:id,quantidade,preco_unitario:price});updateCart();return;
    }
    if(action==='delete-transaction') {
      if(!confirm('Excluir este lançamento? Esta ação não pode ser desfeita.'))return;
      await mutate('/transactions/'+Number(btn.dataset.id),'DELETE',null,['finance','bi'],'Lançamento excluído.');
    }
  }catch(error){toast(error.message);}
});
document.addEventListener('submit',async e=>{
  if(e.target.id==='login-form'){
    e.preventDefault();const values=new FormData(e.target);state.error=null;state.loginBusy=true;
    const username=values.get('username'),password=values.get('password');render();
    try {
      const result=await request('/auth/login',{method:'POST',body:JSON.stringify({username,password})});
      state.user=result.user;state.csrf=result.csrf;state.loginBusy=false;
      if(state.path==='/'||!pages.some(x=>x[3]===state.path))state.path='/dashboard';
      history.replaceState({},'',state.path);render();
    }catch(err){state.error=err.message;state.loginBusy=false;render();}
    return;
  }
  if(e.target.id!=='dialog-form')return;
  e.preventDefault();
  const form=e.target,values=Object.fromEntries(new FormData(form).entries()),kind=form.dataset.form;
  const submit=form.querySelector('[type="submit"]');submit.disabled=true;
  try{
    if(kind==='product'){
      const id=values.id;delete values.id;
      for(const key of ['preco_venda','custo_unitario','estoque_atual','estoque_minimo'])values[key]=Number(values[key]);
      await mutate('/products'+(id?'/'+id:''),id?'PUT':'POST',values,['products','dashboard','bi'],'Produto salvo.');
    }
    if(['sale','purchase'].includes(kind)){
      if(!state.cart.length)throw new Error('Adicione ao menos um item.');
      const payload={data:values.data,metodo_pagamento:values.metodo_pagamento,
        itens:state.cart.map(({id_produto,quantidade,preco_unitario})=>kind==='purchase'?
          {id_produto,quantidade,preco_unitario}:{id_produto,quantidade})};
      if(kind==='purchase') payload.fornecedor=values.fornecedor;
      await mutate(kind==='sale'?'/sales':'/purchases','POST',payload,
        ['sales','purchases','dashboard','bi','products'],kind==='sale'?'Venda registrada com sucesso.':'Compra registrada e estoque atualizado.');
    }
    if(kind==='transaction'){
      values.valor=Number(values.valor);
      await mutate('/transactions','POST',values,['finance','bi'],'Lançamento criado.');
    }
    if(kind==='employee'){
      const id=values.id;delete values.id;values.ativo=values.ativo==='true';
      await mutate('/employees'+(id?'/'+id:''),id?'PUT':'POST',values,['team'],'Funcionário salvo.');
    }
    if(kind==='user'){
      await mutate('/users','POST',values,['team'],'Acesso criado com sucesso.');
    }
  }catch(error){toast(error.message);}finally{submit.disabled=false;}
});
document.addEventListener('change',e=>{
  if(e.target.id==='days') {
    state.days=Number(e.target.value);paintPage();
  }
});
document.addEventListener('input',e=>{
  if(e.target.id==='search'){
    state.search=e.target.value;
    const pos=e.target.selectionStart;
    showPage('products',state.cache.get('products')?.value||[]);
    const search=document.querySelector('#search');search?.focus();
    search?.setSelectionRange(pos,pos);
  }
});
document.addEventListener('keydown',e=>{if(e.key==='Escape' && state.modal)closeModal();});
document.addEventListener('mouseover',e=>{
  const nav=e.target.closest('[data-nav]');if(!nav||!state.user)return;
  const key=available().find(x=>x[3]===nav.dataset.nav)?.[0];
  if(key)dataFor(key).catch(()=>{});
});
window.addEventListener('popstate',()=>{state.path=location.pathname;render();});
(async()=>{
  try{
    const r=await request('/auth/me');state.user=r.user;state.csrf=r.csrf;
    if(state.path==='/'||!pages.some(x=>x[3]===state.path)){
      state.path='/dashboard';history.replaceState({},'','/dashboard');
    }
  }catch(e){state.user=null;state.csrf='';}
  render();
})();
