"""
Modelos de dados para o banco SQLite do Dev Peace.
"""

import sqlite3
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
import os

logger = logging.getLogger(__name__)


@dataclass
class Repository:
    """Modelo para repositórios monitorados."""
    id: Optional[int] = None
    path: str = ""
    name: str = ""
    is_active: bool = True
    created_at: Optional[datetime] = None
    last_activity: Optional[datetime] = None


@dataclass
class WorkSession:
    """Modelo para sessões de trabalho."""
    id: Optional[int] = None
    repository_id: int = 0
    branch_name: str = ""
    jira_issue: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    total_minutes: int = 0
    is_active: bool = True
    jira_worklog_id: Optional[str] = None
    status: str = "active"  # active, completed, orphaned
    original_jira_status: Optional[str] = None  # Status original da issue no Jira
    current_jira_status: Optional[str] = None   # Status atual da issue no Jira


@dataclass
class Activity:
    """Modelo para atividades (modificações, commits)."""
    id: Optional[int] = None
    session_id: int = 0
    activity_type: str = ""  # file_modified, commit, repo_entered
    file_path: Optional[str] = None
    commit_hash: Optional[str] = None
    commit_message: Optional[str] = None
    timestamp: Optional[datetime] = None
    details: Optional[str] = None


@dataclass
class JiraWorklog:
    """Modelo para worklogs enviados ao Jira."""
    id: Optional[int] = None
    session_id: int = 0
    jira_issue: str = ""
    jira_worklog_id: str = ""
    time_spent_minutes: int = 0
    description: str = ""
    sent_at: Optional[datetime] = None
    status: str = "sent"  # sent, failed, pending


@dataclass
class OrphanRecord:
    """Modelo para registros sem issue pai."""
    id: Optional[int] = None
    session_id: int = 0
    branch_name: str = ""
    total_minutes: int = 0
    activities_count: int = 0
    created_at: Optional[datetime] = None
    assigned_issue: Optional[str] = None
    status: str = "orphaned"  # orphaned, assigned


class DatabaseManager:
    """Gerenciador do banco de dados SQLite."""
    
    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            config_dir = Path.home() / ".config" / "dev-peace"
            config_dir.mkdir(parents=True, exist_ok=True)
            db_path = str(config_dir / "database.db")
        
        self.db_path = db_path
        self.init_database()
    
    def get_connection(self) -> sqlite3.Connection:
        """Obtém conexão com o banco de dados."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_database(self):
        """Inicializa o banco de dados com as tabelas necessárias."""
        with self.get_connection() as conn:
            # Tabela de repositórios
            conn.execute("""
                CREATE TABLE IF NOT EXISTS repositories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    path TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_activity TIMESTAMP
                )
            """)
            
            # Tabela de sessões de trabalho
            conn.execute("""
                CREATE TABLE IF NOT EXISTS work_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    repository_id INTEGER NOT NULL,
                    branch_name TEXT NOT NULL,
                    jira_issue TEXT,
                    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    end_time TIMESTAMP,
                    total_minutes INTEGER DEFAULT 0,
                    is_active BOOLEAN DEFAULT 1,
                    jira_worklog_id TEXT,
                    status TEXT DEFAULT 'active',
                    FOREIGN KEY (repository_id) REFERENCES repositories (id)
                )
            """)
            
            # Tabela de atividades
            conn.execute("""
                CREATE TABLE IF NOT EXISTS activities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL,
                    activity_type TEXT NOT NULL,
                    file_path TEXT,
                    commit_hash TEXT,
                    commit_message TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    details TEXT,
                    FOREIGN KEY (session_id) REFERENCES work_sessions (id)
                )
            """)
            
            # Tabela de worklogs do Jira
            conn.execute("""
                CREATE TABLE IF NOT EXISTS jira_worklogs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL,
                    jira_issue TEXT NOT NULL,
                    jira_worklog_id TEXT NOT NULL,
                    time_spent_minutes INTEGER NOT NULL,
                    description TEXT,
                    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'sent',
                    FOREIGN KEY (session_id) REFERENCES work_sessions (id)
                )
            """)
            
            # Tabela de registros órfãos
            conn.execute("""
                CREATE TABLE IF NOT EXISTS orphan_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL,
                    branch_name TEXT NOT NULL,
                    total_minutes INTEGER DEFAULT 0,
                    activities_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    assigned_issue TEXT,
                    status TEXT DEFAULT 'orphaned',
                    FOREIGN KEY (session_id) REFERENCES work_sessions (id)
                )
            """)
            
            conn.commit()

            # Atualiza schema se necessário
            self._update_schema(conn)

    def _update_schema(self, conn: sqlite3.Connection):
        """Atualiza schema do banco de dados para versões mais recentes."""
        try:
            # Verifica se as colunas de status Jira existem
            cursor = conn.execute("PRAGMA table_info(work_sessions)")
            columns = [row[1] for row in cursor.fetchall()]

            if 'original_jira_status' not in columns:
                conn.execute("ALTER TABLE work_sessions ADD COLUMN original_jira_status TEXT")
                logger.debug("Coluna original_jira_status adicionada")

            if 'current_jira_status' not in columns:
                conn.execute("ALTER TABLE work_sessions ADD COLUMN current_jira_status TEXT")
                logger.debug("Coluna current_jira_status adicionada")

            conn.commit()

        except Exception as e:
            logger.error(f"Erro ao atualizar schema: {e}")

    def add_repository(self, path: str, name: str) -> int:
        """Adiciona um repositório ao banco."""
        with self.get_connection() as conn:
            cursor = conn.execute(
                "INSERT INTO repositories (path, name) VALUES (?, ?)",
                (path, name)
            )
            conn.commit()
            return cursor.lastrowid
    
    def get_repository_by_path(self, path: str) -> Optional[Repository]:
        """Busca repositório por caminho."""
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM repositories WHERE path = ?", (path,)
            ).fetchone()
            
            if row:
                return Repository(
                    id=row['id'],
                    path=row['path'],
                    name=row['name'],
                    is_active=bool(row['is_active']),
                    created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
                    last_activity=datetime.fromisoformat(row['last_activity']) if row['last_activity'] else None
                )
            return None
    
    def start_work_session(self, repository_id: int, branch_name: str, jira_issue: Optional[str] = None,
                          original_jira_status: Optional[str] = None, current_jira_status: Optional[str] = None) -> int:
        """Inicia uma nova sessão de trabalho."""
        with self.get_connection() as conn:
            cursor = conn.execute(
                """INSERT INTO work_sessions
                   (repository_id, branch_name, jira_issue, original_jira_status, current_jira_status)
                   VALUES (?, ?, ?, ?, ?)""",
                (repository_id, branch_name, jira_issue, original_jira_status, current_jira_status)
            )
            conn.commit()
            return cursor.lastrowid

    def update_session_jira_status(self, session_id: int, original_status: Optional[str] = None,
                                  current_status: Optional[str] = None):
        """Atualiza os status do Jira para uma sessão."""
        with self.get_connection() as conn:
            updates = []
            params = []

            if original_status is not None:
                updates.append("original_jira_status = ?")
                params.append(original_status)

            if current_status is not None:
                updates.append("current_jira_status = ?")
                params.append(current_status)

            if updates:
                params.append(session_id)
                conn.execute(
                    f"UPDATE work_sessions SET {', '.join(updates)} WHERE id = ?",
                    params
                )
                conn.commit()

    def add_activity(self, session_id: int, activity_type: str, **kwargs) -> int:
        """Adiciona uma atividade à sessão."""
        with self.get_connection() as conn:
            cursor = conn.execute(
                """INSERT INTO activities 
                   (session_id, activity_type, file_path, commit_hash, commit_message, details) 
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (session_id, activity_type, kwargs.get('file_path'), 
                 kwargs.get('commit_hash'), kwargs.get('commit_message'), 
                 kwargs.get('details'))
            )
            conn.commit()
            return cursor.lastrowid

    def end_work_session(self, session_id: int) -> bool:
        """Finaliza uma sessão de trabalho."""
        with self.get_connection() as conn:
            # Calcula tempo total baseado nas atividades
            start_time_row = conn.execute(
                "SELECT start_time FROM work_sessions WHERE id = ?", (session_id,)
            ).fetchone()

            if not start_time_row:
                return False

            now = datetime.now()
            start_time = datetime.fromisoformat(start_time_row['start_time'])
            total_minutes = int((now - start_time).total_seconds() / 60)

            conn.execute(
                """UPDATE work_sessions
                   SET end_time = ?, total_minutes = ?, is_active = 0, status = 'completed'
                   WHERE id = ?""",
                (now.isoformat(), total_minutes, session_id)
            )
            conn.commit()
            return True

    def get_active_session_for_repo(self, repository_id: int) -> Optional[WorkSession]:
        """Busca sessão ativa para um repositório."""
        with self.get_connection() as conn:
            row = conn.execute(
                """SELECT * FROM work_sessions
                   WHERE repository_id = ? AND is_active = 1
                   ORDER BY start_time DESC LIMIT 1""",
                (repository_id,)
            ).fetchone()

            if row:
                return WorkSession(
                    id=row['id'],
                    repository_id=row['repository_id'],
                    branch_name=row['branch_name'],
                    jira_issue=row['jira_issue'],
                    start_time=datetime.fromisoformat(row['start_time']) if row['start_time'] else None,
                    end_time=datetime.fromisoformat(row['end_time']) if row['end_time'] else None,
                    total_minutes=row['total_minutes'],
                    is_active=bool(row['is_active']),
                    jira_worklog_id=row['jira_worklog_id'],
                    status=row['status'],
                    original_jira_status=(
                        row['original_jira_status'] if 'original_jira_status' in row.keys() else None
                    ),
                    current_jira_status=(
                        row['current_jira_status'] if 'current_jira_status' in row.keys() else None
                    )
                )
            return None

    def create_orphan_record(self, session_id: int, branch_name: str) -> int:
        """Cria um registro órfão."""
        with self.get_connection() as conn:
            # Conta atividades da sessão
            activities_count = conn.execute(
                "SELECT COUNT(*) as count FROM activities WHERE session_id = ?",
                (session_id,)
            ).fetchone()['count']

            # Busca tempo total da sessão
            session_row = conn.execute(
                "SELECT total_minutes FROM work_sessions WHERE id = ?",
                (session_id,)
            ).fetchone()

            total_minutes = session_row['total_minutes'] if session_row else 0

            cursor = conn.execute(
                """INSERT INTO orphan_records
                   (session_id, branch_name, total_minutes, activities_count)
                   VALUES (?, ?, ?, ?)""",
                (session_id, branch_name, total_minutes, activities_count)
            )
            conn.commit()
            return cursor.lastrowid

    def get_all_repositories(self) -> List[Repository]:
        """Retorna todos os repositórios."""
        with self.get_connection() as conn:
            rows = conn.execute("SELECT * FROM repositories ORDER BY name").fetchall()
            return [
                Repository(
                    id=row['id'],
                    path=row['path'],
                    name=row['name'],
                    is_active=bool(row['is_active']),
                    created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
                    last_activity=datetime.fromisoformat(row['last_activity']) if row['last_activity'] else None
                )
                for row in rows
            ]

    def toggle_repository_status(self, repository_id: int) -> bool:
        """Ativa/desativa um repositório."""
        with self.get_connection() as conn:
            # Busca status atual
            current_status = conn.execute(
                "SELECT is_active FROM repositories WHERE id = ?", (repository_id,)
            ).fetchone()

            if not current_status:
                return False

            # Inverte o status
            new_status = not bool(current_status['is_active'])

            conn.execute(
                "UPDATE repositories SET is_active = ? WHERE id = ?",
                (new_status, repository_id)
            )
            conn.commit()
            return True

    def get_repository_by_id(self, repository_id: int) -> Optional[Repository]:
        """Busca repositório por ID."""
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM repositories WHERE id = ?", (repository_id,)
            ).fetchone()

            if row:
                return Repository(
                    id=row['id'],
                    path=row['path'],
                    name=row['name'],
                    is_active=bool(row['is_active']),
                    created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
                    last_activity=datetime.fromisoformat(row['last_activity']) if row['last_activity'] else None
                )
            return None

    def get_orphan_records(self) -> List[OrphanRecord]:
        """Retorna todos os registros órfãos."""
        with self.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM orphan_records WHERE status = 'orphaned' ORDER BY created_at DESC"
            ).fetchall()
            return [
                OrphanRecord(
                    id=row['id'],
                    session_id=row['session_id'],
                    branch_name=row['branch_name'],
                    total_minutes=row['total_minutes'],
                    activities_count=row['activities_count'],
                    created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
                    assigned_issue=row['assigned_issue'],
                    status=row['status']
                )
                for row in rows
            ]

    def assign_orphan_issue(self, orphan_id: int, jira_issue: str) -> bool:
        """Associa uma issue do Jira a um registro órfão."""
        with self.get_connection() as conn:
            conn.execute(
                "UPDATE orphan_records SET assigned_issue = ?, status = 'assigned' WHERE id = ?",
                (jira_issue, orphan_id)
            )
            conn.commit()
            return True

    def delete_orphan_record(self, orphan_id: int) -> bool:
        """Exclui um registro órfão."""
        with self.get_connection() as conn:
            conn.execute("DELETE FROM orphan_records WHERE id = ?", (orphan_id,))
            conn.commit()
            return True
