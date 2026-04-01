# BusZapp

## Visão Geral
**BusZapp** é uma aplicação para rastreamento e gerenciamento de rotas de ônibus. O backend é desenvolvido em **Python** utilizando o framework **Flask** em conjunto com **Flask-SocketIO** para fornecer comunicação bidirecional em tempo real. O banco de dados primário é **PostgreSQL**, acessado via **SQLAlchemy**. O frontend da aplicação consiste em arquivos estáticos (HTML/CSS/JS) servidos diretamente pelo backend na raiz do projeto.

## Estrutura do Projeto

Abaixo estão os principais arquivos e pastas que compõem a arquitetura do projeto:

- `src/` — Diretório principal com o código-fonte (Backend).
  - `main.py` — Ponto de entrada da aplicação, onde ocorre a criação e configuração da instância (Factory) do Flask, extensões, registro de blueprints e inicialização do `socketio`.
  - `config.py` — Centraliza as configurações relativas a diferentes ambientes (desenvolvimento, produção, teste).
  - `models/` — Arquivos responsáveis pela definição do banco de dados (tabelas mapeadas via SQLAlchemy).
  - `routes/` — Contém os Blueprints do Flask, ou seja, onde ficam os endpoints e regras de navegação da API (`auth_bp`, `card_bp`, `bus_bp`, `admin_bp`, `tracking_bp`).
  - `services/` — Lógica de negócios da aplicação e serviços auxiliares (separando a lógica das rotas/controllers).
  - `utils/` — Funções utilitárias reaproveitadas em diferentes partes do código.
- `static/` — Armazena os arquivos do frontend. É a interface com a qual o usuário interage.
- `.env.example` — Arquivo de exemplo que lista as variáveis de ambiente necessárias para rodar o app.
- `requirements.txt` — Lista oficial das dependências Python utilizadas neste projeto (ex.: `Flask`, `Flask-SocketIO`, `psycopg2-binary`).
- `simulate_bus.py` — Script utilitário em Python que simula e emite as posições/coordenadas de movimentação de um ônibus via sockets (muito útil em tempo de desenvolvimento).
- `migrate_sqlite_to_postgres.py` — Script responsável por migrar dados legados em SQLite para o PostgreSQL.

## Como Rodar a Aplicação Localmente

### 1. Pré-Requisitos
- **Python 3.8+** instalado no seu computador.
- **PostgreSQL** instalado e ativo, rodando na porta padrão (ou sua porta configurada).
- **Git** (opcional, caso você precise clonar o repositório).

### 2. Configurando o Ambiente e Instalando Dependências

Abra o terminal na raiz do projeto (`BusZapp`) e execute os passos abaixo.

#### Windows:
```cmd
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

#### Linux / macOS:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Configurando as Variáveis de Ambiente

Para que o projeto se conecte ao banco de dados e funcione corretamente, você precisará criar o `.env` baseado no `.env.example`:

1. Copie (ou renomeie) o arquivo `.env.example` para `.env`:
   ```bash
   # Linux/macOS
   cp .env.example .env
   
   # Windows
   copy .env.example .env
   ```
2. Abra o recém-criado arquivo `.env` em um editor de texto de sua preferência.
3. Altere as configurações, dando especial atenção à **`DATABASE_URL`**. Seus testes locais com o postgres precisarão de uma string compatível com a sua base de dados local:
   *Exemplo*: `DATABASE_URL=postgresql://postgres:suasenha@localhost:5432/buszapp`
4. Lembre-se também de criar a base `buszapp` (ou o nome que escolher) dentro do Postgres.

### 4. Inicializando o Banco de Dados

Você não precisa rodar explicitamente a criação de tabelas (`flask db upgrade`), pois o projeto está configurado para criá-las automaticamente via `db.create_all()` no momento em que a aplicação inicia pela primeira vez (dentro de `src/main.py`). Se possuir um banco SQLite que deseja migrar, utilize o script de migração:
```bash
python migrate_sqlite_to_postgres.py
```

### 5. Iniciar a Aplicação Backend

Com o ambiente ativado e as dependências e banco instalados, você pode rodar a aplicação central:

```bash
python -m src.main
# ou alternativamente, caso esteja configurado no sys.path:
python src/main.py
```

O servidor do **Flask-SocketIO** se encarregará de executar a aplicação. Se configurado em ambiente de desenvolvimento `FLASK_ENV=development` no arquivo `.env`, o servidor rodará em modo `debug`.
* O sistema estará acessível por padrão na URL: `http://localhost:8080/`

### 6. Executar Simulação / Tracking (Opcional)

Se você quer ver as posições do ônibus em tempo real rodando no mapa do frontend, execute em uma **outra aba do terminal** (lembre-se de ativar o `venv` novamente nela):

```bash
python simulate_bus.py
```

Isso enviará dados de rota e posição para o websocket local em execução (porta `8080`).

## Documentação da API de Pagamentos (Recarga)

A aplicação conta com um fluxo de pagamento para recarga de saldo integrado, permitindo adicionar créditos à conta do usuário usando diferentes métodos de pagamento.

### Endpoint de Recarga

**`POST /api/recharge`**

**Autenticação Obrigatória:** Sim (requer usuário logado)

**Corpo da Requisição (JSON):**
```json
{
  "amount": 50.00,
  "payment_method": "cartao"
}
```

- **`amount`**: (Obrigatório, número) Valor a ser recarregado. Deve ser numérico e maior que zero.
- **`payment_method`**: (Opcional, string) Método de pagamento escolhido. O valor padrão é `"cartao"`. Opções válidas: `"cartao"` ou `"pix"`.

**Respostas:**

- **`200 OK`**: Recarga e atualização do saldo realizadas com sucesso.
  - Para **PIX**, o `payment_info` da resposta incluirá o campo extra `qr_code` no formato base64.
  - O sistema registra o histórico (`Transaction`) e cria uma notificação para o usuário.
  ```json
  {
    "message": "Recarga realizada com sucesso",
    "new_balance": 50.00,
    "transaction": {
      "id": 1,
      "amount": 50.0,
      "transaction_type": "recharge",
      "description": "Recarga via Cartão de Crédito - R$ 50.00",
      "created_at": "..."
    },
    "payment_info": {
      "method": "Cartão de Crédito",
      "status": "Aprovado",
      "transaction_id": "CARD_1_1680000000"
    }
  }
  ```
- **`400 Bad Request`**: Erro de validação (ex: valor ausente/inválido, negativo, ou se o `payment_method` for inválido).
- **`404 Not Found`**: Usuário não encontrado na base de dados.

### Impactos no Sistema e Extensões
- **Saldo**: O saldo (`card_balance`) recebe a somatória da quantia aprovada.
- **Histórico**: A operação entra no extrato retornado por `GET /api/transactions`.
- **Validação de Catraca**: Ao atingir o crédito, o passageiro pode utilizar a rota com `POST /api/use-transport`, onde o valor da tarifa correspondente é deduzido deste saldo. Caso o saldo atinja o limiar baixo (R$ 5,00), um aviso extra de "Saldo Baixo" será notificado.
