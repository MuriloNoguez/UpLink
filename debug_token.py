#!/usr/bin/env python3
"""
🔍 Debug do Token Discord
Verifica se o token está sendo lido corretamente do .env
"""

import os
from dotenv import load_dotenv

def debug_token():
    """Debug da leitura do token."""
    print("🔍 DEBUG DO TOKEN DISCORD")
    print("-" * 40)
    
    # Carregar .env
    load_dotenv()
    
    # Verificar se arquivo .env existe
    env_file = ".env"
    if os.path.exists(env_file):
        print(f"✅ Arquivo {env_file} encontrado")
        with open(env_file, 'r') as f:
            content = f.read()
            print(f"📄 Tamanho do arquivo: {len(content)} caracteres")
            if "DISCORD_TOKEN" in content:
                print("✅ DISCORD_TOKEN encontrado no arquivo")
            else:
                print("❌ DISCORD_TOKEN NÃO encontrado no arquivo")
    else:
        print(f"❌ Arquivo {env_file} NÃO encontrado")
    
    # Verificar token nas variáveis de ambiente
    token = os.getenv('DISCORD_TOKEN')
    
    if token:
        print(f"✅ Token carregado das variáveis de ambiente")
        print(f"📏 Comprimento do token: {len(token)} caracteres")
        print(f"🔤 Primeiros 10 caracteres: {token[:10]}...")
        print(f"🔤 Últimos 10 caracteres: ...{token[-10:]}")
        
        # Verificar formato básico do token Discord
        if token.count('.') == 2:
            print("✅ Formato do token parece correto (tem 2 pontos)")
            parts = token.split('.')
            print(f"📊 Partes do token: {len(parts[0])}.{len(parts[1])}.{len(parts[2])}")
        else:
            print("❌ Formato do token pode estar incorreto")
            
        # Verificar espaços em branco
        if token != token.strip():
            print("⚠️ Token tem espaços em branco no início/fim")
            print(f"Token limpo: {repr(token.strip())}")
        else:
            print("✅ Token não tem espaços extras")
            
        # Verificar caracteres estranhos
        if token.isascii():
            print("✅ Token contém apenas caracteres ASCII")
        else:
            print("⚠️ Token contém caracteres não-ASCII")
            
    else:
        print("❌ Token NÃO encontrado nas variáveis de ambiente")
        print("🔍 Variáveis disponíveis:")
        for key in os.environ.keys():
            if 'DISCORD' in key.upper() or 'TOKEN' in key.upper():
                print(f"  - {key}")
    
    print()
    print("DATABASE_URL:")
    db_url = os.getenv('DATABASE_URL')
    if db_url:
        print(f"✅ DATABASE_URL encontrada ({len(db_url)} chars)")
        # Não mostrar URL completa por segurança
        if 'postgresql://' in db_url:
            print("✅ Formato PostgreSQL correto")
        else:
            print("⚠️ Formato pode estar incorreto")
    else:
        print("❌ DATABASE_URL não encontrada")


if __name__ == "__main__":
    debug_token()