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
            'auto_revert_on_session_end': False,
            'events': {
                'on_work_start': [],      # Lista de {"from": "Status A", "to": "Status B"}
                'on_first_commit': [],
                'on_work_complete': []
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
        return self._process_event(issue_key, 'on_work_start')
    
    def on_first_commit(self, issue_key: str, commit_message: str) -> bool:
        """Executa ação no primeiro commit de uma issue."""
        # Nota: O parâmetro commit_message pode ser usado futuramente para comentários
        return self._process_event(issue_key, 'on_first_commit')
    
    def on_work_complete(self, issue_key: str) -> bool:
        """Executa ação quando trabalho é finalizado."""
        return self._process_event(issue_key, 'on_work_complete')

    def _process_event(self, issue_key: str, event_name: str) -> bool:
        """Processa um evento buscando a regra de transição correspondente ao status atual."""
        if not self.is_enabled() or not self.jira_client:
            return False
        
        event_rules = self.status_rules.get('events', {}).get(event_name, [])
        if not event_rules:
            return False

        try:
            # Busca status atual QUENTE no Jira
            issue_info = self.jira_client.get_issue(issue_key)
            if not issue_info:
                logger.warning(f"Issue {issue_key} não encontrada para evento {event_name}")
                return False

            current_status = issue_info['status']
            
            # Procura uma regra que combine com o status atual
            target_status = None
            for rule in event_rules:
                # 'from' pode ser uma string simples ou uma lista para facilitar
                from_val = rule.get('from')
                if isinstance(from_val, list):
                    if current_status in from_val:
                        target_status = rule.get('to')
                        break
                elif current_status == from_val:
                    target_status = rule.get('to')
                    break

            if not target_status:
                logger.debug(f"Nenhuma regra de transição encontrada para o status atual '{current_status}' da issue {issue_key} no evento {event_name}")
                return False

            # Executa a transição
            logger.info(f"Evento {event_name}: {issue_key} [{current_status}] -> [{target_status}]")
            success = self.jira_client.transition_issue(issue_key, target_status)

            if success:
                logger.info(f"Status da issue {issue_key} alterado para '{target_status}'")
            
            return success

        except Exception as e:
            logger.error(f"Erro ao processar evento {event_name} para {issue_key}: {e}")
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
            'auto_revert_on_session_end': False,
            'events': {
                'on_work_start': [
                    {'from': ['To Do', 'Open', 'Backlog', 'New', 'A FAZER'], 'to': 'In Progress'}
                ],
                'on_first_commit': [],
                'on_work_complete': [
                    {'from': ['In Progress', 'In Review', 'Fazendo'], 'to': 'Done'}
                ]
            }
        }
    
    def reset_to_defaults(self):
        """Reseta regras para os padrões."""
        default_rules = self.get_default_rules()
        self.save_status_rules(default_rules)
        logger.info("Regras de automação de status resetadas para os padrões")
