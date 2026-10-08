# Auditoria e correções — Coffee BI

Base analisada: `c1863b791205d844c38b7da37614bad7c5c93c5a`, branch `main`.

## Problemas principais encontrados e tratados

| Prioridade | Problema | Correção |
|---|---|---|
| P0 | O repositório não tinha API HTTP; era uma aplicação Streamlit com acesso direto ao banco. | Aplicação FastAPI e frontend servido pela mesma origem, com rotas reais e autenticação. |
| P0 | Venda ignorava falha de baixa por estoque insuficiente. | Baixa condicional no banco, erro `409`, rollback de todos os itens. |
| P0 | Venda/compra faziam commits dentro de cada atualização de estoque. | Um commit por movimento; nenhum registro parcial em caso de erro. |
| P0 | Totais/subtotais do carrinho eram aceitos sem recálculo. | Quantidade × preço calculados no servidor com `Decimal`. |
| P0 | Vendas simultâneas podiam ultrapassar o estoque; cancelamento concorrente podia repor duas vezes. | Atualizações condicionais e cancelamento que só ajusta estoque depois de obter exclusão efetiva do movimento. |
| P1 | Formulário aberto podia sobrescrever estoque alterado depois por venda/compra. | `version` e `If-Match` no PUT de produtos; edição reaberta consulta o produto novamente. |
| P1 | Ausência de contrato/validação HTTP e erros inconsistentes. | Schemas tipados, limites de valores, campos extras rejeitados, `401/403/404/409/422`, rollback e mensagens sem detalhes internos do banco. |
| P1 | Administradores eram criados com senha fixa em inicialização automática. | Bootstrap explícito via ambiente; nenhum novo usuário com senha fixa. Contas antigas são preservadas. |
| P1 | Autorização ficava apenas no estado do Streamlit. | API verifica usuário, funcionário ativo e papel em cada operação; Streamlit atualiza autorização a cada rerun. |
| P1 | Logout da interface antiga mantinha carrinhos no estado da sessão. | Limpeza completa do session state; API usa sessão revogável armazenada como hash. |
| P1 | Conta e funcionário tinham commits independentes. | Criação de usuário com `commit=False` no cadastro vinculado, confirmando tudo ao final. |
| P1 | Checkbox de criar acesso ficava dentro do formulário e não reagia antes do envio. | Controle fora do formulário; campos opcionais aparecem antes da submissão. |
| P1 | Redefinição de senha não revogava sessões HTTP. | Serviço de redefinição revoga sessões existentes; tela antiga usa esse serviço. |
| P1 | `func.literal` gerava função SQL inexistente no fluxo de caixa. | Uso de `sqlalchemy.literal`, com teste do saldo. |
| P1 | Lucro histórico era alterado pelo custo atual do produto. | Snapshot de custo nas novas vendas; fallback estimado para registros antigos, explicado no README. |
| P1 | Gráfico de pagamentos usava argumento não suportado por `px.funnel`. | Paleta discreta compatível com a função. |
| P1 | Insights do BI usavam `df_lucro` sem inicializá-lo quando Lucratividade não estava selecionada. | Consulta disponível independentemente da seleção de gráficos. |
| P1 | Tabela de lucratividade dependia de Matplotlib, ausente dos requisitos. | Dependência incluída e verificação com todos os gráficos habilitados. |
| P2 | Métrica de vendas do mês contava dias agrupados, em vez de vendas. | Soma de `Quantidade`; janela de sete dias corrigida no dashboard principal antigo. |
| P2 | Relatório de lucro podia falhar em receita zero; produtos com mesmo nome eram agrupados juntos. | Tratamento de divisão por zero e agrupamento por ID/nome. |
| P2 | Edição de vários estoques confirmava cada linha separadamente. | Operação de lote com um commit e rollback integral. |
| P2 | SQLite não habilitava integridade referencial. | `PRAGMA foreign_keys=ON`, incluindo exclusão de itens ao cancelar movimentos. |
| P2 | Interface sem tabela organizada, paginação e feedback de operação. | Layout responsivo, tabela ordenável, busca, status, páginas/tamanho de página, CSV, modais e erros visíveis. |
| P2 | Gráficos pouco exploráveis e sem filtros claros. | Filtro de período, valores por hover/foco e adaptação ao tamanho da tela. |
| P2 | Datas dependiam do fuso do servidor. | Fuso do negócio configurável, com padrão São Paulo e suporte a Windows via `tzdata`. |
| P2 | Bytecode gerado era versionado. | Remoção dos `.pyc`, `.gitignore` para ambiente, banco, caches e arquivos de configuração local. |
| P2 | Comando de reset removia sempre `cafeteria.db`, mesmo com outro banco configurado. | Reset considera o caminho SQLite configurado e recusa reset automático de PostgreSQL. |

## Verificação local

- **18 testes de backend:** CRUD/persistência, validação, permissões, logout, origem, totais, rollback, cancelamentos, compra/custo, relatórios, Unicode, paginação, concorrência, versão desatualizada, migração e redefinição de senha.
- **Chromium real:** criação/edição/desativação/reativação de produto; persistência após recarregar; venda/compra e cancelamentos; erro por estoque insuficiente; equipe/financeiro; busca, ordenação, paginação, gráfico, layout móvel e logout. Sem exceções de JavaScript.
- **Streamlit AppTest:** login, seis páginas, BI com todas as opções, criação vinculada de funcionário/usuário e bloqueio após desativação.
- Verificação de sintaxe do JavaScript, compilação Python, lint e diff.

O registro das respostas HTTP observadas no navegador está em [VALIDACAO_HTTP.json](VALIDACAO_HTTP.json). Contém somente método, caminho e status; não contém cookies ou senhas. Capturas da interface estão em [screenshots](screenshots/).

## Limites e operação

- O banco real da instalação do usuário não foi disponibilizado. A validação usa dados isolados em SQLite temporário.
- PostgreSQL não foi executado localmente: o ambiente não permitiu iniciar o processo sob um usuário de sistema apropriado. A workflow inclui PostgreSQL e Python 3.12/3.13; seu resultado deve ser conferido no GitHub.
- Migração é aditiva e idempotente. Faça cópia do banco antes de atualizar a instalação real e aplique a migração em uma única instância antes de iniciar múltiplos workers.
- Custos históricos ausentes em vendas antigas não podem ser reconstruídos com exatidão; o fallback usa o custo atual.
- Cancelamento de compra reverte quantidade, mantendo o custo médio vigente. Reavaliação contábil de devoluções não está implementada.
- Vendas/compras não têm edição arbitrária por PUT: cancelar e registrar novamente evita trocar totais sem ajustar estoque.
- Gerenciamento avançado de usuários permanece na interface Streamlit. O novo frontend permite gerenciar funcionários, e o bootstrap configura contas iniciais.
- O Streamlit ainda emite avisos de depreciação de `use_container_width` nas versões recentes; isso não impediu os fluxos verificados. O frontend web é a interface recomendada.
