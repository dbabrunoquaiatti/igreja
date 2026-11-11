#!/bin/bash
set -e

# Corrigir permissões do volume montado em runtime pelo host
# (necessário porque bind mounts herdam ownership do host, não da imagem)
chown -R grex:grex /app/data 2>/dev/null || true

# Dropar de root para grex e executar o entrypoint principal
exec gosu grex /entrypoint.sh
