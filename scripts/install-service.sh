#!/bin/bash

# Script de instalação do serviço Dev Peace
# Cria um serviço systemd para executar o Dev Peace como daemon

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

# Verifica se está rodando como root
if [[ $EUID -eq 0 ]]; then
   log_error "Este script não deve ser executado como root!"
   log_info "Execute como usuário normal: ./scripts/install-service.sh"
   exit 1
fi

# Detecta informações do sistema
USER=$(whoami)
HOME_DIR=$(eval echo ~$USER)
CURRENT_DIR=$(pwd)

# Detecta o ambiente virtual (tenta .venv primeiro, depois venv)
if [ -d "$CURRENT_DIR/.venv" ]; then
    VENV_PATH="$CURRENT_DIR/.venv"
    log_info "Ambiente virtual detectado em: .venv"
elif [ -d "$CURRENT_DIR/venv" ]; then
    VENV_PATH="$CURRENT_DIR/venv"
    log_info "Ambiente virtual detectado em: venv"
else
    log_error "Nenhum ambiente virtual encontrado em $CURRENT_DIR"
    log_info "Execute primeiro: uv venv (ou python -m venv venv) && pip install -e ."
    exit 1
fi

DEV_PEACE_EXEC="$VENV_PATH/bin/dev-peace"

log_info "🕊️  Instalando Dev Peace como serviço systemd..."
log_info "Usuário: $USER"
log_info "Diretório: $CURRENT_DIR"

# Verifica se o dev-peace está instalado
if [ ! -f "$DEV_PEACE_EXEC" ]; then
    log_error "Dev Peace não encontrado em $DEV_PEACE_EXEC"
    log_info "Execute primeiro: pip install -e ."
    exit 1
fi

# Cria diretório para logs
LOG_DIR="$HOME_DIR/.local/share/dev-peace/logs"
mkdir -p "$LOG_DIR"
log_info "Diretório de logs criado: $LOG_DIR"

# Cria arquivo de configuração do serviço
SERVICE_FILE="$HOME_DIR/.config/systemd/user/dev-peace.service"
mkdir -p "$(dirname "$SERVICE_FILE")"

log_info "Criando arquivo de serviço: $SERVICE_FILE"

cat > "$SERVICE_FILE" << EOF
[Unit]
Description=Dev Peace - Observador inteligente de desenvolvimento
Documentation=file://$CURRENT_DIR/README.md
After=graphical-session.target
Wants=graphical-session.target

[Service]
Type=simple
ExecStart=$DEV_PEACE_EXEC daemon --log-level=info
ExecReload=/bin/kill -HUP \$MAINPID
Restart=always
RestartSec=10
WorkingDirectory=$CURRENT_DIR
Environment=PATH=$VENV_PATH/bin:/usr/local/bin:/usr/bin:/bin
Environment=PYTHONPATH=$CURRENT_DIR/src

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=dev-peace

# Security
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=false
ReadWritePaths=$HOME_DIR/.config/dev-peace $HOME_DIR/.local/share/dev-peace

[Install]
WantedBy=default.target
EOF

log_success "Arquivo de serviço criado!"

# Recarrega systemd
log_info "Recarregando systemd..."
systemctl --user daemon-reload

# Habilita o serviço
log_info "Habilitando serviço dev-peace..."
systemctl --user enable dev-peace.service

log_success "✅ Serviço Dev Peace instalado com sucesso!"
echo
log_info "📋 Comandos úteis:"
echo "  • Iniciar serviço:    systemctl --user start dev-peace"
echo "  • Parar serviço:      systemctl --user stop dev-peace"
echo "  • Status do serviço:  systemctl --user status dev-peace"
echo "  • Ver logs:           journalctl --user -u dev-peace -f"
echo "  • Reiniciar serviço:  systemctl --user restart dev-peace"
echo "  • Desabilitar:        systemctl --user disable dev-peace"
echo
log_info "🔧 Para iniciar automaticamente no boot:"
echo "  sudo loginctl enable-linger $USER"
echo
log_warning "⚠️  Lembre-se de configurar o Jira antes de iniciar:"
echo "  dev-peace config --jira-url <url> --jira-user <user> --jira-token <token>"
echo
log_info "🚀 Para iniciar o serviço agora:"
echo "  systemctl --user start dev-peace"
