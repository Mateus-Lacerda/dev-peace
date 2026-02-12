"""
Interface interativa com InquirerPy.
"""

from pathlib import Path
from typing import Optional
from InquirerPy import inquirer
from InquirerPy.base.control import Choice
from InquirerPy.separator import Separator

from ..database.models import DatabaseManager
from ..core.activity_monitor import DevPeaceActivityMonitor
from ..config.settings import ConfigManager
from ..jira_integration.client import JiraClient


class InteractiveInterface:
    """Interface interativa bonita para o Dev Peace."""
    
    def __init__(self, db: DatabaseManager, monitor: DevPeaceActivityMonitor, config: ConfigManager):
        self.db = db
        self.monitor = monitor
        self.config = config
        self.jira_client: Optional[JiraClient] = None
    
    def run(self) -> int:
        """Executa a interface interativa."""
        print(r'''
  _____                             _.-.                   _____                    
 |  __ \                        .-.  `) |  .-.            |  __ \                   
 | |  | | _____   __        _.'`. .~./  \.~. .`'._        | |__) |__  __ _  ___ ___ 
 | |  | |/ _ \ \ / /    .-'`.'-'.'.-:    ;-.'.'-'.`'-.    |  ___/ _ \/ _` |/ __/ _ \
 | |__| |  __/\ V /      `'`'`'`'`   \  /   `'`'`'`'`     | |  |  __/ (_| | (_|  __/
 |_____/ \___| \_/                   /||\                 |_|   \___|\__,_|\___\___|
                          jgs       / ^^ \                                       
                                    `'``'`
''')
        print("Bem-vindo à interface interativa do Dev Peace!")
        print("Use as setas para navegar e Enter para selecionar\n")
        
        while True:
            try:
                choice = self._show_main_menu()
                
                if choice == 'exit':
                    print("Até logo! Que a paz esteja com seu código!")
                    return 0
                elif choice == 'status':
                    self._show_status()
                elif choice == 'repositories':
                    self._manage_repositories()
                elif choice == 'orphans':
                    self._manage_orphans()
                elif choice == 'config':
                    self._manage_config()
                elif choice == 'monitoring':
                    self._manage_monitoring()
                elif choice == 'jira':
                    self._manage_jira()
                
            except KeyboardInterrupt:
                print("\nAté logo!")
                return 0
            except Exception as e:
                print(f"\nErro inesperado: {e}")
                input("Pressione Enter para continuar...")
    
    def _show_main_menu(self) -> str:
        """Mostra o menu principal."""
        choices = [
            Choice("status",       "[Status]   Ver Status"),
            Choice("repositories", "[Repos]    Gerenciar Repositórios"),
            Choice("monitoring",   "[Monitor]  Controlar Monitoramento"),
            Choice("orphans",      "[Orphans]  Registros Órfãos"),
            Choice("jira",         "[Jira]     Integração Jira"),
            Choice("config",       "[Config]   Configurações"),
            Separator(),
            Choice("exit",         "[Sair]     Sair")
        ]
        
        return inquirer.select(
            message="O que você gostaria de fazer?",
            choices=choices,
            default="status"
        ).execute()
    
    def _show_status(self):
        """Mostra status detalhado."""
        stats = self.monitor.get_repository_stats()
        
        print("\nStatus do Dev Peace")
        print("=" * 40)
        print(f"Status: {'[Rodando]' if stats['is_running'] else '[Parado]'}")
        print(f"Repositórios: {stats['total_repositories']} total, {stats['active_repositories']} ativos")
        print(f"Sessões ativas: {stats['active_sessions']}")
        print(f"Registros órfãos: {stats['orphan_records']}")
        print(f"Caminhos monitorados: {stats['monitored_paths']}")
        
        # Sessões ativas
        active_sessions = self.monitor.get_active_sessions()
        if active_sessions:
            print("\nSessões ativas:")
            for session in active_sessions:
                issue_info = f" ({session.jira_issue})" if session.jira_issue else " (sem issue)"
                print(f"  * {session.branch_name}{issue_info}")
        
        input("\nPressione Enter para continuar...")
    
    def _manage_repositories(self):
        """Gerencia repositórios."""
        while True:
            action = inquirer.select(
                message="Gerenciar repositórios:",
                choices=[
                    Choice("list",   "[Listar]  Listar repositórios"),
                    Choice("add",    "[Add]     Adicionar repositório"),
                    Choice("toggle", "[Toggle]  Ativar/Desativar repositório"),
                    Separator(),
                    Choice("back",   "[Voltar]  Voltar")
                ]
            ).execute()
            
            if action == "back":
                break
            elif action == "list":
                self._list_repositories()
            elif action == "add":
                self._add_repository()
            elif action == "toggle":
                self._toggle_repository()
    
    def _list_repositories(self):
        """Lista repositórios."""
        repositories = self.db.get_all_repositories()
        
        if not repositories:
            print("\nNenhum repositório encontrado")
            input("Pressione Enter para continuar...")
            return
        
        print("\nRepositórios monitorados:")
        print("=" * 50)
        
        for repo in repositories:
            status = "[Ativo]" if repo.is_active else "[Inativo]"
            print(f"\n{status} - {repo.name}")
            print(f"Local: {repo.path}")
            if repo.last_activity:
                print(f"Ultima atividade: {repo.last_activity}")
        
        input("\nPressione Enter para continuar...")
    
    def _add_repository(self):
        """Adiciona repositório."""
        path = inquirer.filepath(
            message="Selecione o caminho do repositório:",
            validate=lambda x: Path(x).is_dir() if x else False,
            invalid_message="Por favor, selecione um diretório válido"
        ).execute()

        if path:
            print(f"\nAdicionando repositório: {path}")
            if self.monitor.add_repository(str(path)):
                print("Repositório adicionado com sucesso!")
            else:
                print("Erro ao adicionar repositório")

            input("Pressione Enter para continuar...")
    
    def _toggle_repository(self):
        """Ativa/desativa repositório."""
        repositories = self.db.get_all_repositories()

        if not repositories:
            print("\nNenhum repositório encontrado")
            input("Pressione Enter para continuar...")
            return

        choices = []
        for repo in repositories:
            status = "[+]" if repo.is_active else "[-]"
            choices.append(Choice(repo.id, f"{status} {repo.name}"))

        repo_id = inquirer.select(
            message="Selecione o repositório:",
            choices=choices
        ).execute()

        # Busca repositório e alterna status
        repo = self.db.get_repository_by_id(repo_id)
        if repo:
            if self.db.toggle_repository_status(repo_id):
                new_status = "ativado" if not repo.is_active else "desativado"
                print(f"\nRepositório {repo.name} foi {new_status}!")
            else:
                print(f"\nErro ao alterar status do repositório {repo.name}")
        else:
            print("\nRepositório não encontrado")

        input("Pressione Enter para continuar...")
    
    def _manage_orphans(self):
        """Gerencia registros órfãos."""
        orphans = self.db.get_orphan_records()
        
        if not orphans:
            print("\nNenhum registro órfão! Tudo organizado!")
            input("Pressione Enter para continuar...")
            return
        
        print(f"\nEncontrados {len(orphans)} registros órfãos")
        
        action = inquirer.select(
            message="O que fazer com os órfãos?",
            choices=[
                Choice("list",   "[Listar]  Listar todos"),
                Choice("assign", "[Link]    Associar issue manualmente"),
                Choice("delete", "[Del]     Excluir órfão"),
                Separator(),
                Choice("back",   "[Voltar]  Voltar")
            ]
        ).execute()
        
        if action == "back":
            return
        elif action == "list":
            self._list_orphans(orphans)
        elif action == "assign":
            self._assign_orphan_issue(orphans)
        elif action == "delete":
            self._delete_orphan(orphans)
    
    def _list_orphans(self, orphans):
        """Lista registros órfãos."""
        print("\nRegistros órfãos:")
        print("=" * 40)
        
        for i, orphan in enumerate(orphans, 1):
            print(f"\n{i}. Branch: {orphan.branch_name}")
            print(f"   Tempo: {orphan.total_minutes} minutos")
            print(f"   Atividades: {orphan.activities_count}")
            print(f"   Criado: {orphan.created_at}")
        
        input("\nPressione Enter para continuar...")
    
    def _assign_orphan_issue(self, orphans):
        """Associa issue a um órfão."""
        choices = []
        for orphan in orphans:
            choices.append(Choice(
                orphan.id,
                f"Branch: {orphan.branch_name} ({orphan.total_minutes}min, {orphan.activities_count} atividades)"
            ))

        orphan_id = inquirer.select(
            message="Selecione o registro órfão:",
            choices=choices
        ).execute()

        issue_key = inquirer.text(
            message="Digite a issue do Jira (ex: PROJ-123):",
            validate=lambda x: len(x) > 0,
            invalid_message="Issue não pode estar vazia"
        ).execute()

        print(f"\nAssociando issue {issue_key} ao registro órfão...")

        # Testa se a issue existe no Jira (se configurado)
        if self.jira_client and self.jira_client.is_connected():
            if not self.jira_client.issue_exists(issue_key):
                print(f"Aviso: Issue {issue_key} não encontrada no Jira")
                if not inquirer.confirm("Continuar mesmo assim?", default=False).execute():
                    return

        # Associa a issue
        if self.db.assign_orphan_issue(orphan_id, issue_key):
            print("Issue associada com sucesso!")
        else:
            print("Erro ao associar issue")

        input("Pressione Enter para continuar...")
    
    def _delete_orphan(self, orphans):
        """Exclui um órfão."""
        choices = []
        for orphan in orphans:
            choices.append(Choice(
                orphan.id,
                f"Branch: {orphan.branch_name} ({orphan.total_minutes}min, {orphan.activities_count} atividades)"
            ))

        orphan_id = inquirer.select(
            message="Selecione o registro órfão para excluir:",
            choices=choices
        ).execute()

        # Confirma exclusão
        if inquirer.confirm("Tem certeza que deseja excluir este registro?", default=False).execute():
            if self.db.delete_orphan_record(orphan_id):
                print("\nRegistro órfão excluído com sucesso!")
            else:
                print("\nErro ao excluir registro órfão")
        else:
            print("\nExclusão cancelada")

        input("Pressione Enter para continuar...")
    
    def _manage_config(self):
        """Gerencia configurações."""
        while True:
            action = inquirer.select(
                message="Configurações:",
                choices=[
                    Choice("show", "[Ver]     Ver configurações"),
                    Choice("jira", "[Jira]    Configurar Jira"),
                    Separator(),
                    Choice("back", "[Voltar]  Voltar")
                ]
            ).execute()
            
            if action == "back":
                break
            elif action == "show":
                self._show_config()
            elif action == "jira":
                self._config_jira()
    
    def _show_config(self):
        """Mostra configurações."""
        config = self.config.get_all_settings()
        
        print("\nConfigurações atuais:")
        print("=" * 30)
        
        for key, value in config.items():
            if 'token' in key.lower() or 'password' in key.lower():
                display_value = '*' * len(str(value)) if value else 'Não configurado'
            else:
                display_value = value or 'Não configurado'
            print(f"{key}: {display_value}")
        
        input("\nPressione Enter para continuar...")
    
    def _config_jira(self):
        """Configura Jira."""
        print("\nConfiguração do Jira")
        
        current_url = self.config.get_setting('jira_url', '')
        current_user = self.config.get_setting('jira_user', '')
        
        url = inquirer.text(
            message="URL do servidor Jira:",
            default=current_url,
            validate=lambda x: len(x) > 0,
            invalid_message="URL não pode estar vazia"
        ).execute()
        
        user = inquirer.text(
            message="Usuário do Jira:",
            default=current_user,
            validate=lambda x: len(x) > 0,
            invalid_message="Usuário não pode estar vazio"
        ).execute()
        
        token = inquirer.secret(
            message="Token de API do Jira:",
            validate=lambda x: len(x) > 0,
            invalid_message="Token não pode estar vazio"
        ).execute()
        
        # Salva configurações
        self.config.set_setting('jira_url', url)
        self.config.set_setting('jira_user', user)
        self.config.set_setting('jira_token', token)
        
        print("Configurações do Jira salvas!")
        
        # Testa conexão
        if inquirer.confirm("Testar conexão com o Jira?", default=True).execute():
            self._test_jira_connection()
        
        input("Pressione Enter para continuar...")
    
    def _test_jira_connection(self):
        """Testa conexão com Jira."""
        print("\nTestando conexão com Jira...")
        
        try:
            url = self.config.get_setting('jira_url')
            user = self.config.get_setting('jira_user')
            token = self.config.get_setting('jira_token')
            
            jira = JiraClient(url, user, token)
            if jira.connect():
                print("Conexão com Jira estabelecida com sucesso!")
                self.jira_client = jira
            else:
                print("Falha na conexão com Jira")
        except Exception as e:
            print(f"Erro ao testar conexão: {e}")
    
    def _manage_monitoring(self):
        """Gerencia monitoramento."""
        is_running = self.monitor.is_running
        
        if is_running:
            action = inquirer.select(
                message="Monitoramento está rodando:",
                choices=[
                    Choice("stop",   "[Stop]    Parar monitoramento"),
                    Choice("status", "[Status]  Ver status"),
                    Separator(),
                    Choice("back",   "[Voltar]  Voltar")
                ]
            ).execute()
            
            if action == "stop":
                print("Parando monitoramento...")
                self.monitor.stop_monitoring()
                print("Monitoramento parado!")
                input("Pressione Enter para continuar...")
        else:
            action = inquirer.select(
                message="Monitoramento está parado:",
                choices=[
                    Choice("start",          "[Start]     Iniciar monitoramento"),
                    Choice("start_specific", "[Caminhos]  Monitorar caminhos específicos"),
                    Separator(),
                    Choice("back",           "[Voltar]    Voltar")
                ]
            ).execute()
            
            if action == "start":
                print("Iniciando monitoramento...")
                self.monitor.start_monitoring()
                print("Monitoramento iniciado!")
                input("Pressione Enter para continuar...")
            elif action == "start_specific":
                # TODO: Implementar seleção de caminhos específicos
                print("Funcionalidade em desenvolvimento...")
                input("Pressione Enter para continuar...")
    
    def _manage_jira(self):
        """Gerencia integração Jira."""
        while True:
            # Verifica se Jira está configurado
            is_configured = self.config.is_jira_configured()
            is_connected = self.jira_client and self.jira_client.is_connected()

            status_text = "[Conectado]" if is_connected else ("[Configurado]" if is_configured else "[Nao configurado]")

            action = inquirer.select(
                message=f"Integração Jira {status_text}:",
                choices=[
                    Choice("test",       "[Test]      Testar conexão"),
                    Choice("projects",   "[Projetos]  Ver projetos disponíveis"),
                    Choice("status",     "[Status]    Descobrir status de projeto"),
                    Choice("workflow",   "[Workflow]  Analisar workflow de issue"),
                    Choice("automation", "[Auto]      Configurar automação de status"),
                    Separator(),
                    Choice("issues",     "[Issues]    Buscar minhas issues"),
                    Choice("worklog",    "[Worklog]   Criar worklog de teste"),
                    Choice("config",     "[Config]    Configurar credenciais"),
                    Separator(),
                    Choice("back",       "[Voltar]    Voltar")
                ]
            ).execute()

            if action == "back":
                break
            elif action == "test":
                self._test_jira_connection()
            elif action == "projects":
                self._show_jira_projects()
            elif action == "status":
                self._discover_project_statuses()
            elif action == "workflow":
                self._analyze_issue_workflow()
            elif action == "automation":
                self._configure_status_automation()
            elif action == "issues":
                self._show_my_jira_issues()
            elif action == "worklog":
                self._create_test_worklog()
            elif action == "config":
                self._config_jira()

    def _show_my_jira_issues(self):
        """Mostra issues do usuário no Jira."""
        if not self.jira_client or not self.jira_client.is_connected():
            print("\nJira não está conectado")
            input("Pressione Enter para continuar...")
            return

        print("\nBuscando suas issues no Jira...")
        issues = self.jira_client.get_my_issues()

        if not issues:
            print("Nenhuma issue encontrada")
        else:
            print(f"\nEncontradas {len(issues)} issues:")
            print("=" * 50)
            for issue in issues[:10]:  # Mostra apenas as 10 primeiras
                print(f"Ticket: {issue['key']} - {issue['summary']}")
                print(f"   Status: {issue['status']}")
                print()

        input("Pressione Enter para continuar...")

    def _create_test_worklog(self):
        """Cria um worklog de teste."""
        if not self.jira_client or not self.jira_client.is_connected():
            print("\nJira não está conectado")
            input("Pressione Enter para continuar...")
            return

        issue_key = inquirer.text(
            message="Digite a issue para criar worklog de teste:",
            validate=lambda x: len(x) > 0,
            invalid_message="Issue não pode estar vazia"
        ).execute()

        time_spent = inquirer.text(
            message="Tempo gasto (ex: 1h 30m):",
            default="30m",
            validate=lambda x: len(x) > 0,
            invalid_message="Tempo não pode estar vazio"
        ).execute()

        description = inquirer.text(
            message="Descrição do trabalho:",
            default="Teste de integração Dev Peace",
            validate=lambda x: len(x) > 0,
            invalid_message="Descrição não pode estar vazia"
        ).execute()

        print(f"\nCriando worklog na issue {issue_key}...")
        worklog_id = self.jira_client.add_worklog(issue_key, time_spent, description)

        if worklog_id:
            print(f"Worklog criado com sucesso! ID: {worklog_id}")
        else:
            print("Erro ao criar worklog")

        input("Pressione Enter para continuar...")

    def _show_jira_projects(self):
        """Mostra projetos disponíveis no Jira."""
        if not self.jira_client or not self.jira_client.is_connected():
            print("\nJira não está conectado")
            input("Pressione Enter para continuar...")
            return

        print("\nBuscando projetos do Jira...")
        projects = self.jira_client.get_projects()

        if not projects:
            print("Nenhum projeto encontrado")
            input("Pressione Enter para continuar...")
            return

        print(f"\nEncontrados {len(projects)} projetos:")
        print("=" * 50)

        for project in projects:
            print(f"Key: {project['key']} - {project['name']}")
            if project['description']:
                print(f"   Desc: {project['description']}")
            if project['lead']:
                print(f"   Lead: {project['lead']}")
            print()

        print("Dica: Use 'Descobrir status de projeto' para ver os status disponíveis")
        input("Pressione Enter para continuar...")

    def _discover_project_statuses(self):
        """Descobre status de um projeto."""
        if not self.jira_client or not self.jira_client.is_connected():
            print("\nJira não está conectado")
            input("Pressione Enter para continuar...")
            return

        # Primeiro, mostra projetos disponíveis
        projects = self.jira_client.get_projects()
        if not projects:
            print("\nNenhum projeto encontrado")
            input("Pressione Enter para continuar...")
            return

        # Permite selecionar um projeto
        project_choices = [Choice(p['key'], f"{p['key']} - {p['name']}") for p in projects]
        project_choices.append(Choice("manual", "[Manual] Digitar chave manualmente"))

        selected_project = inquirer.select(
            message="Selecione o projeto:",
            choices=project_choices
        ).execute()

        if selected_project == "manual":
            project_key = inquirer.text(
                message="Digite a chave do projeto (ex: PROJ):",
                validate=lambda x: len(x) > 0,
                invalid_message="Chave do projeto não pode estar vazia"
            ).execute()
        else:
            project_key = selected_project

        print(f"\nBuscando status do projeto {project_key}...")
        statuses = self.jira_client.get_project_statuses(project_key)

        if not statuses:
            print(f"Nenhum status encontrado para o projeto {project_key}")
            input("Pressione Enter para continuar...")
            return

        print(f"\nStatus disponíveis no projeto {project_key}:")
        print("=" * 40)

        for status in statuses:
            print(f"Status: {status['name']}")

        # Pergunta se quer configurar automação baseada nestes status
        if inquirer.confirm(
            f"Deseja configurar automação baseada nos status do projeto {project_key}?",
            default=True
        ).execute():
            self._apply_project_automation(project_key, [s['name'] for s in statuses])

        input("\nPressione Enter para continuar...")

    def _analyze_issue_workflow(self):
        """Analisa workflow de uma issue específica."""
        if not self.jira_client or not self.jira_client.is_connected():
            print("\nJira não está conectado")
            input("Pressione Enter para continuar...")
            return

        issue_key = inquirer.text(
            message="Digite a chave da issue (ex: PROJ-123):",
            validate=lambda x: len(x) > 0 and '-' in x,
            invalid_message="Digite uma chave válida (ex: PROJ-123)"
        ).execute()

        print(f"\nAnalisando workflow da issue {issue_key}...")
        workflow_info = self.jira_client.get_issue_workflow_statuses(issue_key)

        if not workflow_info:
            print(f"Não foi possível obter informações da issue {issue_key}")
            input("Pressione Enter para continuar...")
            return

        print(f"\nIssue: {issue_key}")
        print("=" * 30)
        print(f"Status atual: {workflow_info['current_status']}")
        print(f"Projeto: {workflow_info['project']}")
        print(f"Tipo: {workflow_info['issue_type']}")

        print("\nTransições disponíveis:")
        for transition in workflow_info['available_transitions']:
            print(f"  * {transition['name']} -> {transition['to_status']}")
            if transition['description']:
                print(f"    Desc: {transition['description']}")

        # Pergunta se quer configurar automação baseada nesta issue
        if inquirer.confirm(
            f"Deseja configurar automação baseada no workflow desta issue?",
            default=True
        ).execute():
            self._apply_project_automation(workflow_info['project'], workflow_info['all_possible_statuses'])

        input("\nPressione Enter para continuar...")

    def _configure_status_automation(self):
        """Configura automação de status."""
        from ..core.status_manager import StatusManager

        status_manager = StatusManager(self.config, self.jira_client)

        while True:
            action = inquirer.select(
                message="Configurar automação de status:",
                choices=[
                    Choice("show",      "[Ver]     Ver regras atuais"),
                    Choice("enable",    "[ON]      Habilitar automação"),
                    Choice("disable",   "[OFF]     Desabilitar automação"),
                    Choice("configure", "[Config]  Configurar baseado no Jira"),
                    Choice("rules",     "[Regras]  Gerenciar regras individuais"),
                    Choice("reset",     "[Reset]   Resetar para padrões"),
                    Separator(),
                    Choice("back",      "[Voltar]  Voltar")
                ]
            ).execute()

            if action == "back":
                break
            elif action == "show":
                self._show_automation_rules(status_manager)
            elif action == "enable":
                self._enable_automation(status_manager)
            elif action == "disable":
                self._disable_automation(status_manager)
            elif action == "configure":
                self._configure_automation_from_jira(status_manager)
            elif action == "rules":
                self._manage_individual_rules(status_manager)
            elif action == "reset":
                self._reset_automation_rules(status_manager)

    def _show_automation_rules(self, status_manager):
        """Mostra regras de automação atuais."""
        rules = status_manager.status_rules

        print("\nRegras de Automação de Status")
        print("=" * 40)
        print(f"Status geral: {'[Habilitado]' if rules.get('enabled') else '[Desabilitado]'}")
        
        # Mostra configuração de reversão automática
        auto_revert = rules.get('auto_revert_on_session_end', False)
        print(f"Reversão automática: {'[Habilitada]' if auto_revert else '[Desabilitada]'}")
        print()

        events = rules.get('events', {})
        for event_name, transitions in events.items():
            title = event_name.replace('on_', '').replace('_', ' ').title()
            print(f"Evento {title}:")
            if not transitions:
                print("   (Nenhuma regra configurada)")
            else:
                for i, trans in enumerate(transitions, 1):
                    from_val = trans.get('from')
                    to_val = trans.get('to')
                    print(f"   {i}. {from_val} -> {to_val}")
            print()

        input("Pressione Enter para continuar...")

    def _enable_automation(self, status_manager):
        """Habilita automação de status."""
        rules = status_manager.status_rules.copy()
        rules['enabled'] = True
        status_manager.save_status_rules(rules)
        print("\nAutomação de status habilitada!")
        input("Pressione Enter para continuar...")

    def _disable_automation(self, status_manager):
        """Desabilita automação de status."""
        rules = status_manager.status_rules.copy()
        rules['enabled'] = False
        status_manager.save_status_rules(rules)
        print("\nAutomação de status desabilitada!")
        input("Pressione Enter para continuar...")

    def _configure_automation_from_jira(self, status_manager):
        """Configura automação baseada no Jira."""
        if not self.jira_client or not self.jira_client.is_connected():
            print("\nJira não está conectado")
            input("Pressione Enter para continuar...")
            return

        # Escolhe método de configuração
        method = inquirer.select(
            message="Como deseja descobrir os status?",
            choices=[
                Choice("project", "[Projeto] Por projeto"),
                Choice("issue", "[Issue] Por issue específica"),
                Choice("back", "[Voltar] Voltar")
            ]
        ).execute()

        if method == "back":
            return
        elif method == "project":
            self._configure_by_project(status_manager)
        elif method == "issue":
            self._configure_by_issue(status_manager)

    def _configure_by_project(self, status_manager):
        """Configura automação por projeto."""
        projects = self.jira_client.get_projects()
        if not projects:
            print("\nNenhum projeto encontrado")
            input("Pressione Enter para continuar...")
            return

        # Seleciona projeto
        project_choices = [Choice(p['key'], f"{p['key']} - {p['name']}") for p in projects]
        project_choices.append(Choice("manual", "[Manual] Digitar chave manualmente"))

        selected_project = inquirer.select(
            message="Selecione o projeto:",
            choices=project_choices
        ).execute()

        if selected_project == "manual":
            project_key = inquirer.text(
                message="Digite a chave do projeto:",
                validate=lambda x: len(x) > 0,
                invalid_message="Chave não pode estar vazia"
            ).execute()
        else:
            project_key = selected_project

        # Busca status do projeto
        print(f"\nDescobrindo status do projeto {project_key}...")
        statuses = self.jira_client.get_project_statuses(project_key)

        if not statuses:
            print(f"Nenhum status encontrado for {project_key}")
            input("Pressione Enter para continuar...")
            return

        status_names = [s['name'] for s in statuses]
        self._apply_project_automation(project_key, status_names)

    def _configure_by_issue(self, status_manager):
        """Configura automação por issue."""
        issue_key = inquirer.text(
            message="Digite a chave da issue (ex: PROJ-123):",
            validate=lambda x: len(x) > 0 and '-' in x,
            invalid_message="Digite uma chave válida"
        ).execute()

        print(f"\nAnalisando issue {issue_key}...")
        workflow_info = self.jira_client.get_issue_workflow_statuses(issue_key)

        if not workflow_info:
            print(f"Não foi possível analisar a issue {issue_key}")
            input("Pressione Enter para continuar...")
            return

        self._apply_project_automation(workflow_info['project'], workflow_info['all_possible_statuses'])

    def _apply_project_automation(self, project_key, available_statuses):
        """Aplica configuração de automação baseada nos status disponíveis."""
        from ..core.status_manager import StatusManager

        status_manager = StatusManager(self.config, self.jira_client)

        print(f"\nConfigurando automação para projeto {project_key}...")
        print("Status disponíveis:")
        for status in available_statuses:
            print(f"  Status: {status}")

        # Mapeia status automaticamente
        status_mapping = {
            'todo': [
                'To Do', 'TODO', 'Backlog', 'New', 'Open', 'Created',
                'A FAZER', 'FILA', 'Na fila', 'Fila de', 'DEMANDAS'
            ],
            'in_progress': [
                'In Progress', 'IN PROGRESS', 'Em Progresso', 'Doing', 'Development',
                'FAZENDO', 'Trabalhando', 'Implementando', 'CRIANDO', 'EDITANDO',
                'Editando', 'Criando', 'GRAVANDO', 'Gravando', 'Analisando', 'ANALISANDO'
            ],
            'done': [
                'Done', 'DONE', 'Closed', 'Resolved', 'Finalizado', 'Complete',
                'FEITO', 'FINALIZADO', 'Concluído', 'Resolvido', 'Implementado'
            ]
        }

        found_statuses = {}
        for category, possible_names in status_mapping.items():
            for status in available_statuses:
                if any(possible.lower() in status.lower() or status.lower() in possible.lower()
                       for possible in possible_names):
                    found_statuses[category] = status
                    break

        if found_statuses:
            print("\nMapeamento automático encontrado:")
            for category, status in found_statuses.items():
                print(f"  {category}: {status}")

            # Oferece opções de configuração
            config_action = inquirer.select(
                message="Como deseja proceder?",
                choices=[
                    Choice("auto", "[Auto] Aplicar configuração automática"),
                    Choice("edit", "[Edit] Editar configuração antes de aplicar"),
                    Choice("manual", "[Manual] Configurar tudo manualmente"),
                    Choice("cancel", "[Cancel] Cancelar")
                ]
            ).execute()

            if config_action == "auto":
                self._apply_automatic_config(status_manager, found_statuses)
            elif config_action == "edit":
                self._edit_and_apply_config(status_manager, found_statuses, available_statuses)
            elif config_action == "manual":
                self._manual_config_from_statuses(status_manager, available_statuses)
            else:
                print("Configuração cancelada")
        else:
            print("\nNão foi possível mapear automaticamente")
            if inquirer.confirm("Deseja configurar manualmente?", default=True).execute():
                self._manual_config_from_statuses(status_manager, available_statuses)
            else:
                print("Configure manualmente usando 'Gerenciar regras individuais'")

        input("\nPressione Enter para continuar...")

    def _apply_automatic_config(self, status_manager, found_statuses):
        """Aplica configuração automática."""
        rules = status_manager.status_rules.copy()
        if 'events' not in rules:
            rules['events'] = {'on_work_start': [], 'on_first_commit': [], 'on_work_complete': []}

        if 'todo' in found_statuses and 'in_progress' in found_statuses:
            rules['events']['on_work_start'] = [
                {'from': found_statuses['todo'], 'to': found_statuses['in_progress']}
            ]
            print(f"Configurado início: {found_statuses['todo']} -> {found_statuses['in_progress']}")

        if 'in_progress' in found_statuses and 'done' in found_statuses:
            rules['events']['on_work_complete'] = [
                {'from': found_statuses['in_progress'], 'to': found_statuses['done']}
            ]
            print(f"Configurado fim: {found_statuses['in_progress']} -> {found_statuses['done']}")

        # Habilita automação
        rules['enabled'] = True
        status_manager.save_status_rules(rules)
        print("Configuração salva e automação habilitada!")

    def _edit_and_apply_config(self, status_manager, found_statuses, available_statuses):
        """Permite editar a configuração antes de aplicar."""
        print("\nEditando configuração...")

        # Cria mapeamento editável
        config_mapping = {}

        # Configura regra de início de trabalho
        print("\nConfigurando regra: Início de Trabalho")
        print("Quando você entra em um repositório, de qual status para qual status a issue deve ir?")

        from_status_start = self._select_status_from_list(
            available_statuses,
            "Selecione o status DE ORIGEM (ex: A Fazer, Fila, etc.):",
            found_statuses.get('todo')
        )

        to_status_start = self._select_status_from_list(
            available_statuses,
            "Selecione o status DE DESTINO (ex: Em Progresso, Fazendo, etc.):",
            found_statuses.get('in_progress')
        )

        if from_status_start and to_status_start:
            config_mapping['on_work_start'] = {
                'from': from_status_start,
                'to': to_status_start,
                'enabled': True
            }

        # Configura regra de primeiro commit (opcional)
        if inquirer.confirm("Deseja configurar mudança de status no primeiro commit?", default=False).execute():
            print("\nConfigurando regra: Primeiro Commit")

            from_status_commit = self._select_status_from_list(
                available_statuses,
                "Status de origem para primeiro commit:",
                found_statuses.get('todo')
            )

            to_status_commit = self._select_status_from_list(
                available_statuses,
                "Status de destino para primeiro commit:",
                found_statuses.get('in_progress')
            )

            if from_status_commit and to_status_commit:
                config_mapping['on_first_commit'] = {
                    'from': from_status_commit,
                    'to': to_status_commit,
                    'enabled': True
                }

        # Configura regra de finalização (opcional)
        if inquirer.confirm("Deseja configurar mudança de status ao finalizar trabalho?", default=False).execute():
            print("\nConfigurando regra: Finalização de Trabalho")

            from_status_complete = self._select_status_from_list(
                available_statuses,
                "Status de origem para finalização:",
                found_statuses.get('in_progress')
            )

            to_status_complete = self._select_status_from_list(
                available_statuses,
                "Status de destino para finalização:",
                found_statuses.get('done')
            )

            if from_status_complete and to_status_complete:
                config_mapping['on_work_complete'] = {
                    'from': from_status_complete,
                    'to': to_status_complete,
                    'enabled': True
                }

        # Aplica a configuração
        if config_mapping:
            self._apply_custom_config(status_manager, config_mapping)
        else:
            print("Nenhuma configuração foi definida")

    def _select_status_from_list(self, available_statuses, message, default_status=None):
        """Permite selecionar um status de uma lista com busca fuzzy."""
        if not available_statuses:
            return inquirer.text(message=message, default=default_status or "").execute()

        choices = [Choice(status, status) for status in available_statuses]
        choices.append(Separator())
        choices.append(Choice(None, "[X] Não configurar / Cancelar"))

        # Define o padrão se fornecido
        default_choice = default_status if default_status in available_statuses else None

        selected = inquirer.select(
            message=message,
            choices=choices,
            default=default_choice,
            filter=lambda val: val
        ).execute()

        return selected

    def _apply_custom_config(self, status_manager, config_mapping):
        """Aplica configuração customizada."""
        rules = status_manager.status_rules.copy()
        if 'events' not in rules:
            rules['events'] = {'on_work_start': [], 'on_first_commit': [], 'on_work_complete': []}

        for event_name, config in config_mapping.items():
            if event_name in rules['events']:
                rules['events'][event_name] = [
                    {'from': config['from'], 'to': config['to']}
                ]
                print(f"Configurado {event_name}: {config['from']} -> {config['to']}")

        # Habilita automação geral
        rules['enabled'] = True
        status_manager.save_status_rules(rules)
        print("Configuração customizada salva e automação habilitada!")

    def _manual_config_from_statuses(self, status_manager, available_statuses):
        """Configuração completamente manual."""
        print("\nConfiguração Manual Completa")
        print("Vamos configurar as transições para cada evento...")

        while True:
            event_name = inquirer.select(
                message="Selecione um evento para adicionar regras:",
                choices=[
                    Choice("on_work_start",    "[Start]     Início de Trabalho"),
                    Choice("on_first_commit",  "[Commit]    Primeiro Commit"),
                    Choice("on_work_complete", "[Complete]  Finalização de Trabalho"),
                    Separator(),
                    Choice("done",             "[OK]        Finalizar configuração")
                ]
            ).execute()

            if event_name == "done":
                break

            self._add_transition_to_event(status_manager, event_name)

        # Pergunta se quer habilitar automação
        if inquirer.confirm("Habilitar automação com essas configurações?", default=True).execute():
            rules = status_manager.status_rules.copy()
            rules['enabled'] = True
            status_manager.save_status_rules(rules)
            print("Automação habilitada!")

    def _manage_individual_rules(self, status_manager):
        """Gerencia regras individuais."""
        rules = status_manager.status_rules.copy()
        events = rules.get('events', {})

        event_choices = [
            Choice("on_work_start",    "[Start]     Início de Trabalho"),
            Choice("on_first_commit",  "[Commit]    Primeiro Commit"),
            Choice("on_work_complete", "[Complete]  Finalização de Trabalho"),
            Separator(),
            Choice("back",             "[Voltar]    Voltar")
        ]

        selected_event = inquirer.select(
            message="Selecione o evento para gerenciar regras:",
            choices=event_choices
        ).execute()

        if selected_event == "back":
            return

        self._manage_event_transitions(status_manager, selected_event)

    def _manage_event_transitions(self, status_manager, event_name):
        """Gerencia transições de um evento específico."""
        while True:
            rules = status_manager.status_rules.copy()
            transitions = rules.get('events', {}).get(event_name, [])
            
            title = event_name.replace('on_', '').replace('_', ' ').title()
            print(f"\nGerenciando: {title}")
            
            choices = []
            if transitions:
                for i, trans in enumerate(transitions):
                    choices.append(Choice(i, f"[Remover]  {trans['from']} -> {trans['to']}"))
                choices.append(Separator())
            
            choices.append(Choice("add",  "[Add]      Adicionar nova transição"))
            choices.append(Choice("back", "[Voltar]   Voltar"))

            action = inquirer.select(
                message="Selecione uma ação:",
                choices=choices
            ).execute()

            if action == "back":
                break
            elif action == "add":
                self._add_transition_to_event(status_manager, event_name)
            else:
                # Remover transição
                idx = int(action)
                removed = transitions.pop(idx)
                status_manager.save_status_rules(rules)
                print(f"Transição removida: {removed['from']} -> {removed['to']}")

    def _add_transition_to_event(self, status_manager, event_name):
        """Adiciona uma nova transição a um evento com filtragem por projeto."""
        rules = status_manager.status_rules.copy()
        
        # Garante que o cliente Jira está conectado
        if not self.jira_client or not self.jira_client.is_connected():
            if self.config.is_jira_configured():
                jira_config = self.config.get_jira_config()
                temp_jira = JiraClient(jira_config['url'], jira_config['user'], jira_config['token'])
                if temp_jira.connect():
                    self.jira_client = temp_jira

        if not self.jira_client or not self.jira_client.is_connected():
            print("\nJira não está conectado. Configure as credenciais primeiro.")
            input("Pressione Enter para continuar...")
            return

        # 1. Seleção de Projeto para filtrar status
        print("\nBuscando projetos...")
        projects = self.jira_client.get_projects()
        
        project_choices = [Choice("all", "[Global]  Todos os Status (Global)")]
        for p in projects:
            project_choices.append(Choice(p['key'], f"[{p['key']}]  {p['name']}"))
        
        selected_project = inquirer.select(
            message="Filtrar status de qual projeto?",
            choices=project_choices,
            default="all"
        ).execute()

        # 2. Busca de Status baseada no projeto
        if selected_project == "all":
            print("Buscando todos os status globais...")
            available_statuses = self.jira_client.get_all_statuses()
        else:
            print(f"Buscando status do projeto {selected_project}...")
            available_statuses = self.jira_client.get_project_statuses(selected_project)

        if not available_statuses:
            print("Aviso: Nenhum status encontrado.")
            if not inquirer.confirm("Deseja digitar manualmente?", default=True).execute():
                return

        def get_status_choice(message):
            if available_statuses:
                choice = inquirer.select(
                    message=message,
                    choices=[Choice(s, s) for s in available_statuses] + [Choice("custom", "[Manual]  Digitar manualmente...")]
                ).execute()
                
                if choice == "custom":
                    return inquirer.text(message=f"Digite o {message.lower()}").execute()
                return choice
            else:
                return inquirer.text(message=message).execute()

        # 3. Seleção de Origem e Destino
        from_status = get_status_choice("Status de ORIGEM:")
        if not from_status: return

        to_status = get_status_choice("Status de DESTINO:")
        if not to_status: return

        if from_status and to_status:
            if 'events' not in rules:
                rules['events'] = {'on_work_start': [], 'on_first_commit': [], 'on_work_complete': []}
            
            if event_name not in rules['events']:
                rules['events'][event_name] = []
            
            rules['events'][event_name].append({
                'from': from_status,
                'to': to_status
            })
            
            status_manager.save_status_rules(rules)
            print(f"Nova regra adicionada: {from_status} -> {to_status}")

    def _reset_automation_rules(self, status_manager):
        """Reseta regras para os padrões."""
        if inquirer.confirm("Aviso: Tem certeza que deseja resetar todas as regras?", default=False).execute():
            status_manager.reset_to_defaults()
            print("Regras resetadas para os padrões!")
        else:
            print("Reset cancelado")

        input("Pressione Enter para continuar...")
