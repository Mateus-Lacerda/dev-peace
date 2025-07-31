#!/bin/bash

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Funções de log
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

# Detecta o diretório atual do projeto
CURRENT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_EXECUTABLE="$CURRENT_DIR/venv/bin/dev-peace"
LOCAL_BIN="$HOME/.local/bin"
GLOBAL_EXECUTABLE="$LOCAL_BIN/dev-peace"

log_info "🔗 Instalando Dev Peace globalmente..."
log_info "Diretório do projeto: $CURRENT_DIR"
log_info "Executável: $VENV_EXECUTABLE"

# Verifica se o executável existe
if [ ! -f "$VENV_EXECUTABLE" ]; then
    log_error "Executável não encontrado: $VENV_EXECUTABLE"
    log_error "Execute primeiro: pip install -e ."
    exit 1
fi

# Cria diretório ~/.local/bin se não existir
if [ ! -d "$LOCAL_BIN" ]; then
    log_info "Criando diretório: $LOCAL_BIN"
    mkdir -p "$LOCAL_BIN"
fi

# Remove link simbólico existente se houver
if [ -L "$GLOBAL_EXECUTABLE" ]; then
    log_info "Removendo link simbólico existente..."
    rm "$GLOBAL_EXECUTABLE"
fi

# Cria novo link simbólico
log_info "Criando link simbólico: $GLOBAL_EXECUTABLE -> $VENV_EXECUTABLE"
ln -s "$VENV_EXECUTABLE" "$GLOBAL_EXECUTABLE"

if [ $? -eq 0 ]; then
    log_success "Link simbólico criado com sucesso!"
else
    log_error "Falha ao criar link simbólico"
    exit 1
fi

# Verifica se ~/.local/bin está no PATH
if [[ ":$PATH:" != *":$LOCAL_BIN:"* ]]; then
    log_warning "⚠️  $LOCAL_BIN não está no PATH"
    
    # Detecta shell do usuário
    USER_SHELL=$(basename "$SHELL")
    
    case "$USER_SHELL" in
        "bash")
            SHELL_RC="$HOME/.bashrc"
            ;;
        "zsh")
            SHELL_RC="$HOME/.zshrc"
            ;;
        "fish")
            SHELL_RC="$HOME/.config/fish/config.fish"
            ;;
        *)
            SHELL_RC="$HOME/.profile"
            ;;
    esac
    
    log_info "Shell detectado: $USER_SHELL"
    log_info "Arquivo de configuração: $SHELL_RC"
    
    # Pergunta se quer adicionar ao PATH
    read -p "Deseja adicionar $LOCAL_BIN ao PATH automaticamente? (y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        # Adiciona ao PATH no arquivo de configuração do shell
        if [ "$USER_SHELL" = "fish" ]; then
            echo "set -gx PATH $LOCAL_BIN \$PATH" >> "$SHELL_RC"
        else
            echo "export PATH=\"$LOCAL_BIN:\$PATH\"" >> "$SHELL_RC"
        fi
        
        log_success "PATH atualizado em $SHELL_RC"
        log_info "Execute: source $SHELL_RC"
        log_info "Ou abra um novo terminal"
    else
        log_warning "Adicione manualmente ao seu PATH:"
        log_warning "echo 'export PATH=\"$LOCAL_BIN:\$PATH\"' >> $SHELL_RC"
    fi
else
    log_success "✅ $LOCAL_BIN já está no PATH"
fi

# Testa o comando
log_info "🧪 Testando comando global..."

# Adiciona temporariamente ao PATH para teste
export PATH="$LOCAL_BIN:$PATH"

if command -v dev-peace >/dev/null 2>&1; then
    log_success "✅ Comando 'dev-peace' disponível globalmente!"
    
    # Testa execução
    log_info "Testando execução..."
    if dev-peace --version >/dev/null 2>&1; then
        log_success "✅ Comando executando corretamente!"
    else
        log_warning "⚠️  Comando encontrado mas pode ter problemas de execução"
    fi
else
    log_error "❌ Comando 'dev-peace' não encontrado no PATH"
    log_error "Verifique se $LOCAL_BIN está no seu PATH"
fi

echo
log_success "🎉 Instalação global concluída!"
echo
log_info "📋 Como usar:"
log_info "  • dev-peace --help          - Ver ajuda"
log_info "  • dev-peace status          - Ver status"
log_info "  • dev-peace interactive     - Interface interativa"
log_info "  • dev-peace config --show   - Ver configurações"
echo
log_info "🔧 Se o comando não funcionar:"
log_info "  • Abra um novo terminal"
log_info "  • Ou execute: source $SHELL_RC"
log_info "  • Ou adicione manualmente ao PATH: export PATH=\"$LOCAL_BIN:\$PATH\""
echo
log_info "🚀 Agora você pode usar 'dev-peace' de qualquer diretório!"
