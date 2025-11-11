"""
Script de migração para a nova estrutura modular.
Execute este script para fazer backup do main.py antigo e usar a nova versão.
"""

import os
import shutil
from datetime import datetime

def migrate():
    """Realiza a migração para a nova estrutura."""
    print("🔄 Iniciando migração para estrutura modular...")
    
    # Fazer backup do main.py antigo
    if os.path.exists('main.py'):
        backup_name = f"main_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py"
        shutil.copy2('main.py', backup_name)
        print(f"✅ Backup criado: {backup_name}")
    
    # Substituir pelo novo main.py
    if os.path.exists('main_new.py'):
        if os.path.exists('main.py'):
            os.remove('main.py')
        shutil.move('main_new.py', 'main.py')
        print("✅ main.py atualizado com nova estrutura")
    
    print("\n📁 Nova estrutura criada:")
    print("├── main.py (refatorado)")
    print("├── config.py (configurações)")
    print("├── database.py (inalterado)")
    print("├── modules/")
    print("│   ├── ui/")
    print("│   │   ├── views.py (botões/interfaces)")
    print("│   │   └── modals.py (formulários)")
    print("│   └── commands/")
    print("│       └── ticket_commands.py (comandos slash)")
    print("└── utils/")
    print("    └── helpers.py (funções auxiliares)")
    
    print("\n🚀 Migração concluída! Execute 'python main.py' para testar.")
    print("\n💡 Benefícios da nova estrutura:")
    print("- Código mais organizado e fácil de manter")
    print("- Responsabilidades bem separadas")
    print("- Configurações centralizadas")
    print("- Funcionalidades modulares")
    print("- Fácil adição de novas features")

if __name__ == "__main__":
    migrate()