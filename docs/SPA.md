# Coffee BI 2 — SPA + Cloud Firestore

## Comando de inicialização unificado

A nova aplicação também oferece o CLI instalável BI (maiúsculas). Para instalar
uma vez na sua máquina, a partir da raiz do repositório:

    python -m pip install -e .

Depois, com o mesmo ambiente Python ativo, inicie o sistema inteiro usando:

    BI init

Esse comando cria o .env se necessário, gera o SESSION_SECRET (quando estiver
vazio e APP_ENV=development), pede o ID do projeto Firebase, verifica o
Firestore e oferece cadastro da conta admin quando o banco estiver vazio.
Inicializa o FastAPI com todo o frontend na mesma porta, sem iniciar Streamlit.

Opções:

    BI init --emulator          # emulador Firestore isolado + site + API
    BI init --reload            # reinício automático ao editar código
    BI init --no-browser        # sem abrir navegador
    BI init --port 8081         # altera porta HTTP

Para o Cloud Firestore na nuvem, configure credenciais de servidor via ADC
ou variável GOOGLE_APPLICATION_CREDENTIALS (JSON privado). O comando não cria
automaticamente projeto Firebase, não publica regras e não descobre chaves privadas.
Para o modo emulador, instale Node.js, Java e Firebase CLI. O emulador é
bloqueado no modo APP_ENV=production. O comando não inventa senhas.

---

A nova aplicação foi criada a partir da branch codespace-vigilant-potato-69vpjr5w7v6c54vq. A main não é usada nem alterada. Os arquivos do Streamlit foram preservados para comparação; a nova API usa Firestore para TODOS os dados operacionais.

## 1. Preparar Firebase

1. Crie ou selecione um projeto em https://console.firebase.google.com/.
2. Habilite Cloud Firestore (modo de produção) em uma região adequada.
3. Configure uma conta de serviço no servidor com acesso mínimo ao Firestore.
4. Para Google Cloud Run, prefira credenciais padrão (ADC) sem JSON. Para servidor externo, configure GOOGLE_APPLICATION_CREDENTIALS com o caminho privado do JSON.
5. Publique as regras em firestore.rules, que negam acesso direto pelo navegador. O Admin SDK ignora as regras de segurança do Firestore e usa IAM.

Esta implementação utiliza Firestore como banco, NÃO Firebase Authentication: a autenticação continua na API (hash bcrypt, cookie HttpOnly, CSRF e autorização por cargo).

## 2. Variáveis no arquivo .env

Copie .env.example e defina:
- FIREBASE_PROJECT_ID: ID do projeto Firebase
- SESSION_SECRET: valor aleatório permanente (mais de 32 caracteres)
- GOOGLE_APPLICATION_CREDENTIALS: caminho do JSON privado para uso fora do Google Cloud, se necessário
- APP_ENV=production: habilita cookie Secure, exige SESSION_SECRET
- PUBLIC_ORIGIN=https://seu-dominio.com: obrigatório quando servidor recebe requests atrás de proxy reverso
- BUSINESS_TIMEZONE=America/Sao_Paulo: fuso operacional

Nunca publique o JSON da conta de serviço nem .env em PR/ZIP público.

## 3. Instalação

Python 3.11+:

    python -m venv .venv
    # Linux/macOS: source .venv/bin/activate
    # Windows PowerShell: .venv\Scripts\Activate.ps1
    python -m pip install -r requirements-api.txt
    # Copie .env.example para .env e configure o Firebase.
    python -m api.bootstrap_admin --username admin
    uvicorn api.main:app --reload --port 8000

Acesse http://127.0.0.1:8000 e veja a documentação da API em /api/docs.
A criação da primeira conta exige senha com pelo menos 10 caracteres no terminal. Não existe senha padrão.

### Ambiente local de testes sem credenciais

Inicie o emulador em um terminal:

    npx --yes firebase-tools emulators:start --only firestore --project demo-coffee-bi

Em outro terminal, defina FIREBASE_PROJECT_ID=demo-coffee-bi, FIRESTORE_EMULATOR_HOST=127.0.0.1:8080 e inicie a API. Em PowerShell, use $env:FIREBASE_PROJECT_ID="demo-coffee-bi" e $env:FIRESTORE_EMULATOR_HOST="127.0.0.1:8080".

O emulador é descartável. Nunca use o projeto demo no ambiente de produção.

## 4. Migração dos dados SQL/SQLite existentes

api/migrate_sql_to_firestore.py lê todos os produtos, vendas e seus itens, compras e seus itens, transações, funcionários e usuários, preservando senhas como hashes bcrypt e mantendo IDs originais.

1. Interrompa as escritas da aplicação antiga e faça um backup verificável do banco SQL original.
2. Configure MIGRATION_SOURCE_DATABASE_URL com o endereço SQLAlchemy da origem (por exemplo: sqlite:///./data/cafeteria.db).
3. Configure FIREBASE_PROJECT_ID e credenciais para o destino.
4. Faça inventário em modo seguro (somente leitura):

    python -m api.migrate_sql_to_firestore

5. Verifique contagens e execute, somente após confirmar o projeto vazio:

    python -m api.migrate_sql_to_firestore --apply --confirm-project-id ID_EXATO_DO_PROJETO

6. Verifique os totais financeiros, contagem e estoque, usuários e permissões antes de mudar a aplicação.

O script não remove nem altera registros do banco SQL. Para segurança, recusa destinos não vazios. Importações grandes são feitas em lotes: se um lote falhar, a migração total não é atômica; faça reconciliação manual antes de repetir.

## 5. Estrutura Firestore

Coleções: users, usernames, employees, products, sales, purchases, transactions, _counters.

IDs numéricos do frontend anterior continuam preservados como IDs de documento. Valores monetários são armazenados como centavos inteiros e convertidos em reais pela API. Vendas, baixa de estoque e incremento de contador são uma transação Firestore; o mesmo vale para compras e cálculo do custo médio ponderado. O Firestore usa concorrência/retry quando um documento da transação sofre alterações. Ver https://firebase.google.com/docs/firestore/manage-data/transactions.

A API continua sendo a única forma de acesso aos dados para o site. O Admin SDK é privilegiado e a identidade do servidor deve ser protegida por IAM.

## 6. Testar

    python -m pip install -r requirements-dev.txt
    node --check web/app.js
    npx --yes firebase-tools emulators:exec --only firestore --project demo-coffee-bi -- "python -m pytest -q tests/test_api_spa.py"

O GitHub Actions também executa os testes com o emulador. Nunca execute a limpeza dos fixtures contra um projeto Firebase real.

Publique as regras com as permissões corretas:

    firebase deploy --only firestore:rules,firestore:indexes --project ID_EXATO_DO_PROJETO

Antes de operar com clientes reais, ainda são necessários HTTPS, backups periódicos, revisões de IAM, limites de requisição distribuídos, monitoramento e estratégias de paginação/sumarização do dashboard para volume elevado. Esta implementação não inclui emissão fiscal, NF-e, TEF ou integração com adquirentes.
