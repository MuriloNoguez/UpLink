# Render.com - Configuração de Build Otimizada
# https://render.com/docs/deploy-configuration

# Build Command Otimizado (novo)
# pip install --no-deps --cache-dir=/opt/render/project/.cache/pip -r requirements_optimized.txt && python start_bot.py

# Versão ainda mais otimizada (se quiser remover sync completamente):
# pip install --cache-dir=/opt/render/project/.cache/pip -r requirements_optimized.txt && python bot_optimized.py

# Start Command
# python start_bot.py

# Environment Variables necessárias:
# DISCORD_TOKEN=seu_token_aqui
# DATABASE_URL=sua_url_postgresql_aqui

# Configuração do runtime.txt (crie este arquivo se não existir)
# python-3.13.4

# .gitignore additions para cache
# .cache/
# __pycache__/
# *.pyc
# bot.log

# Configurações recomendadas no painel do Render:
# - Node Version: não aplicável (Python app)
# - Build Command: pip install --cache-dir=/opt/render/project/.cache/pip -r requirements_optimized.txt && python start_bot.py
# - Start Command: python start_bot.py  
# - Auto-Deploy: Sim (para deploys automáticos do GitHub)

# Estimativa de melhoria:
# Antes: ~2-3 minutos de build
# Depois: ~30-60 segundos de build

# Cache locations Render:
# - /opt/render/project/.cache/pip (pip cache)
# - Dependências Python são cached automaticamente pelo Render
# - Build artifacts são cached entre deploys