"""
Gerenciador de configurações do Dev Peace.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class ConfigManager:
    """Gerenciador de configurações do Dev Peace."""
    
    def __init__(self, config_file: Optional[str] = None):
        if config_file is None:
            config_dir = Path.home() / ".config" / "dev-peace"
            config_dir.mkdir(parents=True, exist_ok=True)
            config_file = str(config_dir / "config.json")
        
        self.config_file = config_file
        self._config: Dict[str, Any] = {}
        self._load_config()
    
    def _load_config(self):
        """Carrega configurações do arquivo."""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self._config = json.load(f)
                logger.debug(f"Configurações carregadas de {self.config_file}")
            else:
                self._config = self._get_default_config()
                self._save_config()
                logger.info(f"Arquivo de configuração criado: {self.config_file}")
        except Exception as e:
            logger.error(f"Erro ao carregar configurações: {e}")
            self._config = self._get_default_config()
    
    def _save_config(self):
        """Salva configurações no arquivo."""
        try:
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=2, ensure_ascii=False)
            logger.debug(f"Configurações salvas em {self.config_file}")
        except Exception as e:
            logger.error(f"Erro ao salvar configurações: {e}")
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Retorna configurações padrão."""
        return {
            'jira_url': '',
            'jira_user': '',
            'jira_token': '',
            'auto_worklog': True,
            'min_session_minutes': 5,
            'commit_comment_threshold': 1,  # Linhas mínimas para comentar commit
            'worklog_description_template': 'Desenvolvimento - sessão registrada automaticamente',
            'monitoring': {
                'recursive': True,
                'ignore_patterns': [
                    '*.tmp',
                    '*.log',
                    '.DS_Store',
                    'node_modules/*',
                    '.venv/*',
                    '__pycache__/*'
                ]
            },
            'ui': {
                'theme': 'default',
                'show_notifications': True,
                'verbose_logging': False
            }
        }
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """Obtém uma configuração."""
        keys = key.split('.')
        value = self._config
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def set_setting(self, key: str, value: Any):
        """Define uma configuração."""
        keys = key.split('.')
        config = self._config
        
        # Navega até o penúltimo nível
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        # Define o valor
        config[keys[-1]] = value
        self._save_config()
        logger.debug(f"Configuração definida: {key} = {value}")
    
    def get_all_settings(self) -> Dict[str, Any]:
        """Retorna todas as configurações."""
        return self._config.copy()
    
    def reset_to_defaults(self):
        """Reseta configurações para os padrões."""
        self._config = self._get_default_config()
        self._save_config()
        logger.info("Configurações resetadas para os padrões")
    
    def get_jira_config(self) -> Dict[str, str]:
        """Retorna configurações específicas do Jira."""
        return {
            'url': self.get_setting('jira_url', ''),
            'user': self.get_setting('jira_user', ''),
            'token': self.get_setting('jira_token', '')
        }
    
    def is_jira_configured(self) -> bool:
        """Verifica se o Jira está configurado."""
        jira_config = self.get_jira_config()
        return all(jira_config.values())
    
    def get_monitoring_config(self) -> Dict[str, Any]:
        """Retorna configurações de monitoramento."""
        return self.get_setting('monitoring', {})
    
    def should_auto_worklog(self) -> bool:
        """Verifica se deve criar worklogs automaticamente."""
        return self.get_setting('auto_worklog', True)
    
    def get_min_session_minutes(self) -> int:
        """Retorna tempo mínimo de sessão em minutos."""
        return self.get_setting('min_session_minutes', 5)
    
    def get_commit_comment_threshold(self) -> int:
        """Retorna limite de linhas para comentar commits."""
        return self.get_setting('commit_comment_threshold', 1)
    
    def get_worklog_template(self) -> str:
        """Retorna template de descrição do worklog."""
        return self.get_setting('worklog_description_template', 
                               'Desenvolvimento - sessão registrada automaticamente')
    
    def export_config(self, file_path: str) -> bool:
        """Exporta configurações para arquivo."""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=2, ensure_ascii=False)
            logger.info(f"Configurações exportadas para {file_path}")
            return True
        except Exception as e:
            logger.error(f"Erro ao exportar configurações: {e}")
            return False
    
    def import_config(self, file_path: str) -> bool:
        """Importa configurações de arquivo."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                imported_config = json.load(f)
            
            # Valida configurações importadas
            if self._validate_config(imported_config):
                self._config = imported_config
                self._save_config()
                logger.info(f"Configurações importadas de {file_path}")
                return True
            else:
                logger.error("Configurações importadas são inválidas")
                return False
        except Exception as e:
            logger.error(f"Erro ao importar configurações: {e}")
            return False
    
    def _validate_config(self, config: Dict[str, Any]) -> bool:
        """Valida estrutura de configurações."""
        required_keys = ['jira_url', 'jira_user', 'jira_token', 'auto_worklog']
        
        try:
            for key in required_keys:
                if key not in config:
                    return False
            return True
        except Exception:
            return False
    
    def update_config(self, updates: Dict[str, Any]):
        """Atualiza múltiplas configurações."""
        for key, value in updates.items():
            self.set_setting(key, value)
        logger.info(f"Atualizadas {len(updates)} configurações")
    
    def get_config_file_path(self) -> str:
        """Retorna caminho do arquivo de configuração."""
        return self.config_file
