# 🎫 Bot de Tickets - Sistema Completo

Sistema modular de tickets de suporte para Discord com interface customizada.

## 📁 Estrutura do Projeto

```
├── config.py              # Configurações centralizadas
├── database.py             # Gerenciamento do banco MySQL
├── main.py                 # Bot principal (versão antiga)
├── sync_commands.py        # ⭐ Sincronizador de comandos
├── run_bot.py              # ⭐ Bot principal (nova versão)
├── start_bot.bat           # ⭐ Script para iniciar tudo
├── modules/
│   ├── commands/
│   │   └── ticket_commands.py  # Comandos slash
│   └── ui/
│       ├── views.py        # Botões e interfaces
│       └── modals.py       # Formulários e seleções
└── utils/
    └── helpers.py          # Funções utilitárias
```

## 🚀 Como Usar

### Método 1: Script Automático (Recomendado)
```bash
# Execute o arquivo batch (duplo clique ou pelo terminal)
start_bot.bat
```

### Método 2: Manual
```bash
# 1. Primeiro, sincronize os comandos
python sync_commands.py

# 2. Depois execute o bot principal
python run_bot.py
```

### Método 3: Bot Original (Alternativo)
```bash
# Executa tudo junto (pode ter delay nos comandos)
python main.py
```

## ⚡ Comandos Disponíveis

### Comandos Slash (digite `/` no Discord):
- `/ticket` - 🎫 Abrir um novo ticket de suporte
- `/setup_tickets` - Configura o sistema em um canal
- `/ticket_close` - Fecha ticket atual
- `/ticket_pause` - Pausa ticket (admin)
- `/ticket_unpause` - Despausa ticket (admin)
- `/ticket_history` - Ver histórico de tickets
- `/ticket_force_close` - Força fechamento (admin)

### Comandos de Texto (digite `!` no Discord):
- `!sync` - Força sincronização de comandos
- `!setup` - Configura tickets no canal atual

## 🎯 Características

### ✅ Sistema de Reutilização
- **1 canal por usuário**: Cada usuário reutiliza o mesmo canal
- **Histórico preservado**: Conversas anteriores ficam salvas
- **Auto-fechamento**: Tickets fecham automaticamente após 24h

### ✅ Interface Personalizada
- **Emojis customizados**: Usa emojis do próprio servidor
- **Seleção por plataforma**: Arbo, Lais, SendPulse, Outros
- **Interface limpa**: Design moderno e intuitivo

### ✅ Funcionalidades Avançadas
- **Pausar tickets**: Impede novas mensagens temporariamente
- **Histórico completo**: Ver todos os tickets de um usuário
- **Fechamento forçado**: Para tickets problemáticos
- **Logs detalhados**: Acompanhar todas as ações

## 🛠️ Configuração

### Arquivos Importantes:
- `config.py` - Token do bot, configurações gerais
- `database.py` - Conexão MySQL (usuário/senha/database)

### Emojis Customizados:
```python
TICKET_REASONS = {
    "Arbo": "🌱",
    "Lais": "<:Lais:1437865327001342052>",  # Emoji custom
    "SendPulse": "📧",
    "Outros": "❓"
}
```

## 🐛 Solução de Problemas

### Comandos não aparecem no Discord:
1. Execute `sync_commands.py` primeiro
2. Use `!sync` no Discord
3. Aguarde até 1 hora (cache do Discord)
4. Reinicie o aplicativo Discord

### Erro de conexão MySQL:
1. Verifique as credenciais em `database.py`
2. Certifique-se que o MySQL está rodando
3. Crie o database `tickets_bot` manualmente

### Bot não responde:
1. Verifique o token em `config.py`
2. Confirme as permissões do bot no servidor
3. Veja os logs em `bot.log`

## 📋 Permissões Necessárias

O bot precisa das seguintes permissões no Discord:
- `applications.commands` (comandos slash)
- `Send Messages`
- `Manage Channels`
- `Create Public Threads`
- `Embed Links`
- `Add Reactions`
- `Use External Emojis`

## 🎨 Customização

### Mudar opções do ticket:
Edite `TICKET_REASONS` em `config.py`

### Alterar cores dos embeds:
Modifique `EMBED_COLORS` em `config.py`

### Ajustar tempo de fechamento:
Altere `auto_close_hours` em `config.py`

---

**Desenvolvido por**: Sistema modular Python  
**Versão**: 2.0 (Refatorado)  
**Discord.py**: 2.6.4+  
**Python**: 3.8+