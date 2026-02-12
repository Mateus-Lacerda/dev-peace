
"""
Monitor principal de atividades de desenvolvimento.
"""

import logging
from datetime import datetime
from typing import Optional, Dict, List
from watchdog.observers import Observer

from ..database.models import DatabaseManager, Repository, WorkSession
from ..git_monitor.detector import GitActivityMonitor, GitRepositoryDetector
from ..git_monitor.branch_parser import JiraBranchParser
from ..jira_integration.client import JiraClient
from ..config.settings import ConfigManager
from .status_manager import StatusManager

logger = logging.getLogger(__name__)


class DevPeaceActivityMonitor:
    """Monitor principal que coordena todas as atividades do Dev Peace."""
    
    def __init__(self, db_manager: Optional[DatabaseManager] = None, config: Optional[ConfigManager] = None):
        self.db = db_manager or DatabaseManager()
        self.config = config or ConfigManager()
        self.observer = Observer()
        self.active_sessions: Dict[str, int] = {}  # repo_path -> session_id
        self.monitored_paths: List[str] = []
        self.is_running = False
        self.first_commits: Dict[str, bool] = {}  # session_id -> has_first_commit

        # Inicializa cliente Jira se configurado
        self.jira_client = self._init_jira_client()

        # Inicializa gerenciador de status
        self.status_manager = StatusManager(self.config, self.jira_client)

        # Configura o monitor de atividades Git
        self.git_monitor = GitActivityMonitor(
            on_repo_entered=self._handle_repository_entry,
            on_file_modified=self._handle_file_modification,
            on_commit_detected=self._handle_commit_detection,
            on_branch_changed=self._handle_branch_change
        )

    def _init_jira_client(self) -> Optional[JiraClient]:
        """Inicializa cliente Jira se configurado."""
        jira_config = self.config.get_jira_config()
        if not all(jira_config.values()):
            return None

        try:
            client = JiraClient(jira_config['url'], jira_config['user'], jira_config['token'])
            if client.connect():
                logger.info("Cliente Jira inicializado com sucesso")
                return client
            else:
                logger.warning("Falha ao conectar com Jira")
                return None
        except Exception as e:
            logger.error(f"Erro ao inicializar cliente Jira: {e}")
            return None
    
    def add_repository(self, repo_path: str) -> bool:
        """Adiciona um repositório para monitoramento."""
        try:
            # Verifica se é um repositório Git válido
            if not GitRepositoryDetector.is_git_repository(repo_path):
                logger.error(f"Caminho não é um repositório Git: {repo_path}")
                return False
            
            # Verifica se já está sendo monitorado
            existing_repo = self.db.get_repository_by_path(repo_path)
            if existing_repo:
                logger.info(f"Repositório já está sendo monitorado: {repo_path}")
                return True
            
            # Adiciona ao banco de dados
            repo_name = GitRepositoryDetector.get_repository_name(repo_path)
            repo_id = self.db.add_repository(repo_path, repo_name)
            
            logger.info(f"Repositório adicionado: {repo_name} ({repo_path})")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao adicionar repositório: {e}")
            return False
    
    def start_monitoring(self, paths: Optional[List[str]] = None):
        """Inicia o monitoramento dos repositórios."""
        if self.is_running:
            logger.warning("Monitor já está em execução")
            return
        
        # Se não foram fornecidos caminhos, monitora todos os repositórios do banco
        if not paths:
            repositories = self.db.get_all_repositories()
            paths = [repo.path for repo in repositories if repo.is_active]
        
        # Configura monitoramento para cada caminho
        for path in paths:
            try:
                self.observer.schedule(self.git_monitor, path, recursive=True)
                self.monitored_paths.append(path)
                logger.info(f"Monitorando: {path}")
            except Exception as e:
                logger.error(f"Erro ao configurar monitoramento para {path}: {e}")
        
        if not paths:
            logger.info("Nenhum repositório configurado no momento. Aguardando novos repositórios...")
        
        # Inicia o observador
        self.observer.start()

        self.is_running = True
        logger.info("Monitor de atividades iniciado")
    
    def stop_monitoring(self):
        """Para o monitoramento."""
        if not self.is_running:
            return
        
        # Finaliza sessões ativas
        for repo_path, session_id in self.active_sessions.items():
            self._end_work_session(session_id)
        
        # Para o observador
        self.observer.stop()
        self.observer.join()

        self.is_running = False
        self.active_sessions.clear()
        self.monitored_paths.clear()

        logger.info("Monitor de atividades parado")

    def refresh_repositories(self):
        """Atualiza a lista de repositórios monitorados a partir do banco de dados."""
        if not self.is_running:
            return

        repositories = self.db.get_all_repositories()
        active_paths = [repo.path for repo in repositories if repo.is_active]

        # Encontra novos caminhos para monitorar
        new_paths = [p for p in active_paths if p not in self.monitored_paths]
        
        for path in new_paths:
            try:
                self.observer.schedule(self.git_monitor, path, recursive=True)
                self.monitored_paths.append(path)
                logger.info(f"Novo repositório detectado e monitorado: {path}")
            except Exception as e:
                logger.error(f"Erro ao configurar monitoramento para novo caminho {path}: {e}")
    
    def _handle_repository_entry(self, repo_path: str, repo_name: str, branch_name: str, jira_issue: Optional[str]):
        """Processa entrada em repositório Git."""
        try:
            # Busca ou cria repositório no banco
            repository = self.db.get_repository_by_path(repo_path)
            if not repository:
                repo_id = self.db.add_repository(repo_path, repo_name)
                repository = self.db.get_repository_by_path(repo_path)
            
            if not repository:
                logger.error(f"Erro ao obter repositório: {repo_path}")
                return
            
            # Verifica se já existe sessão ativa para este repositório
            existing_session = self.db.get_active_session_for_repo(repository.id)
            if existing_session:
                # Se a branch mudou, finaliza a sessão anterior
                if existing_session.branch_name != branch_name:
                    self._end_work_session(existing_session.id)
                else:
                    # Sessão já existe para a mesma branch
                    self.active_sessions[repo_path] = existing_session.id
                    logger.info(f"Continuando sessão existente: {branch_name}")
                    return
            
            # Inicia nova sessão de trabalho (status será capturado quando automação for aplicada)
            session_id = self.db.start_work_session(repository.id, branch_name, jira_issue)
            self.active_sessions[repo_path] = session_id

            # Registra atividade de entrada no repositório
            self.db.add_activity(
                session_id=session_id,
                activity_type="repo_entered",
                details=f"Entrada no repositório {repo_name}, branch: {branch_name}"
            )

            logger.info(f"Nova sessão iniciada: {repo_name} - {branch_name}")
            if jira_issue:
                logger.info(f"Issue do Jira detectada: {jira_issue}")

                # Aplica automação de status para início de trabalho
                try:
                    original_status = None

                    # SEMPRE captura status original (para reversão automática)
                    if jira_issue and self.jira_client:
                        issue_info_before = self.jira_client.get_issue(jira_issue)
                        if issue_info_before:
                            original_status = issue_info_before['status']
                            logger.debug(f"Status original capturado para {jira_issue}: {original_status}")

                    success = self.status_manager.on_work_start(jira_issue)

                    # Atualiza a sessão com o status original (sempre, mesmo se automação não foi aplicada)
                    if original_status:
                        if success:
                            # Se automação foi aplicada, captura o novo status
                            issue_info_after = self.jira_client.get_issue(jira_issue) if self.jira_client else None
                            if issue_info_after and isinstance(issue_info_after, Dict):
                                new_status = issue_info_after.copy()['status']
                                self.db.update_session_jira_status(session_id, original_status=original_status, current_status=new_status)
                                logger.debug(f"Status atualizado (com automação) - Original: {original_status}, Atual: {new_status}")
                        else:
                            # Se automação não foi aplicada, status atual = status original
                            self.db.update_session_jira_status(session_id, original_status=original_status, current_status=original_status)
                            logger.debug(f"Status atualizado (sem automação) - Original: {original_status}, Atual: {original_status}")

                except Exception as e:
                    logger.error(f"Erro ao aplicar automação de status para {jira_issue}: {e}")
            else:
                logger.warning(f"Nenhuma issue do Jira encontrada na branch: {branch_name}")
                # Cria registro órfão
                self.db.create_orphan_record(session_id, branch_name)
            
        except Exception as e:
            logger.error(f"Erro ao processar entrada no repositório: {e}")

    def _handle_branch_change(self, repo_path: str, repo_name: str, old_branch: str, new_branch: str, jira_issue: Optional[str]):
        """Processa mudança de branch."""
        try:
            logger.info(f"Mudança de branch detectada: {repo_name}")
            logger.info(f"Branch anterior: {old_branch} → Nova branch: {new_branch}")

            # Busca repositório no banco
            repository = self.db.get_repository_by_path(repo_path)
            if not repository:
                logger.error(f"Repositório não encontrado no banco: {repo_path}")
                return

            # Finaliza sessão anterior se existir
            existing_session = self.db.get_active_session_for_repo(repository.id)
            if existing_session:
                logger.info(f"Finalizando sessão anterior: {old_branch}")
                self._end_work_session(existing_session.id)

            # Inicia nova sessão para a nova branch
            session_id = self.db.start_work_session(repository.id, new_branch, jira_issue)
            self.active_sessions[repo_path] = session_id

            # Registra atividade de mudança de branch
            self.db.add_activity(
                session_id=session_id,
                activity_type="branch_changed",
                details=f"Mudança de branch: {old_branch} → {new_branch}"
            )

            logger.info(f"Nova sessão iniciada: {repo_name} - {new_branch}")

            if jira_issue:
                logger.info(f"Issue do Jira detectada: {jira_issue}")

                # Aplica automação de status para início de trabalho
                try:
                    original_status = None

                    # SEMPRE captura status original (para reversão automática)
                    if jira_issue and self.jira_client:
                        issue_info_before = self.jira_client.get_issue(jira_issue)
                        if issue_info_before:
                            original_status = issue_info_before['status']
                            logger.debug(f"Status original capturado para {jira_issue}: {original_status}")

                    success = self.status_manager.on_work_start(jira_issue)

                    # Atualiza a sessão com o status original (sempre, mesmo se automação não foi aplicada)
                    if original_status:
                        if success:
                            # Se automação foi aplicada, captura o novo status
                            issue_info_after = self.jira_client.get_issue(jira_issue) if self.jira_client else None
                            if issue_info_after and isinstance(issue_info_after, Dict):
                                new_status = issue_info_after.copy()['status']
                                self.db.update_session_jira_status(session_id, original_status=original_status, current_status=new_status)
                                logger.debug(f"Status atualizado (com automação) - Original: {original_status}, Atual: {new_status}")
                        else:
                            # Se automação não foi aplicada, status atual = status original
                            self.db.update_session_jira_status(session_id, original_status=original_status, current_status=original_status)
                            logger.debug(f"Status atualizado (sem automação) - Original: {original_status}, Atual: {original_status}")

                except Exception as e:
                    logger.error(f"Erro ao aplicar automação de status para {jira_issue}: {e}")
            else:
                logger.warning(f"Nenhuma issue do Jira encontrada na branch: {new_branch}")
                # Cria registro órfão
                self.db.create_orphan_record(session_id, new_branch)

        except Exception as e:
            logger.error(f"Erro ao processar mudança de branch: {e}")

    def _handle_file_modification(self, repo_path: str, relative_path: str):
        """Processa modificação de arquivo."""
        try:
            # PRIMEIRO: Verifica se a branch mudou (aproveitando qualquer atividade)
            self._check_branch_change_on_activity(repo_path)

            session_id = self.active_sessions.get(repo_path)
            if not session_id:
                return

            # Registra atividade de modificação
            self.db.add_activity(
                session_id=session_id,
                activity_type="file_modified",
                file_path=relative_path,
                details=f"Arquivo modificado: {relative_path}"
            )

            logger.debug(f"Arquivo modificado registrado: {relative_path}")

        except Exception as e:
            logger.error(f"Erro ao processar modificação de arquivo: {e}")

    def _check_branch_change_on_activity(self, repo_path: str):
        """Verifica se a branch mudou aproveitando qualquer atividade no repositório."""
        try:
            current_branch = GitRepositoryDetector.get_current_branch(repo_path)
            if not current_branch:
                return

            # Verifica se temos uma sessão ativa
            session_id = self.active_sessions.get(repo_path)
            if not session_id:
                return

            # Busca a sessão atual no banco
            repository = self.db.get_repository_by_path(repo_path)
            if not repository:
                return

            active_session = self.db.get_active_session_for_repo(repository.id)
            if not active_session:
                return

            # Verifica se a branch mudou
            if active_session.branch_name != current_branch:
                logger.info(f"Mudança de branch detectada durante atividade: {repo_path}")
                logger.info(f"Branch anterior: {active_session.branch_name} → Nova branch: {current_branch}")

                # Processa a mudança de branch
                repo_name = GitRepositoryDetector.get_repository_name(repo_path)
                jira_issue = GitRepositoryDetector.extract_jira_issue(current_branch)

                self._handle_branch_change(repo_path, repo_name, active_session.branch_name, current_branch, jira_issue)

        except Exception as e:
            logger.error(f"Erro ao verificar mudança de branch: {e}")
    
    def _handle_commit_detection(self, repo_path: str, commit_hash: str, commit_message: Optional[str]):
        """Processa detecção de commit."""
        try:
            session_id = self.active_sessions.get(repo_path)
            if not session_id:
                return
            
            # Registra atividade de commit
            self.db.add_activity(
                session_id=session_id,
                activity_type="commit",
                commit_hash=commit_hash,
                commit_message=commit_message,
                details=f"Commit: {commit_hash[:8]} - {commit_message}"
            )
            
            logger.info(f"Commit registrado: {commit_hash[:8]} - {commit_message}")

            # Verifica se é o primeiro commit da sessão
            is_first_commit = session_id not in self.first_commits
            if is_first_commit:
                self.first_commits[session_id] = True

                # Busca a issue da sessão para automação de status
                session = self.db.get_active_session_for_repo(
                    self.db.get_repository_by_path(repo_path).id
                )

                if session and session.jira_issue:
                    try:
                        self.status_manager.on_first_commit(session.jira_issue, commit_message)
                    except Exception as e:
                        logger.error(f"Erro ao aplicar automação de primeiro commit: {e}")

            # Adiciona comentário no Jira se configurado
            if commit_message and len(commit_message.split('\n')) > self.config.get_commit_comment_threshold():
                session = self.db.get_active_session_for_repo(
                    self.db.get_repository_by_path(repo_path).id
                )

                if session and session.jira_issue and self.jira_client:
                    try:
                        from datetime import datetime
                        self.jira_client.add_comment(
                            session.jira_issue,
                            f"*Commit:* {commit_hash[:8]}\n*Data:* {datetime.now().strftime('%d/%m/%Y %H:%M')}\n*Mensagem:* {commit_message}"
                        )
                        logger.info(f"Comentário de commit adicionado à issue {session.jira_issue}")
                    except Exception as e:
                        logger.error(f"Erro ao adicionar comentário de commit: {e}")
            
        except Exception as e:
            logger.error(f"Erro ao processar commit: {e}")
    
    def _end_work_session(self, session_id: int):
        """Finaliza uma sessão de trabalho."""
        try:
            # Busca informações da sessão antes de finalizar
            session = None

            for repo_path, current_session_id in self.active_sessions.items():
                if current_session_id == session_id:
                    repository = self.db.get_repository_by_path(repo_path)
                    if repository:
                        session = self.db.get_active_session_for_repo(repository.id)
                        break

            success = self.db.end_work_session(session_id)
            if success:
                logger.info(f"Sessão finalizada: {session_id}")

                # Aplica reversão automática de status se configurado
                if session and session.jira_issue and session.original_jira_status:
                    logger.info(f"Aplicando reversão automática para {session.jira_issue}: {session.original_jira_status}")
                    try:
                        result = self.status_manager.on_session_end(session.jira_issue, session.original_jira_status)
                        if result:
                            logger.info(f"Status da issue {session.jira_issue} revertido automaticamente para '{session.original_jira_status}'")
                        else:
                            logger.warning(f"Falha ao reverter status da issue {session.jira_issue}")
                    except Exception as e:
                        logger.error(f"Erro ao reverter status da issue {session.jira_issue}: {e}")


                # TODO: Integrar com Jira para registrar worklog
            else:
                logger.error(f"Erro ao finalizar sessão: {session_id}")
        except Exception as e:
            logger.error(f"Erro ao finalizar sessão: {e}")
    
    def get_active_sessions(self) -> List[WorkSession]:
        """Retorna todas as sessões ativas."""
        active_sessions = []
        for repo_path, session_id in self.active_sessions.items():
            repository = self.db.get_repository_by_path(repo_path)
            if repository:
                session = self.db.get_active_session_for_repo(repository.id)
                if session:
                    active_sessions.append(session)
        return active_sessions
    
    def force_end_session(self, repo_path: str) -> bool:
        """Força o fim de uma sessão específica."""
        session_id = self.active_sessions.get(repo_path)
        if session_id:
            self._end_work_session(session_id)
            del self.active_sessions[repo_path]
            return True
        return False
    
    def get_repository_stats(self) -> Dict[str, any]:
        """Retorna estatísticas dos repositórios monitorados."""
        repositories = self.db.get_all_repositories()
        orphan_records = self.db.get_orphan_records()
        
        return {
            'total_repositories': len(repositories),
            'active_repositories': len([r for r in repositories if r.is_active]),
            'active_sessions': len(self.active_sessions),
            'orphan_records': len(orphan_records),
            'monitored_paths': len(self.monitored_paths),
            'is_running': self.is_running
        }


