#!/usr/bin/env python3
"""
Script de teste para verificar o funcionamento do sistema keep-alive melhorado.
"""

import asyncio
import logging
from keep_alive import simple_ping_test, KeepAliveSystem

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def test_keep_alive_functionality():
    """Testa a funcionalidade do keep-alive."""
    
    print("🧪 TESTE DO SISTEMA KEEP-ALIVE")
    print("=" * 50)
    
    # Teste 1: Conectividade básica
    print("\n1️⃣ Testando conectividade com novos endpoints...")
    await simple_ping_test()
    
    # Teste 2: Sistema keep-alive sem bot
    print("\n2️⃣ Testando sistema keep-alive...")
    system = KeepAliveSystem(None)  # Sem bot para teste
    
    # Simular um ping manual
    try:
        print("   Executando ping manual...")
        await system.keep_alive_task()
    except Exception as e:
        logger.error(f"Erro no ping manual: {e}")
    
    # Teste 3: Estatísticas
    print("\n3️⃣ Verificando estatísticas...")
    stats = system.get_stats()
    print(f"   - Pings bem-sucedidos: {stats['successful_pings']}")
    print(f"   - Pings falharam: {stats['failed_pings']}")
    print(f"   - Taxa de sucesso: {stats['success_rate']}%")
    print(f"   - Sistema ativo: {stats['is_running']}")
    
    print("\n✅ TESTE CONCLUÍDO!")
    print("=" * 50)


async def main():
    """Função principal do teste."""
    try:
        await test_keep_alive_functionality()
    except KeyboardInterrupt:
        print("\n⚠️ Teste interrompido pelo usuário")
    except Exception as e:
        logger.error(f"Erro no teste: {e}")


if __name__ == "__main__":
    # Executar teste
    print("🚀 Iniciando teste do keep-alive...")
    asyncio.run(main())