/** Integration test for actual browser-side submit wiring, without a browser. */
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

function harness() {
  const source=readFileSync('web/app.js','utf8');
  const cutoff=source.lastIndexOf('(async()=>{');
  assert.ok(cutoff>0,'App bootstrap boundary missing');
  const handlers={};
  const root={innerHTML:''};
  const toast={textContent:'',classList:{add(){},remove(){}}};
  const modalHost={innerHTML:'',replaceChildren(){this.innerHTML='';},querySelector(){return {focus(){}};}};
  const content={innerHTML:''};
  const calls=[];
  const created={id:51,nome:'Cold Brew',categoria:'Cafés',preco_venda:18.5,
    custo_unitario:4.3,estoque_atual:12,estoque_minimo:3,unidade:'un',ativo:true};
  let success=true;
  const fakeDocument={
    querySelector(selector){
      if(selector==='#root')return root;
      if(selector==='#toast')return toast;
      if(selector==='#modal-host')return modalHost;
      if(selector==='#content')return content;
      return null;
    },
    getElementById(){return null;},
    addEventListener(name,listener){handlers[name]=listener;},
  };
  class TestFormData {
    constructor(form){this.form=form;}
    *entries(){yield*Object.entries(this.form.values);}
  }
  const context=vm.createContext({
    document:fakeDocument,
    window:{addEventListener(){},innerWidth:1280,innerHeight:800},
    history:{replaceState(){},pushState(){}},
    location:{pathname:'/products'},
    Intl,Date,Math,Number,String,Map,Set,Array,Object,JSON,Error,Promise,
    FormData:TestFormData,
    fetch:async (path,options)=>{
      calls.push({path,method:options.method,headers:options.headers,body:options.body});
      if(!success)return {ok:false,status:403,json:async()=>({detail:'Sem permissão'})};
      if(path==='/api/products'&&options.method==='POST')
        return {ok:true,status:201,json:async()=>created};
      if(path==='/api/products/51'&&options.method==='PUT')
        return {ok:true,status:200,json:async()=>({...created,...JSON.parse(options.body)})};
      if(path==='/api/products/51'&&options.method==='DELETE')
        return {ok:true,status:200,json:async()=>({ok:true})};
      if(path==='/api/products'&&options.method==='GET')
        return {ok:true,status:200,json:async()=>[created]};
      throw Error('Unexpected HTTP call '+options.method+' '+path);
    },
    setTimeout:()=>1,clearTimeout(){},
    confirm:()=>true,
    console,
  });
  vm.runInContext(source.slice(0,cutoff),context);
  vm.runInContext("state.user={username:'admin',role:'admin'};state.csrf='test-token';state.path='/products';",context);
  return {context,handlers,root,toast,modalHost,content,calls,setSuccess(value){success=value;}};
}
function form(values) {
  const feedback={textContent:''};
  const submit={disabled:false};
  return {
    id:'dialog-form',dataset:{form:'product'},values,
    checkValidity:()=>true,reportValidity(){},
    querySelector(sel){
      if(sel==='[type="submit"]')return submit;
      if(sel==='.form-feedback')return feedback;
      return null;
    },
    feedback,submit,
  };
}

test('novo produto: clique mostra form, submit faz POST, GET confirma, tabela atualiza',async()=>{
  const h=harness();
  vm.runInContext('productForm()',h.context);
  assert.match(h.modalHost.innerHTML,/data-form="product"/);
  assert.match(h.modalHost.innerHTML,/<form id="dialog-form" novalidate/);
  assert.match(h.modalHost.innerHTML,/type="submit"/);
  const f=form({
    id:'',nome:'Cold Brew',categoria:'Cafés',preco_venda:'18,50',
    custo_unitario:'4,30',estoque_atual:'12',estoque_minimo:'3',unidade:'un',
  });
  let prevented=false;
  await h.handlers.submit({target:f,preventDefault(){prevented=true;}});
  assert.equal(prevented,true);
  assert.equal(f.submit.disabled,false);
  assert.equal(h.calls.length,2);
  assert.deepEqual(h.calls.map(x=>[x.method,x.path]),[
    ['POST','/api/products'],['GET','/api/products']
  ]);
  const posted=JSON.parse(h.calls[0].body);
  assert.equal(posted.nome,'Cold Brew');
  assert.equal(posted.preco_venda,18.5);
  assert.equal(posted.custo_unitario,4.3);
  assert.equal(h.calls[0].headers['X-CSRF-Token'],'test-token');
  assert.match(h.content.innerHTML,/Cold Brew/);
  assert.match(h.toast.textContent,/criado com sucesso/);
});

test('erro HTTP no POST não anuncia sucesso nem fecha modal',async()=>{
  const h=harness();h.setSuccess(false);
  vm.runInContext('productForm()',h.context);
  const f=form({
    id:'',nome:'Cold Brew',categoria:'Cafés',preco_venda:'18,50',
    custo_unitario:'4,30',estoque_atual:'12',estoque_minimo:'3',unidade:'un',
  });
  await h.handlers.submit({target:f,preventDefault(){}});
  assert.equal(h.calls.length,1);
  assert.equal(h.calls[0].method,'POST');
  assert.match(f.feedback.textContent,/HTTP 403/);
  assert.match(h.modalHost.innerHTML,/dialog-form/);
});

test('os métodos dos formulários e ações existem com caminhos REST corretos',()=>{
  const source=readFileSync('web/app.js','utf8');
  for(const token of [
    "await saveProduct(values,id)",
    "id?'PUT':'POST'",
    "'/sales':'/purchases','POST'",
    "if(action==='archive-product')",
    "if(action==='archive-employee')",
    "data-action=\"table-sort\"",
    "data-action=\"table-page\"",
    "function smartSelect",
    "function openDropdown",
  ])assert.ok(source.includes(token),token);
});


test('editar e arquivar: PUT e DELETE realmente saem do cliente HTTP',async()=>{
  const h=harness();
  const f=form({
    id:'51',nome:'Cold Brew Premium',categoria:'Cafés',preco_venda:'20,00',
    custo_unitario:'5,00',estoque_atual:'15',estoque_minimo:'4',unidade:'un',
  });
  await h.handlers.submit({target:f,preventDefault(){}});
  assert.deepEqual(h.calls.map(x=>[x.method,x.path]),[
    ['PUT','/api/products/51'],['GET','/api/products']
  ]);
  h.calls.length=0;
  const btn={
    dataset:{action:'archive-product',id:'51'},
    closest(){return null;},
  };
  const target={
    classList:{contains:()=>false},
    closest(selector){return selector==='[data-action]'?btn:null;},
  };
  await h.handlers.click({target,preventDefault(){}});
  assert.equal(h.calls[0].method,'DELETE');
  assert.equal(h.calls[0].path,'/api/products/51');
});
