#!/bin/bash

# Script de exemplo para demonstrar o uso do serviço Dev Peace

set -e

# Cores para output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}🕊️  Exemplo de uso do Dev Peace como serviço${NC}"
echo "=================================================="
echo

echo -e "${YELLOW}1. Instalando o serviço...${NC}"
./scripts/install-service.sh

echo
echo -e "${YELLOW}2. Configurando Jira (exemplo)...${NC}"
echo "dev-peace config --jira-url 'https://empresa.atlassian.net' \\"
echo "                  --jira-user 'seu@email.com' \\"
echo "                  --jira-token 'seu-token-aqui'"

echo
echo -e "${YELLOW}3. Adicionando repositórios...${NC}"
echo "dev-peace add /caminho/para/repositorio1"
echo "dev-peace add /caminho/para/repositorio2"

echo
echo -e "${YELLOW}4. Configurando automação de status...${NC}"
echo "# Ver regras atuais"
echo "dev-peace automation show"
echo
echo "# Habilitar automação geral"
echo "dev-peace automation enable"
echo
echo "# Habilitar regra específica"
echo "dev-peace automation enable on_work_start"

echo
echo -e "${YELLOW}5. Iniciando o serviço...${NC}"
echo "systemctl --user start dev-peace"

echo
echo -e "${YELLOW}6. Verificando status...${NC}"
echo "systemctl --user status dev-peace"

echo
echo -e "${YELLOW}7. Visualizando logs...${NC}"
echo "journalctl --user -u dev-peace -f"

echo
echo -e "${YELLOW}8. Comandos úteis durante o uso...${NC}"
echo "# Ver status do Dev Peace"
echo "dev-peace status"
echo
echo "# Alterar status de issue manualmente"
echo "dev-peace status-issue PROJ-123 'In Progress' --comment 'Iniciando trabalho'"
echo
echo "# Ver registros órfãos"
echo "dev-peace orphans"
echo
echo "# Interface interativa"
echo "dev-peace interactive"

echo
echo -e "${YELLOW}9. Parando o serviço...${NC}"
echo "systemctl --user stop dev-peace"

echo
echo -e "${GREEN}✅ Exemplo completo!${NC}"
echo
echo -e "${BLUE}📋 Fluxo típico de uso:${NC}"
echo "1. Configure o Jira uma vez"
echo "2. Adicione seus repositórios"
echo "3. Configure automação de status"
echo "4. Inicie o serviço"
echo "5. Trabalhe normalmente - Dev Peace cuida do resto!"
echo
echo -e "${BLUE}🔍 Para debug:${NC}"
echo "journalctl --user -u dev-peace --since '1 hour ago'"
