"""
Cliente para integração com Jira.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from jira import JIRA
from jira.exceptions import JIRAError

logger = logging.getLogger(__name__)


class JiraClient:
    """Cliente para interação com Jira."""
    
    def __init__(self, server_url: str, username: str, api_token: str):
        self.server_url = server_url
        self.username = username
        self.api_token = api_token
        self._client: Optional[JIRA] = None
        self._authenticated = False
    
    def connect(self) -> bool:
        """Conecta ao Jira e autentica."""
        try:
            self._client = JIRA(
                server=self.server_url,
                basic_auth=(self.username, self.api_token)
            )
            
            # Testa a conexão
            self._client.myself()
            self._authenticated = True
            logger.info(f"Conectado ao Jira: {self.server_url}")
            return True
            
        except JIRAError as e:
            logger.error(f"Erro ao conectar ao Jira: {e}")
            self._authenticated = False
            return False
        except Exception as e:
            logger.error(f"Erro inesperado ao conectar ao Jira: {e}")
            self._authenticated = False
            return False
    
    def is_connected(self) -> bool:
        """Verifica se está conectado ao Jira."""
        return self._authenticated and self._client is not None
    
    def get_issue(self, issue_key: str) -> Optional[Dict[str, Any]]:
        """Busca uma issue do Jira."""
        if not self.is_connected():
            logger.error("Cliente Jira não está conectado")
            return None
        
        try:
            issue = self._client.issue(issue_key)
            return {
                'key': issue.key,
                'summary': issue.fields.summary,
                'description': issue.fields.description,
                'status': issue.fields.status.name,
                'assignee': issue.fields.assignee.displayName if issue.fields.assignee else None,
                'project': issue.fields.project.key,
                'issue_type': issue.fields.issuetype.name,
                'created': issue.fields.created,
                'updated': issue.fields.updated
            }
        except JIRAError as e:
            if e.status_code == 404:
                logger.warning(f"Issue não encontrada: {issue_key}")
            else:
                logger.error(f"Erro ao buscar issue {issue_key}: {e}")
            return None
        except Exception as e:
            logger.error(f"Erro inesperado ao buscar issue {issue_key}: {e}")
            return None
    
    def issue_exists(self, issue_key: str) -> bool:
        """Verifica se uma issue existe no Jira."""
        return self.get_issue(issue_key) is not None
    
    def add_worklog(self, issue_key: str, time_spent: str, description: str, 
                   started: Optional[datetime] = None) -> Optional[str]:
        """Adiciona um worklog a uma issue."""
        if not self.is_connected():
            logger.error("Cliente Jira não está conectado")
            return None
        
        try:
            # Se não foi fornecida data de início, usa agora
            if started is None:
                started = datetime.now()
            
            worklog = self._client.add_worklog(
                issue=issue_key,
                timeSpent=time_spent,
                comment=description,
                started=started
            )
            
            logger.info(f"Worklog adicionado à issue {issue_key}: {time_spent}")
            return worklog.id
            
        except JIRAError as e:
            logger.error(f"Erro ao adicionar worklog à issue {issue_key}: {e}")
            return None
        except Exception as e:
            logger.error(f"Erro inesperado ao adicionar worklog: {e}")
            return None
    
    def add_comment(self, issue_key: str, comment: str) -> bool:
        """Adiciona um comentário a uma issue."""
        if not self.is_connected():
            logger.error("Cliente Jira não está conectado")
            return False
        
        try:
            self._client.add_comment(issue_key, comment)
            logger.info(f"Comentário adicionado à issue {issue_key}")
            return True
            
        except JIRAError as e:
            logger.error(f"Erro ao adicionar comentário à issue {issue_key}: {e}")
            return False
        except Exception as e:
            logger.error(f"Erro inesperado ao adicionar comentário: {e}")
            return False
    
    def get_worklogs(self, issue_key: str) -> List[Dict[str, Any]]:
        """Obtém todos os worklogs de uma issue."""
        if not self.is_connected():
            logger.error("Cliente Jira não está conectado")
            return []
        
        try:
            worklogs = self._client.worklogs(issue_key)
            return [
                {
                    'id': wl.id,
                    'author': wl.author.displayName,
                    'time_spent': wl.timeSpent,
                    'comment': wl.comment,
                    'started': wl.started,
                    'created': wl.created,
                    'updated': wl.updated
                }
                for wl in worklogs
            ]
        except JIRAError as e:
            logger.error(f"Erro ao buscar worklogs da issue {issue_key}: {e}")
            return []
        except Exception as e:
            logger.error(f"Erro inesperado ao buscar worklogs: {e}")
            return []
    
    def search_issues(self, jql: str, max_results: int = 50) -> List[Dict[str, Any]]:
        """Busca issues usando JQL."""
        if not self.is_connected():
            logger.error("Cliente Jira não está conectado")
            return []
        
        try:
            issues = self._client.search_issues(jql, maxResults=max_results)
            return [
                {
                    'key': issue.key,
                    'summary': issue.fields.summary,
                    'status': issue.fields.status.name,
                    'assignee': issue.fields.assignee.displayName if issue.fields.assignee else None,
                    'project': issue.fields.project.key
                }
                for issue in issues
            ]
        except JIRAError as e:
            logger.error(f"Erro ao buscar issues com JQL '{jql}': {e}")
            return []
        except Exception as e:
            logger.error(f"Erro inesperado ao buscar issues: {e}")
            return []
    
    def get_my_issues(self, status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """Busca issues atribuídas ao usuário atual."""
        jql = f"assignee = currentUser()"
        
        if status_filter:
            jql += f" AND status = '{status_filter}'"
        
        jql += " ORDER BY updated DESC"
        
        return self.search_issues(jql)

    def transition_issue(self, issue_key: str, new_status: str) -> bool:
        """Faz transição de status de uma issue."""
        if not self.is_connected():
            logger.error("Cliente Jira não está conectado")
            return False

        try:
            # Debug: log dos parâmetros recebidos
            logger.debug(f"transition_issue chamado com: issue_key={issue_key}, new_status={new_status} (tipo: {type(new_status)})")

            # Garante que new_status é uma string
            if not isinstance(new_status, str):
                logger.error(f"new_status deve ser string, recebido: {type(new_status)} - {new_status}")
                return False

            # Busca transições disponíveis
            issue = self._client.issue(issue_key)
            transitions = self._client.transitions(issue)

            # Debug: log das transições disponíveis
            logger.debug(f"Transições disponíveis para {issue_key}:")
            for i, transition in enumerate(transitions):
                logger.debug(f"  {i}: {transition}")

            # Procura a transição pelo nome do status
            target_transition = None
            for transition in transitions:
                # Debug: log de cada comparação
                to_name = transition['to']['name']
                logger.debug(f"Comparando '{to_name}' com '{new_status}'")

                if to_name.lower() == new_status.lower():
                    target_transition = transition
                    break

            if not target_transition:
                logger.error(f"Transição para '{new_status}' não disponível para issue {issue_key}")
                available = [t['to']['name'] for t in transitions]
                logger.error(f"Transições disponíveis: {', '.join(available)}")
                return False

            # Executa a transição
            transition_id = target_transition['id']
            logger.debug(f"Executando transição ID: {transition_id}")

            # Executa a transição primeiro
            self._client.transition_issue(issue, transition_id)

            logger.info(f"Issue {issue_key} transicionada para '{new_status}'")
            return True

        except JIRAError as e:
            logger.error(f"Erro ao fazer transição da issue {issue_key}: {e}")
            return False
        except Exception as e:
            logger.error(f"Erro inesperado ao fazer transição: {e}")
            return False

    def get_available_transitions(self, issue_key: str) -> List[Dict[str, Any]]:
        """Obtém transições disponíveis para uma issue."""
        if not self.is_connected():
            logger.error("Cliente Jira não está conectado")
            return []

        try:
            issue = self._client.issue(issue_key)
            transitions = self._client.transitions(issue)

            return [
                {
                    'id': t['id'],
                    'name': t['name'],
                    'to_status': t['to']['name']
                }
                for t in transitions
            ]
        except JIRAError as e:
            logger.error(f"Erro ao buscar transições da issue {issue_key}: {e}")
            return []
        except Exception as e:
            logger.error(f"Erro inesperado ao buscar transições: {e}")
            return []

    def get_project_statuses(self, project_key: str) -> List[str]:
        """Obtém todos os nomes de status únicos disponíveis."""
        if not self.is_connected():
            logger.error("Cliente Jira não está conectado")
            return []

        try:
            # Na versão 3.10.x da lib jira, usamos o método statuses() global
            # Se quisermos filtrar por projeto, precisaríamos de transições de issues reais,
            # mas por simplicidade e robustez, vamos retornar os status globais que 
            # costumam cobrir o que o usuário precisa.
            all_statuses = self._client.statuses()
            return sorted(list(set(s.name for s in all_statuses)))

        except Exception as e:
            logger.error(f"Erro ao buscar status do Jira: {e}")
            return []

    def get_issue_workflow_statuses(self, issue_key: str) -> Dict[str, Any]:
        """Obtém informações completas do workflow de uma issue específica."""
        if not self.is_connected():
            logger.error("Cliente Jira não está conectado")
            return {}

        try:
            issue = self._client.issue(issue_key)
            transitions = self._client.transitions(issue)

            current_status = issue.fields.status.name
            available_transitions = []

            for transition in transitions:
                available_transitions.append({
                    'id': transition['id'],
                    'name': transition['name'],
                    'to_status': transition['to']['name'],
                    'description': transition.get('description', '')
                })

            return {
                'issue_key': issue_key,
                'current_status': current_status,
                'project': issue.fields.project.key,
                'issue_type': issue.fields.issuetype.name,
                'available_transitions': available_transitions,
                'all_possible_statuses': [t['to_status'] for t in available_transitions] + [current_status]
            }

        except JIRAError as e:
            logger.error(f"Erro ao buscar workflow da issue {issue_key}: {e}")
            return {}
        except Exception as e:
            logger.error(f"Erro inesperado ao buscar workflow: {e}")
            return {}

    def get_projects(self) -> List[Dict[str, Any]]:
        """Lista todos os projetos acessíveis."""
        if not self.is_connected():
            logger.error("Cliente Jira não está conectado")
            return []

        try:
            projects = self._client.projects()
            return [
                {
                    'key': project.key,
                    'name': project.name,
                    'description': getattr(project, 'description', ''),
                    'lead': getattr(project.lead, 'displayName', '') if hasattr(project, 'lead') else ''
                }
                for project in projects
            ]
        except JIRAError as e:
            logger.error(f"Erro ao buscar projetos: {e}")
            return []
        except Exception as e:
            logger.error(f"Erro inesperado ao buscar projetos: {e}")
            return []

    def get_all_statuses(self) -> List[str]:
        """Obtém todos os nomes de status únicos disponíveis no servidor Jira."""
        if not self.is_connected():
            return []
        
        try:
            all_statuses = self._client.statuses()
            return sorted(list(set(s.name for s in all_statuses)))
        except Exception as e:
            logger.error(f"Erro ao buscar status globais do Jira: {e}")
            return []

    @staticmethod
    def format_time_spent(minutes: int) -> str:
        """Converte minutos para formato do Jira (ex: 1h 30m)."""
        if minutes <= 0:
            return "1m"  # Mínimo de 1 minuto
        
        hours = minutes // 60
        remaining_minutes = minutes % 60
        
        if hours > 0 and remaining_minutes > 0:
            return f"{hours}h {remaining_minutes}m"
        elif hours > 0:
            return f"{hours}h"
        else:
            return f"{remaining_minutes}m"
    
    @staticmethod
    def parse_time_spent(time_str: str) -> int:
        """Converte formato do Jira para minutos."""
        import re
        
        # Padrões: 1h 30m, 2h, 45m, 1d 2h 30m
        total_minutes = 0
        
        # Dias
        days_match = re.search(r'(\d+)d', time_str)
        if days_match:
            total_minutes += int(days_match.group(1)) * 8 * 60  # 8 horas por dia
        
        # Horas
        hours_match = re.search(r'(\d+)h', time_str)
        if hours_match:
            total_minutes += int(hours_match.group(1)) * 60
        
        # Minutos
        minutes_match = re.search(r'(\d+)m', time_str)
        if minutes_match:
            total_minutes += int(minutes_match.group(1))
        
        return max(total_minutes, 1)  # Mínimo de 1 minuto


class JiraWorklogManager:
    """Gerenciador de worklogs para integração com Dev Peace."""
    
    def __init__(self, jira_client: JiraClient):
        self.jira = jira_client

    def create_worklog_from_session(self, issue_key: str, session_minutes: int,
                                  activities: List[str], start_time: datetime) -> Optional[str]:
        """Cria um worklog baseado em uma sessão de trabalho."""
        if not self.jira.is_connected():
            return None
        
        # Formata tempo gasto
        time_spent = JiraClient.format_time_spent(session_minutes)
        
        # Cria descrição baseada nas atividades
        description = self._create_worklog_description(activities)
        if not description:
            return None
        
        # Adiciona worklog
        return self.jira.add_worklog(issue_key, time_spent, description, start_time)
    
    def add_commit_comment(self, issue_key: str, commit_hash: str, commit_message: str, 
                          commit_time: datetime) -> bool:
        """Adiciona comentário de commit à issue."""
        if not self.jira.is_connected():
            return False
        
        # Formata comentário
        comment = f"*Commit:* {commit_hash[:8]}\n"
        comment += f"*Data:* {commit_time.strftime('%d/%m/%Y %H:%M')}\n"
        comment += f"*Mensagem:* {commit_message}"
        
        return self.jira.add_comment(issue_key, comment)
    
    def _create_worklog_description(self, activities: List[str]) -> str | None:
        """Cria descrição do worklog baseada nas atividades."""
        if not activities:
            # return "Desenvolvimento - sessão registrada automaticamente pelo Dev Peace"
            return None

        # Agrupa atividades por tipo
        file_modifications = [a for a in activities if "Arquivo modificado" in a]
        commits = [a for a in activities if "Commit" in a]
        
        description = "Registro de desenvolvimento:\n"

        if file_modifications:
            description += f"• {len(file_modifications)} arquivo(s) modificado(s)\n"
        
        if commits:
            description += f"• {len(commits)} commit(s) realizado(s)\n"
            # Adiciona mensagens dos commits mais recentes
            recent_commits = commits[-3:]  # Últimos 3 commits
            for commit in recent_commits:
                if " - " in commit:
                    commit_msg = commit.split(" - ", 1)[1]
                    description += f"  - {commit_msg}\n"
        
        return description
