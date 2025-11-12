"""
Configurações e constantes do bot de tickets.
"""

import os
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()

# Configurações do Discord
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')

# Configurações do Banco de Dados PostgreSQL
DATABASE_CONFIG = {
    'url': os.getenv('DATABASE_URL', 'postgresql://user:password@localhost:5432/bot_tickets'),
    'host': os.getenv('POSTGRES_HOST', 'localhost'),
    'port': int(os.getenv('POSTGRES_PORT', '5432')),
    'database': os.getenv('POSTGRES_DB', 'bot_tickets'),
    'user': os.getenv('POSTGRES_USER', 'postgres'),
    'password': os.getenv('POSTGRES_PASSWORD', ''),
    'sslmode': os.getenv('POSTGRES_SSLMODE', 'prefer'),
    'connect_timeout': int(os.getenv('POSTGRES_TIMEOUT', '30'))
}

# Configurações do Bot
BOT_CONFIG = {
    'command_prefix': '/',
    'support_role_name': 'Suporte TI',
    'tickets_category_name': 'Tecnologia',
    'auto_close_hours': 12,
    'auto_close_check_minutes': 30,
    'channel_names_to_setup': ['suporte', 'tickets', 'ajuda', 'support', 'help']
}

# Embeds e Mensagens
EMBED_COLORS = {
    'success': 0x00ff00,    # Verde
    'error': 0xff0000,      # Vermelho  
    'warning': 0xffa500,    # Laranja
    'info': 0x0099ff,       # Azul
    'closed': 0xff0000,     # Vermelho
    'paused': 0xffa500,     # Laranja
    'reopened': 0xffa500    # Laranja
}

# Emoji para status
STATUS_EMOJI = {
    'open': '🟢',
    'closed': '🔴',
    'paused': '⏸️',
    'unknown': '❓'
}

# Opções de motivos para tickets
TICKET_REASONS = [
    {
        'label': 'Arbo',
        'description': 'Problemas relacionados ao Arbo',
        'emoji': '<:arbo:1437860050201874442>'
    },
    {
        'label': 'Lais',
        'description': 'Problemas relacionados ao Lais',
        'emoji': '<:Lais:1437865327001342052>'
    },
    {
        'label': 'SendPulse',
        'description': 'Problemas relacionados ao SendPulse',
        'emoji': '<:SP:1437860450523025459>'
    },
    {
        'label': 'Outros',
        'description': 'Outros tipos de problemas',
        'emoji': '❓'
    }
]

# Validação de configuração
def validate_config():
    """Valida se todas as configurações necessárias estão presentes."""
    if not DISCORD_TOKEN:
        raise ValueError("DISCORD_TOKEN não encontrado nas variáveis de ambiente!")
    return True