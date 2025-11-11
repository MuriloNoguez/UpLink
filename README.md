# Bot de Discord - Sistema de Tickets de TI

Um bot completo para gestão de chamados de suporte técnico em servidores Discord.

## 📋 Funcionalidades

- ✅ Embed permanente com botão "Abrir Ticket"
- ✅ Select menu para escolha do motivo (Acesso/Senha, Hardware, Software, Rede/Internet, Outros)
- ✅ Modal para descrição detalhada do problema
- ✅ Criação automática de canais privados de ticket
- ✅ Fechamento automático após 12 horas
- ✅ **Sistema de pausa de tickets (administradores)**
- ✅ **Bloqueio de novos tickets para usuários com tickets pausados**
- ✅ Sistema de permissões com cargo "Suporte TI"
- ✅ Persistência de dados em MySQL
- ✅ Logs estruturados e tratamento de exceções
- ✅ Views persistentes (funcionam após restart do bot)
- ✅ Comandos slash para administração

## 🛠️ Requisitos

- Python 3.8+
- MySQL 5.7+ ou MariaDB
- Servidor Discord com permissões administrativas

### Dependências Python
- `discord.py` >= 2.0
- `mysql-connector-python`
- `python-dotenv`

## 📦 Instalação

1. **Clone ou baixe os arquivos**
   ```bash
   # Os arquivos já estão no diretório atual
   ```

2. **Instale as dependências**
   ```bash
   # Ative o ambiente virtual se ainda não estiver ativo
   .venv\Scripts\activate
   
   # As dependências já foram instaladas, mas se precisar:
   pip install discord.py mysql-connector-python python-dotenv
   ```

3. **Configure o banco de dados MySQL**
   - Instale MySQL ou MariaDB
   - Crie um banco de dados chamado `bot_tickets`
   - Anote as credenciais de acesso

4. **Configure as variáveis de ambiente**
   - Copie `.env.example` para `.env`
   - Edite `.env` com suas configurações:

   ```env
   # Discord Bot Configuration
   DISCORD_TOKEN=seu_token_aqui
   
   # MySQL Database Configuration
   MYSQL_HOST=localhost
   MYSQL_PORT=3306
   MYSQL_DB=bot_tickets
   MYSQL_USER=root
   MYSQL_PASSWORD=sua_senha_mysql
   ```

## 🤖 Configuração do Bot Discord

1. **Crie uma aplicação no Discord Developer Portal**
   - Acesse: https://discord.com/developers/applications
   - Clique em "New Application"
   - Dê um nome ao seu bot

2. **Configure o bot**
   - Vá para a aba "Bot"
   - Clique em "Reset Token" e copie o token
   - Cole no arquivo `.env` na variável `DISCORD_TOKEN`

3. **Configure as permissões**
   - Vá para a aba "OAuth2" → "URL Generator"
   - Em "Scopes", marque: `bot` e `applications.commands`
   - Em "Bot Permissions", marque:
     - Manage Channels
     - Read Messages/View Channels
     - Send Messages
     - Manage Messages
     - Embed Links
     - Attach Files
     - Read Message History
     - Use Slash Commands

4. **Convide o bot para seu servidor**
   - Use a URL gerada para adicionar o bot ao seu servidor

## 🏃 Executando o Bot

```bash
# Certifique-se que o ambiente virtual está ativo
.venv\Scripts\activate

# Execute o bot
python main.py
```

## ⚙️ Configuração no Discord

1. **Crie o cargo "Suporte TI"** (opcional mas recomendado)
   - No Discord, vá em Configurações do Servidor → Cargos
   - Crie um cargo chamado exatamente "Suporte TI"
   - Atribua aos membros da equipe de suporte

2. **Configure o sistema de tickets**
   - Use o comando `/setup_tickets #canal`
   - Exemplo: `/setup_tickets #suporte`
   - Isso criará o embed com o botão para abrir tickets

## 📊 Estrutura do Banco de Dados

O bot cria automaticamente a seguinte tabela:

```sql
CREATE TABLE tickets (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    user_name VARCHAR(255) NOT NULL,
    channel_id BIGINT NOT NULL UNIQUE,
    reason VARCHAR(100) NOT NULL,
    description TEXT,
    status ENUM('open', 'closed') DEFAULT 'open',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    closed_at TIMESTAMP NULL
);
```

## 🎮 Comandos

### Comandos Slash (Administradores)

- `/setup_tickets <canal>` - Configura o sistema de tickets em um canal
- `/ticket_close` - Fecha manualmente um ticket (usado dentro do canal do ticket)
- `/ticket_pause` - **NOVO!** Pausa um ticket (apenas administradores)
- `/ticket_unpause` - **NOVO!** Despausa um ticket (apenas administradores)

### Comandos de Texto

- `!setup` - Configura no canal atual
- `!setup #canal` - Configura em canal específico
- `!sync` - Sincroniza comandos slash

### Interações

- **Botão "Abrir Ticket"** - Inicia o processo de criação de ticket
- **Select Menu** - Escolha do motivo do chamado
- **Modal** - Descrição detalhada do problema

## 🔧 Funcionamento

1. **Usuário clica em "Abrir Ticket"**
   - Sistema verifica se já tem ticket aberto **ou pausado**
   - Se ticket pausado, bloqueia criação de novos
   - Mostra select menu com motivos

2. **Usuário seleciona motivo**
   - Abre modal para descrição

3. **Usuário preenche descrição**
   - Sistema cria canal privado
   - Adiciona permissões para usuário e Suporte TI
   - Salva no banco de dados
   - Envia embed com informações do ticket

4. **Fechamento automático**
   - Após 12 horas, tickets são fechados automaticamente
   - Canal torna-se somente leitura
   - Nome é prefixado com 🔒
   - Status atualizado no banco

5. **Sistema de pausa (administradores)**
   - `/ticket_pause` - Pausa o ticket atual
   - Usuário não pode mais enviar mensagens
   - Usuário fica bloqueado para abrir novos tickets
   - Canal é renomeado com ⏸️
   - `/ticket_unpause` - Remove a pausa

## ⏸️ **Sistema de Pausa de Tickets**

### **Como funciona:**
- **Administradores** podem pausar tickets com `/ticket_pause`
- **Usuário pausado** não pode criar novos tickets
- **Canal pausado** fica somente-leitura para o usuário
- **Nome do canal** é prefixado com ⏸️
- **Tickets pausados** não são fechados automaticamente

### **Casos de uso:**
- 🚫 **Usuário problemático** - Pausar para investigação
- ⏳ **Aguardando informações** - Pausar até usuário fornecer dados
- 🔄 **Escalação** - Pausar enquanto transfere para outro setor
- 📋 **Análise** - Pausar para análise técnica detalhada

### **Permissões para pausar:**
- Cargo **"Suporte TI"**
- Permissão **"Gerenciar Canais"**

## 📝 Logs

O bot gera logs em dois locais:
- Console (saída padrão)
- Arquivo `bot.log`

Níveis de log incluem:
- INFO: Operações normais
- WARNING: Situações inesperadas
- ERROR: Erros que precisam atenção

## 🚨 Solução de Problemas

### Bot não inicia
- Verifique se o token está correto no `.env`
- Confirme se as dependências estão instaladas
- Verifique a conexão com MySQL

### Comandos não aparecem
- Aguarde até 1 hora para sincronização global
- Use Ctrl+R para recarregar o Discord
- Verifique se o bot tem permissão "Use Slash Commands"

### Erro de banco de dados
- Confirme se MySQL está rodando
- Verifique credenciais no `.env`
- Confirme se o banco `bot_tickets` existe

### Permissões insuficientes
- Bot precisa de "Manage Channels" para criar canais
- Bot precisa de "Manage Messages" para gerenciar tickets
- Verifique hierarquia de cargos no servidor

## 🔒 Segurança

- Nunca compartilhe seu token do bot
- Use senhas fortes para MySQL
- Mantenha o arquivo `.env` privado
- Considere usar um usuário MySQL específico com permissões limitadas

## 📞 Suporte

Se encontrar problemas:
1. Verifique os logs em `bot.log`
2. Confirme todas as configurações
3. Teste as permissões do bot no servidor
4. Verifique conectividade com MySQL

## 📄 Licença

Este projeto é fornecido como exemplo educacional. Adapte conforme necessário para seu uso.