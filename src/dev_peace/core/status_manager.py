"""
Gerenciador de status automático de issues do Jira.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from ..config.settings import ConfigManager
from ..jira_integration.client import JiraClient

logger = logging.getLogger(__name__)


class StatusManager:
    """Gerenciador de mudanças automáticas de status no Jira."""
    
    def __init__(self, config: ConfigManager, jira_client: Optional[JiraClient] = None):
        self.config = config
        self.jira_client = jira_client
        self.status_rules = self._load_status_rules()

    def _load_status_rules(self) -> Dict[str, Any]:
        """Carrega regras de mudança de status da configuração."""
        return self.config.get_setting('status_automation', {
            'enabled': False,
            'auto_revert_on_session_end': False,  # Reverte status automaticamente quando sessão é finalizada
            'rules': {
                'on_work_start': {
                    'enabled': True,
                    'from_status': ['To Do', 'Open', 'Backlog'],
                    'to_status': 'In Progress',
                },
                'on_first_commit': {
                    'enabled': False,
                    'from_status': ['To Do', 'Open', 'Backlog'],
                    'to_status': 'In Progress',
                },
                'on_work_complete': {
                    'enabled': False,
                    'from_status': ['In Progress'],
                    'to_status': 'Done',
                }
            }
        })
    
    def save_status_rules(self, rules: Dict[str, Any]):
        """Salva regras de mudança de status na configuração."""
        self.config.set_setting('status_automation', rules)
        self.status_rules = rules
    
    def is_enabled(self) -> bool:
        """Verifica se a automação de status está habilitada."""
        return self.status_rules.get('enabled', False)

    def is_auto_revert_enabled(self) -> bool:
        """Verifica se a reversão automática de status está habilitada."""
        return self.status_rules.get('auto_revert_on_session_end', False)
    
    def on_work_start(self, issue_key: str) -> bool:
        """Executa ação quando trabalho é iniciado em uma issue."""
        if not self.is_enabled() or not self.jira_client:
            return False
        
        rule = self.status_rules.get('rules', {}).get('on_work_start', {})
        if not rule.get('enabled', False):
            return False
        
        return self._apply_status_rule(issue_key, rule, 'work_start')
    
    def on_first_commit(self, issue_key: str, commit_message: str) -> bool:
        """Executa ação no primeiro commit de uma issue."""
        if not self.is_enabled() or not self.jira_client:
            return False
        
        rule = self.status_rules.get('rules', {}).get('on_first_commit', {})
        if not rule.get('enabled', False):
            return False
        
        # Substitui placeholder na mensagem
        rule = rule.copy()
        if 'comment' in rule:
            rule['comment'] = rule['comment'].format(commit_message=commit_message)
        
        return self._apply_status_rule(issue_key, rule, 'first_commit')
    
    def on_work_complete(self, issue_key: str) -> bool:
        """Executa ação quando trabalho é finalizado."""
        if not self.is_enabled() or not self.jira_client:
            return False
        
        rule = self.status_rules.get('rules', {}).get('on_work_complete', {})
        if not rule.get('enabled', False):
            return False
        
        return self._apply_status_rule(issue_key, rule, 'work_complete')
    
    def _apply_status_rule(self, issue_key: str, rule: Dict[str, Any], event_type: str) -> bool:
        """Aplica uma regra de mudança de status."""
        try:
            # Busca informações da issue
            issue_info = self.jira_client.get_issue(issue_key)
            if not issue_info:
                logger.warning(f"Issue {issue_key} não encontrada para evento {event_type}")
                return False

            current_status = issue_info['status']
            from_statuses = rule.get('from_status', [])
            to_status = rule.get('to_status')

            # Verifica se o status atual permite a transição
            if from_statuses and current_status not in from_statuses:
                logger.debug(f"Status atual '{current_status}' não está na lista permitida {from_statuses}")
                return False

            if not to_status:
                logger.error(f"Status de destino não definido na regra {event_type}")
                return False

            # Executa a transição
            logger.info(f"Aplicando regra {event_type}: {issue_key} {current_status} → {to_status}")

            success = self.jira_client.transition_issue(issue_key, to_status)

            if success:
                logger.info(f"Status da issue {issue_key} alterado automaticamente para '{to_status}'")
            else:
                logger.warning(f"Falha ao alterar status da issue {issue_key} para '{to_status}'")

            return success

        except Exception as e:
            logger.error(f"Erro ao aplicar regra de status {event_type} para {issue_key}: {e}")
            return False

    def on_session_end(self, issue_key: str, original_status: str) -> bool:
        """Executa ação quando uma sessão é finalizada."""
        if not self.is_enabled() or not self.jira_client:
            return False

        if not self.is_auto_revert_enabled():
            return False

        try:
            # Busca informações atuais da issue
            issue_info = self.jira_client.get_issue(issue_key)
            if not issue_info:
                logger.warning(f"Issue {issue_key} não encontrada para reversão")
                return False

            current_status = issue_info['status']

            # Se o status já está no estado original, considera como sucesso
            if current_status == original_status:
                logger.debug(f"Status da issue {issue_key} já está no estado original '{original_status}', reversão não necessária")
                return True

            # Executa a reversão
            logger.info(f"Revertendo status da issue {issue_key}: {current_status} → {original_status}")

            success = self.jira_client.transition_issue(issue_key, original_status)

            if success:
                logger.info(f"Status da issue {issue_key} revertido automaticamente para '{original_status}'")
            else:
                logger.warning(f"Falha ao reverter status da issue {issue_key} para '{original_status}'")

            return success

        except Exception as e:
            logger.error(f"Erro ao reverter status da issue {issue_key}: {e}")
            return False
    
    def get_available_statuses(self, issue_key: str) -> List[str]:
        """Obtém status disponíveis para transição de uma issue."""
        if not self.jira_client:
            return []
        
        transitions = self.jira_client.get_available_transitions(issue_key)
        return [t['to_status'] for t in transitions]
    
    def validate_rule(self, rule: Dict[str, Any], issue_key: Optional[str] = None) -> Dict[str, Any]:
        """Valida uma regra de mudança de status."""
        validation = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        # Validações básicas
        if not rule.get('to_status'):
            validation['valid'] = False
            validation['errors'].append("Status de destino é obrigatório")
        
        # Se temos uma issue específica, valida transições
        if issue_key and self.jira_client:
            available_statuses = self.get_available_statuses(issue_key)
            to_status = rule.get('to_status')
            
            if to_status and to_status not in available_statuses:
                validation['warnings'].append(
                    f"Status '{to_status}' pode não estar disponível para transição"
                )
        
        return validation
    
    def get_default_rules(self) -> Dict[str, Any]:
        """Retorna regras padrão de automação de status."""
        return {
            'enabled': False,
            'rules': {
                'on_work_start': {
                    'enabled': True,
                    'from_status': ['To Do', 'Open', 'Backlog', 'New'],
                    'to_status': 'In Progress',
                    'comment': 'Trabalho iniciado automaticamente pelo Dev Peace'
                },
                'on_first_commit': {
                    'enabled': False,
                    'from_status': ['To Do', 'Open', 'Backlog', 'New'],
                    'to_status': 'In Progress',
                    'comment': 'Primeiro commit realizado: {commit_message}'
                },
                'on_work_complete': {
                    'enabled': False,
                    'from_status': ['In Progress', 'In Review'],
                    'to_status': 'Done',
                    'comment': 'Trabalho finalizado automaticamente pelo Dev Peace'
                }
            }
        }
    
    def reset_to_defaults(self):
        """Reseta regras para os padrões."""
        default_rules = self.get_default_rules()
        self.save_status_rules(default_rules)
        logger.info("Regras de automação de status resetadas para os padrões")
