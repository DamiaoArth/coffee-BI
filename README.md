# Coffee BI — versão moderna (FastAPI + Firebase)

**A nova aplicação web já não usa SQLite/PostgreSQL para operar.** O banco é **Cloud Firestore (Firebase)**, com acesso exclusivo pelo backend FastAPI.

Guia para configurar Firebase, executar, usar emulador e migrar dados SQL existentes: [docs/SPA.md](docs/SPA.md).

    python -m pip install -r requirements-api.txt
    # Configure FIREBASE_PROJECT_ID, credenciais do Firebase e SESSION_SECRET no .env
    python -m api.bootstrap_admin --username admin
    uvicorn api.main:app --reload --port 8000

A aplicação web fica em http://localhost:8000; a API em /api/docs.
A branch original com Streamlit e seu banco SQL permanece abaixo, apenas como versão legada.

---

# ERP Cafeteria

Sistema de gestão e BI para cafeteria: vendas, produtos/estoque, compras,
financeiro, equipe e relatórios.

## Executar

```bash
pip install -r requirements.txt
python init_db.py      # opcional: cria dados de exemplo
streamlit run app.py
```

Contas padrão criadas no primeiro acesso: `admin`, `gerente`, `funcionario`
(senha = nome do usuário + `123`). Troque as senhas em Equipe > Acessos.

## Estrutura

```
app.py              login + visão geral
pages/              Vendas, Produtos, Compras, Financeiro, Funcionarios, BI_Dashboard
ui/                 design system
  icons.py          registro de ícones (SVG inline + equivalente Material)
  theme.py          tokens de cor/tipografia e CSS global
  components.py     page_header, section, kpi_card, notice, badge, empty_state, navs
  charts.py         tema Plotly unificado
  format.py         formatação pt-BR (moeda, data, percentual)
  page.py           setup_page: config, tema, controle de acesso, sidebar
config/ models/ services/    camada de dados e regras (inalterada)
.streamlit/config.toml       tema fixo da aplicação
```

## Temas

O app segue o tema claro ou escuro escolhido pelo usuário (menu ⋮ > Settings,
ou a preferência do sistema). As duas paletas da marca estão em
`.streamlit/config.toml`, nas seções `[theme.light]` e `[theme.dark]`.

O CSS do design system não fixa cor de fundo nem de texto: superfícies, bordas
e textos secundários são derivados da cor de texto herdada com `color-mix`, de
modo que o mesmo CSS fica correto nos dois temas sem detecção server-side.
Acentos de marca e semânticos usam meio-tons legíveis sobre claro e escuro.

Ao criar componentes novos, siga a regra: **nunca escreva um hex de fundo ou de
texto**. Use `inherit`, `var(--erp-surface)`, `var(--erp-line)`,
`var(--erp-muted)`, `var(--erp-faint)` ou `tone_colors(tone)`.

## Convenções de front

- Sem emojis. Ícones vêm de `ui/icons.py`, fonte única com duas saídas:
  `icon("nome")` para HTML e `material("nome")` para os parâmetros `icon=`
  nativos do Streamlit.
- Nenhuma página monta HTML próprio: usa os componentes de `ui/components.py`.
- Gráficos passam por `ui/charts.py` para manter paleta e eixos consistentes.
- `setup_page()` é sempre a primeira chamada Streamlit de cada página; ela
  garante `set_page_config` antes de qualquer render e aplica o controle
  de acesso por nível.
- Toda página restrita some da navegação de quem não tem permissão.
