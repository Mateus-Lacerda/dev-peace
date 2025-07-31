"""
Parser de branches para extrair informações de issues do Jira.
"""

import re
from typing import Optional, Dict, List
from dataclasses import dataclass


@dataclass
class BranchInfo:
    """Informações extraídas de uma branch."""
    original_name: str
    branch_type: Optional[str] = None
    jira_issue: Optional[str] = None
    description: Optional[str] = None
    is_valid_jira_format: bool = False


class JiraBranchParser:
    """Parser para extrair informações de issues do Jira de nomes de branches."""
    
    # Padrões comuns de branches com issues do Jira
    BRANCH_PATTERNS = [
        # Padrão: tipo/PROJ-123-descricao
        r'^(?P<type>[^/]+)/(?P<issue>[A-Z]+-\d+)(?:-(?P<desc>.+))?$',
        
        # Padrão: tipo/PROJ-123
        r'^(?P<type>[^/]+)/(?P<issue>[A-Z]+-\d+)$',
        
        # Padrão: PROJ-123-descricao
        r'^(?P<issue>[A-Z]+-\d+)(?:-(?P<desc>.+))?$',
        
        # Padrão: PROJ-123
        r'^(?P<issue>[A-Z]+-\d+)$',
        
        # Padrão: tipo/PROJ123 (sem hífen)
        r'^(?P<type>[^/]+)/(?P<issue>[A-Z]+\d+)$',
        
        # Padrão: PROJ123 (sem hífen)
        r'^(?P<issue>[A-Z]+\d+)$',
    ]
    
    # Tipos de branch comuns
    COMMON_BRANCH_TYPES = {
        'feature', 'feat', 'bugfix', 'fix', 'hotfix', 'release', 'chore', 
        'docs', 'style', 'refactor', 'test', 'perf', 'build', 'ci'
    }
    
    @classmethod
    def parse_branch(cls, branch_name: str) -> BranchInfo:
        """Analisa o nome da branch e extrai informações."""
        if not branch_name:
            return BranchInfo(original_name="")
        
        branch_info = BranchInfo(original_name=branch_name)
        
        # Tenta cada padrão
        for pattern in cls.BRANCH_PATTERNS:
            match = re.match(pattern, branch_name, re.IGNORECASE)
            if match:
                groups = match.groupdict()
                
                # Extrai tipo da branch
                if 'type' in groups and groups['type']:
                    branch_info.branch_type = groups['type'].lower()
                
                # Extrai issue do Jira
                if 'issue' in groups and groups['issue']:
                    issue = groups['issue'].upper()
                    branch_info.jira_issue = issue
                    branch_info.is_valid_jira_format = cls._is_valid_jira_issue(issue)
                
                # Extrai descrição
                if 'desc' in groups and groups['desc']:
                    branch_info.description = groups['desc'].replace('-', ' ').replace('_', ' ')
                
                break
        
        return branch_info
    
    @classmethod
    def _is_valid_jira_issue(cls, issue: str) -> bool:
        """Valida se o formato da issue do Jira está correto."""
        # Formato padrão: PROJ-123 ou PROJ123
        return bool(re.match(r'^[A-Z]+-?\d+$', issue))
    
    @classmethod
    def extract_jira_issue(cls, branch_name: str) -> Optional[str]:
        """Extrai apenas a issue do Jira do nome da branch."""
        branch_info = cls.parse_branch(branch_name)
        return branch_info.jira_issue if branch_info.is_valid_jira_format else None
    
    @classmethod
    def is_feature_branch(cls, branch_name: str) -> bool:
        """Verifica se é uma branch de feature."""
        branch_info = cls.parse_branch(branch_name)
        return branch_info.branch_type in ['feature', 'feat']
    
    @classmethod
    def is_bugfix_branch(cls, branch_name: str) -> bool:
        """Verifica se é uma branch de bugfix."""
        branch_info = cls.parse_branch(branch_name)
        return branch_info.branch_type in ['bugfix', 'fix', 'hotfix']
    
    @classmethod
    def get_branch_category(cls, branch_name: str) -> str:
        """Retorna a categoria da branch."""
        branch_info = cls.parse_branch(branch_name)
        
        if not branch_info.branch_type:
            return "other"
        
        branch_type = branch_info.branch_type.lower()
        
        if branch_type in ['feature', 'feat']:
            return "feature"
        elif branch_type in ['bugfix', 'fix', 'hotfix']:
            return "bugfix"
        elif branch_type in ['release']:
            return "release"
        elif branch_type in ['chore', 'docs', 'style', 'refactor']:
            return "maintenance"
        elif branch_type in ['test']:
            return "test"
        else:
            return "other"
    
    @classmethod
    def suggest_branch_name(cls, jira_issue: str, branch_type: str = "feature", description: str = "") -> str:
        """Sugere um nome de branch baseado na issue do Jira."""
        if not jira_issue:
            return ""
        
        # Normaliza o tipo da branch
        branch_type = branch_type.lower()
        if branch_type not in cls.COMMON_BRANCH_TYPES:
            branch_type = "feature"
        
        # Normaliza a descrição
        if description:
            desc = re.sub(r'[^a-zA-Z0-9\s]', '', description)
            desc = re.sub(r'\s+', '-', desc.strip()).lower()
            return f"{branch_type}/{jira_issue}-{desc}"
        else:
            return f"{branch_type}/{jira_issue}"
    
    @classmethod
    def validate_branch_name(cls, branch_name: str) -> Dict[str, any]:
        """Valida um nome de branch e retorna informações de validação."""
        branch_info = cls.parse_branch(branch_name)
        
        validation = {
            'is_valid': False,
            'has_jira_issue': False,
            'has_valid_type': False,
            'suggestions': [],
            'warnings': []
        }
        
        # Verifica se tem issue do Jira
        if branch_info.jira_issue and branch_info.is_valid_jira_format:
            validation['has_jira_issue'] = True
        else:
            validation['warnings'].append("Branch não contém uma issue válida do Jira")
        
        # Verifica se tem tipo válido
        if branch_info.branch_type and branch_info.branch_type in cls.COMMON_BRANCH_TYPES:
            validation['has_valid_type'] = True
        else:
            validation['warnings'].append("Branch não tem um tipo reconhecido")
            validation['suggestions'].append("Use tipos como: feature, bugfix, hotfix, chore")
        
        # Branch é válida se tem issue do Jira
        validation['is_valid'] = validation['has_jira_issue']
        
        return validation
