# Coffee BI — ERP para cafeterias

Aplicação moderna com **FastAPI + Firebase Cloud Firestore + frontend SPA**. Os arquivos Streamlit foram mantidos como código legado.

## Inicie toda a aplicação com BI init

**Instalação única** no diretório do projeto (Python 3.11+).

**Windows / PowerShell:**

    py -m venv .venv
    .\.venv\Scripts\Activate.ps1
    python -m pip install -e .
    BI init

**Linux / macOS:**

    python3 -m venv .venv
    source .venv/bin/activate
    python -m pip install -e .
    BI init

Depois da instalação única, basta ativar o mesmo ambiente virtual e executar **BI init**.

O comando faz o seguinte:
- Cria o .env local a partir de .env.example, se ainda não existir.
- Gera e grava um SESSION_SECRET aleatório e estável sem mostrá-lo no terminal.
- Solicita o ID do Firebase se estiver ausente (em terminal interativo).
- Verifica a conexão com o Cloud Firestore configurado.
- Permite cadastrar o primeiro administrador, se o banco estiver vazio.
- Inicializa FastAPI/Uvicorn e frontend no mesmo servidor.
- Abre http://127.0.0.1:8000 no navegador, quando possível.
- Encerra os processos iniciados ao pressionar Ctrl+C.

**O Cloud Firestore real está hospedado no Firebase e não é iniciado localmente.**
BI init exige credenciais configuradas por ADC (Google Cloud) ou GOOGLE_APPLICATION_CREDENTIALS,
apontando a um JSON de conta de serviço guardado fora do repositório.

### Sem Firebase real: modo emulador

Com Node.js, Java e Firebase CLI disponíveis, use:

    BI init --emulator

O comando inicia o emulador Firestore local e o aplicativo. Ele usa o projeto
isolado demo-coffee-bi e nunca deve acessar a base de produção.

### Opções de desenvolvimento

    BI init --reload                 # atualiza o backend ao salvar arquivos
    BI init --port 8081              # porta da aplicação
    BI init --no-browser             # não abre a janela do navegador
    BI init --emulator --reload      # emulador e recarregamento automático
    BI init --help                   # opções disponíveis

Após a instalação, cada terminal precisa do ambiente virtual ativado para
resolver o executável BI. Se o PowerShell restringir a ativação, use
.venv\Scripts\activate.bat pelo CMD.

Consulte [docs/SPA.md](docs/SPA.md) para configuração Firebase, migração SQL e produção.

---

## Código legado: Streamlit (somente para referência)

**Não utilize senhas de demonstração da versão legada em produção.**
A nova aplicação não gera contas com senhas padrão.

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
