#!/bin/bash

# Script de instalação do serviço Dev Peace para macOS
# Cria um Launch Agent para executar o Dev Peace como daemon

set -e

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Função para log colorido
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Verifica se é macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
   log_error "Este script é exclusivo para macOS!"
   exit 1
fi

# Verifica se está rodando como root
if [[ $EUID -eq 0 ]]; then
   log_error "Este script não deve ser executado como root!"
   log_info "Execute como usuário normal: ./scripts/install-service-macos.sh"
   exit 1
fi

# Detecta informações do sistema
USER=$(whoami)
HOME_DIR=$(eval echo ~$USER)
CURRENT_DIR=$(pwd)

# Tenta encontrar o executável dev-peace no PATH primeiro (caso instalado via uv tool)
if command -v dev-peace >/dev/null 2>&1; then
    DEV_PEACE_EXEC=$(command -v dev-peace)
    log_info "Executável dev-peace detectado no sistema: $DEV_PEACE_EXEC"
else
    # Se não encontrar no PATH, tenta nos ambientes virtuais locais
    if [ -d "$CURRENT_DIR/.venv" ]; then
        VENV_PATH="$CURRENT_DIR/.venv"
        DEV_PEACE_EXEC="$VENV_PATH/bin/dev-peace"
        log_info "Ambiente virtual detectado em: .venv"
    elif [ -d "$CURRENT_DIR/venv" ]; then
        VENV_PATH="$CURRENT_DIR/venv"
        DEV_PEACE_EXEC="$VENV_PATH/bin/dev-peace"
        log_info "Ambiente virtual detectado em: venv"
    else
        log_error "Nenhum ambiente virtual encontrado e 'dev-peace' não está no PATH."
        log_info "Execute primeiro: uv tool install --editable .  OU  uv venv && pip install -e ."
        exit 1
    fi
fi

# Verifica se o executável realmente existe e é válido
if [ ! -f "$DEV_PEACE_EXEC" ]; then
    log_error "Dev Peace não encontrado em $DEV_PEACE_EXEC"
    log_info "Execute primeiro: uv tool install --editable ."
    exit 1
fi

log_info "🕊️  Instalando Dev Peace como Launch Agent no macOS..."
log_info "Usuário: $USER"
log_info "Diretório: $CURRENT_DIR"

# Cria diretório para logs
LOG_DIR="$HOME_DIR/Library/Logs/dev-peace"
mkdir -p "$LOG_DIR"
log_info "Diretório de logs criado: $LOG_DIR"

# Cria diretórios de configuração se não existirem
mkdir -p "$HOME_DIR/.config/dev-peace"

# Nome do serviço
LABEL="com.devpeace.daemon"
PLIST_FILE="$HOME_DIR/Library/LaunchAgents/$LABEL.plist"

log_info "Criando arquivo plist: $PLIST_FILE"

cat > "$PLIST_FILE" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>$LABEL</string>
    <key>ProgramArguments</key>
    <array>
        <string>$DEV_PEACE_EXEC</string>
        <string>daemon</string>
        <string>--log-level</string>
        <string>info</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>WorkingDirectory</key>
    <string>$CURRENT_DIR</string>
    <key>StandardOutPath</key>
    <string>$LOG_DIR/stdout.log</string>
    <key>StandardErrorPath</key>
    <string>$LOG_DIR/stderr.log</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>$(dirname $DEV_PEACE_EXEC):$PATH</string>
        <key>PYTHONPATH</key>
        <string>$CURRENT_DIR/src</string>
    </dict>
</dict>
</plist>
EOF

log_success "Arquivo plist criado!"

# Carrega o serviço
log_info "Carregando o serviço com launchctl..."
launchctl unload "$PLIST_FILE" 2>/dev/null || true
launchctl load "$PLIST_FILE"

log_success " Serviço Dev Peace instalado e carregado com sucesso!"
echo
log_info " Comandos úteis no macOS:"
echo "  • Iniciar serviço:    launchctl load $PLIST_FILE"
echo "  • Parar serviço:      launchctl unload $PLIST_FILE"
echo "  • Ver logs:           tail -f $LOG_DIR/stdout.log"
echo "  • Ver erros:          tail -f $LOG_DIR/stderr.log"
echo
log_warning "  Lembre-se de configurar o Jira antes de iniciar:"
echo "  dev-peace config --jira-url <url> --jira-user <user> --jira-token <token>"
echo
log_info " O serviço já foi iniciado e rodará automaticamente ao fazer login."
