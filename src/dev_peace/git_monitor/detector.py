"""
Detector de repositórios Git e atividades de desenvolvimento.
"""

import os
import re
from pathlib import Path
from typing import Optional, Tuple, List
from watchdog.events import FileSystemEventHandler, FileSystemEvent
import pygit2
import logging

logger = logging.getLogger(__name__)


class GitRepositoryDetector:
    """Detector de repositórios Git e extrator de informações."""
    
    @staticmethod
    def is_git_repository(path: str) -> bool:
        """Verifica se o caminho é um repositório Git."""
        git_dir = Path(path) / ".git"
        return git_dir.exists() and (git_dir.is_dir() or git_dir.is_file())
    
    @staticmethod
    def get_repository_root(path: str) -> Optional[str]:
        """Encontra a raiz do repositório Git."""
        current_path = Path(path).resolve()
        
        while current_path != current_path.parent:
            if GitRepositoryDetector.is_git_repository(str(current_path)):
                return str(current_path)
            current_path = current_path.parent
        
        return None
    
    @staticmethod
    def get_current_branch(repo_path: str) -> Optional[str]:
        """Obtém a branch atual do repositório."""
        try:
            repo = pygit2.Repository(repo_path)
            if repo.head_is_unborn:
                return None
            
            branch_name = repo.head.shorthand
            return branch_name
        except Exception as e:
            logger.error(f"Erro ao obter branch atual: {e}")
            return None
    
    @staticmethod
    def extract_jira_issue(branch_name: str) -> Optional[str]:
        """Extrai a issue do Jira do nome da branch."""
        if not branch_name:
            return None
        
        # Padrões comuns para branches com issues do Jira
        patterns = [
            r'[^/]+/([A-Z]+-\d+)',  # tipo/PROJ-123
            r'([A-Z]+-\d+)',        # PROJ-123
            r'[^/]+/([A-Z]+\d+)',   # tipo/PROJ123
            r'([A-Z]+\d+)',         # PROJ123
        ]
        
        for pattern in patterns:
            match = re.search(pattern, branch_name, re.IGNORECASE)
            if match:
                issue = match.group(1).upper()
                # Valida formato básico de issue do Jira
                if re.match(r'^[A-Z]+-?\d+$', issue):
                    return issue
        
        return None
    
    @staticmethod
    def get_repository_name(repo_path: str) -> str:
        """Obtém o nome do repositório."""
        return Path(repo_path).name


class GitActivityMonitor(FileSystemEventHandler):
    """Monitor de atividades em repositórios Git."""

    def __init__(self, on_repo_entered=None, on_file_modified=None, on_commit_detected=None, on_branch_changed=None):
        super().__init__()
        self.on_repo_entered = on_repo_entered
        self.on_file_modified = on_file_modified
        self.on_commit_detected = on_commit_detected
        self.on_branch_changed = on_branch_changed
        self.tracked_repos = {}  # path -> last_activity_time
        self.tracked_branches = {}  # repo_path -> current_branch
        self.git_operations = set()  # Para rastrear operações Git em andamento
    
    def on_opened(self, event: FileSystemEvent):
        """Chamado quando um arquivo é aberto."""
        if event.is_directory:
            return
        
        file_path = event.src_path
        
        # Detecta entrada em repositório Git
        if self._is_git_entry_pattern(file_path):
            self._handle_repository_entry(file_path)
    
    def on_modified(self, event: FileSystemEvent):
        """Chamado quando um arquivo é modificado."""
        if event.is_directory:
            return

        file_path = event.src_path

        # Debug: log de todos os arquivos modificados
        logger.debug(f"Arquivo modificado detectado: {file_path}")

        # Detecta mudanças de branch (PRIORIDADE ALTA)
        if self._is_branch_change_pattern(file_path):
            logger.debug(f"Padrão de mudança de branch detectado: {file_path}")
            self._handle_branch_change(file_path)
            return  # Importante: retorna aqui para não processar como arquivo interno

        # Detecta commits
        if self._is_commit_pattern(file_path):
            logger.debug(f"Padrão de commit detectado: {file_path}")
            self._handle_commit_detection(file_path)
            return  # Importante: retorna aqui para não processar como arquivo interno

        # Detecta modificações de arquivos normais (apenas se não for arquivo interno do Git)
        if not self._is_git_internal_file(file_path):
            self._handle_file_modification(file_path)
    
    def _is_git_entry_pattern(self, file_path: str) -> bool:
        """Verifica se o arquivo indica entrada em repositório Git."""
        path = Path(file_path)
        
        # Padrão: abertura de .git/HEAD ou .git/index
        if path.name in ['HEAD', 'index'] and path.parent.name == '.git':
            return True
        
        return False
    
    def _is_commit_pattern(self, file_path: str) -> bool:
        """Verifica se o arquivo indica um commit."""
        path = Path(file_path)

        # Padrão melhor: mudanças no arquivo .git/logs/HEAD que registra commits
        if path.name == 'HEAD' and path.parent.name == 'logs' and path.parent.parent.name == '.git':
            return True

        return False
    
    def _is_branch_change_pattern(self, file_path: str) -> bool:
        """Verifica se o arquivo indica mudança de branch."""
        path = Path(file_path)

        # Debug: log de verificação
        if path.name == 'HEAD' and path.parent.name == '.git':
            logger.debug(f"Arquivo .git/HEAD detectado: {file_path}")
            return True

        return False

    def _is_git_internal_file(self, file_path: str) -> bool:
        """Verifica se é um arquivo interno do Git."""
        return '.git' in Path(file_path).parts
    
    def _handle_repository_entry(self, file_path: str):
        """Processa entrada em repositório Git."""
        repo_root = GitRepositoryDetector.get_repository_root(file_path)
        if not repo_root:
            return
        
        # Evita múltiplas detecções do mesmo repositório
        if repo_root in self.tracked_repos:
            return
        
        self.tracked_repos[repo_root] = True
        
        branch_name = GitRepositoryDetector.get_current_branch(repo_root)
        jira_issue = GitRepositoryDetector.extract_jira_issue(branch_name) if branch_name else None
        repo_name = GitRepositoryDetector.get_repository_name(repo_root)
        
        logger.info(f"Entrada detectada no repositório: {repo_name}")
        logger.info(f"Branch: {branch_name}")
        logger.info(f"Issue do Jira: {jira_issue}")
        
        if self.on_repo_entered:
            self.on_repo_entered(repo_root, repo_name, branch_name, jira_issue)
    
    def _handle_file_modification(self, file_path: str):
        """Processa modificação de arquivo."""
        repo_root = GitRepositoryDetector.get_repository_root(file_path)
        if not repo_root:
            return
        
        # Calcula caminho relativo
        relative_path = os.path.relpath(file_path, repo_root)
        
        logger.debug(f"Arquivo modificado: {relative_path}")
        
        if self.on_file_modified:
            self.on_file_modified(repo_root, relative_path)

    def _handle_branch_change(self, file_path: str):
        """Processa mudança de branch."""
        repo_root = GitRepositoryDetector.get_repository_root(file_path)
        if not repo_root:
            return

        # Obtém a nova branch
        new_branch = GitRepositoryDetector.get_current_branch(repo_root)
        if not new_branch:
            return

        # Verifica se a branch realmente mudou
        old_branch = self.tracked_branches.get(repo_root)
        if old_branch == new_branch:
            return

        # Atualiza branch rastreada
        self.tracked_branches[repo_root] = new_branch

        # Se é a primeira vez que vemos este repositório, não é uma mudança
        if old_branch is None:
            return

        # Processa mudança de branch
        jira_issue = GitRepositoryDetector.extract_jira_issue(new_branch)
        repo_name = GitRepositoryDetector.get_repository_name(repo_root)

        logger.info(f"Mudança de branch detectada no repositório: {repo_name}")
        logger.info(f"Branch anterior: {old_branch}")
        logger.info(f"Nova branch: {new_branch}")
        logger.info(f"Issue do Jira: {jira_issue}")

        # Chama callback de mudança de branch
        if self.on_branch_changed:
            self.on_branch_changed(repo_root, repo_name, old_branch, new_branch, jira_issue)

    def _handle_commit_detection(self, file_path: str):
        """Processa detecção de commit."""
        repo_root = GitRepositoryDetector.get_repository_root(file_path)
        if not repo_root:
            return

        # Lê o último commit do arquivo .git/logs/HEAD
        commit_hash = self._get_latest_commit_hash(repo_root)
        if not commit_hash:
            return

        # Evita múltiplas detecções do mesmo commit
        commit_key = f"{repo_root}:{commit_hash}"
        if commit_key in self.git_operations:
            return

        self.git_operations.add(commit_key)

        # Obtém informações do commit
        commit_message = self._get_commit_message(repo_root, commit_hash)

        logger.info(f"Commit detectado: {commit_hash[:8]}")
        logger.info(f"Mensagem: {commit_message}")

        if self.on_commit_detected:
            self.on_commit_detected(repo_root, commit_hash, commit_message)
    
    def _get_commit_message(self, repo_root: str, commit_hash: str) -> Optional[str]:
        """Obtém a mensagem do commit."""
        try:
            repo = pygit2.Repository(repo_root)
            obj = repo.get(commit_hash)
            # Verifica se o objeto tem o atributo message (é um commit)
            if obj and hasattr(obj, 'message') and obj.message:
                return obj.message.strip()
        except Exception as e:
            logger.error("Erro ao obter mensagem do commit: %s", e)

        return None

    def _get_latest_commit_hash(self, repo_root: str) -> Optional[str]:
        """Obtém o hash do último commit do arquivo .git/logs/HEAD."""
        try:
            head_log_path = Path(repo_root) / '.git' / 'logs' / 'HEAD'
            if not head_log_path.exists():
                return None

            # Lê a última linha do arquivo (último commit)
            with open(head_log_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                if lines:
                    last_line = lines[-1].strip()
                    # Formato: old_hash new_hash author timestamp message
                    parts = last_line.split(' ', 2)
                    if len(parts) >= 2:
                        return parts[1]  # new_hash é o hash do commit
        except Exception as e:
            logger.error("Erro ao obter hash do último commit: %s", e)

        return None

    def reset_tracking(self):
        """Reseta o rastreamento de repositórios."""
        self.tracked_repos.clear()
        self.git_operations.clear()
