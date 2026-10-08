# Coffee BI — Nova interface (SPA + FastAPI)

Esta implementação foi adicionada **sem excluir o aplicativo Streamlit existente**, sobre a branch `codespace-vigilant-potato-69vpjr5w7v6c54vq`. A branch `main` não foi usada como base e não deve ser alterada por esta PR.

## Instalação local

Python 3.11 ou superior:

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
# source .venv/bin/activate
pip install -r requirements-api.txt
# Windows: copy .env.example .env
# Linux/macOS: cp .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Copie o segredo aleatório gerado para `SESSION_SECRET` no arquivo `.env`.
O arquivo `.env` real **não deve ser versionado**, por conter credenciais.

Configure a primeira conta, com a senha de sua escolha (sem usuário padrão inseguro):

```bash
python -m api.bootstrap_admin --username admin
uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload
```

Abra http://127.0.0.1:8000. A documentação interativa da API fica em http://127.0.0.1:8000/api/docs.

Se você já possui um banco SQLite, faça backup e reutilize o arquivo `data/cafeteria.db`, que é a localização da branch de origem. Em PostgreSQL, mantenha `DATABASE_URL` apontando ao mesmo banco. **Não execute `init_db.py` antigo em produção**: ele cria dados e credenciais de demonstração.

## Escopo implementado

- Login redesenhado, com sessão assinada em cookie HttpOnly, proteção CSRF em operações de escrita, controle de acesso no backend e criação explícita do administrador.
- Navbar horizontal responsiva e navegação SPA via History API, sem recarga total.
- Cache em memória por recurso, deduplicação de chamadas, prefetch ao interagir com a navegação e invalidação após alterações.
- Skeletons desenhados para indicadores, gráficos, filtros, catálogo, vendas, compras, financeiro e equipe.
- Dashboard e BI ligados aos dados reais; gráficos de faturamento, vendas por pagamento, alertas de estoque e ranking de produtos.
- Produtos: listagem, cadastro, edição e arquivamento lógico.
- Vendas: registro de pedidos e baixa de estoque em uma só transação, com rejeição por estoque insuficiente.
- Compras: lançamento de fornecedores, entrada de estoque e cálculo de custo médio ponderado.
- Financeiro: lançamentos avulsos, extrato e indicadores.
- Equipe: funcionários e criação de acesso com papéis `admin`, `Gerente`, `funcionario`.
- Banco SQLAlchemy original preservado; o Streamlit antigo continua disponível.

## Qualidade

```bash
pip install -r requirements-dev.txt
pytest -q tests/test_api_spa.py
node --check web/app.js
```

O frontend utiliza JavaScript nativo, HTML e CSS sem instalar um segundo runtime para o cliente. O Uvicorn atende tanto os arquivos estáticos quanto `/api/*` na mesma origem, simplificando cookies e CSRF.

## Estrutura

```text
api/main.py                 FastAPI: segurança, endpoints, dashboards
api/bootstrap_admin.py      provisionamento seguro inicial
web/index.html              ponto de entrada
web/app.js                  navegação, componentes e estado do cliente
web/styles.css              design system, responsividade e skeletons
tests/test_api_spa.py       testes funcionais da API
requirements-api.txt        dependências do servidor
requirements-dev.txt        ferramentas de teste
Dockerfile.api              imagem do serviço (configurar HTTPS)
.env.example                modelo de variáveis sem segredos
```

## Produção — cuidados obrigatórios

Configure `APP_ENV=production`, `SESSION_SECRET` permanente (32+ caracteres), `PUBLIC_ORIGIN` e HTTPS em proxy reverso. Faça backup automático do banco e migrações com Alembic antes de mudanças futuras. Use armazenamento persistente: SQLite em disco efêmero de hospedagem perde dados. O limitador de login atual é em memória por processo; para múltiplos workers, use armazenamento compartilhado (ex.: Redis). Atualize senhas legadas fracas criadas pela versão de demonstração.

**Limitações:** o projeto modernizado é um ERP funcional para os módulos descritos, não substitui sistemas homologados de NFC-e, TEF, NF-e, contabilidade ou gestão fiscal. Nenhuma integração fiscal ou de adquirente é simulada como se existisse. Persistência e autenticação devem ser testadas no seu ambiente antes do uso com dados reais.

Para comparar sem perder código: rode `streamlit run app.py` para a interface antiga e `uvicorn api.main:app` para a nova.
