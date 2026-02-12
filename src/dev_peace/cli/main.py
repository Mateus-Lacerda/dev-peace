"""
Interface de linha de comando principal do Dev Peace.
"""

import argparse
import sys
import logging
from pathlib import Path
from typing import Optional

from ..core.activity_monitor import DevPeaceActivityMonitor
from ..database.models import DatabaseManager
from ..config.settings import ConfigManager
from .interactive import InteractiveInterface

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)


class DevPeaceCLI:
    """Interface de linha de comando do Dev Peace."""
    
    def __init__(self):
        self.db = DatabaseManager()
        self.monitor = DevPeaceActivityMonitor(self.db)
        self.config = ConfigManager()
        self.interactive = InteractiveInterface(self.db, self.monitor, self.config)
    
    def create_parser(self) -> argparse.ArgumentParser:
        """Cria o parser de argumentos."""
        parser = argparse.ArgumentParser(
            prog='dev-peace',
            description=r'''
  _____                             _.-.                   _____                    
 |  __ \                        .-.  `) |  .-.            |  __ \                   
 | |  | | _____   __        _.'`. .~./  \.~. .`'._        | |__) |__  __ _  ___ ___ 
 | |  | |/ _ \ \ / /    .-'`.'-'.'.-:    ;-.'.'-'.`'-.    |  ___/ _ \/ _` |/ __/ _ \
 | |__| |  __/\ V /      `'`'`'`'`   \  /   `'`'`'`'`     | |  |  __/ (_| | (_|  __/
 |_____/ \___| \_/                   /||\                 |_|   \___|\__,_|\___\___|
                          jgs       / ^^ \                                       
                                    `'``'`

Dev Peace - O observador zen que transforma seu caos de desenvolvimento em worklogs organizados!
    
    Cansado de esquecer de registrar suas horas no Jira? 
    Farto de tentar lembrar o que você fez ontem?
    Dev Peace está aqui para trazer paz à sua vida de dev! 
    
    Ele observa silenciosamente seus repositórios, detecta quando você entra neles,
    monitora suas modificações, registra seus commits e ainda por cima conversa
    com o Jira para você. É quase como ter um assistente pessoal, mas sem o salário!
            ''',
            epilog='''
Exemplos de uso:
    dev-peace start                    # Inicia o monitoramento (modo zen ativado)
    dev-peace add /path/to/repo        # Adiciona um repo para observação
    dev-peace status                   # Vê o que está rolando
    dev-peace interactive              # Interface para os preguiçosos
    dev-peace docs                     # Abre a documentação no navegador
    dev-peace orphans                  # Vê os registros perdidos na vida
    
Que a paz esteja com seu código!
            ''',
            formatter_class=argparse.RawDescriptionHelpFormatter
        )
        
        subparsers = parser.add_subparsers(dest='command', help='Comandos disponíveis')
        
        # Comando start
        start_parser = subparsers.add_parser(
            'start', 
            help='Inicia o monitoramento (finalmente, produtividade!)'
        )
        start_parser.add_argument(
            '--paths', 
            nargs='+', 
            help='Caminhos específicos para monitorar (senão monitora tudo)'
        )
        start_parser.add_argument(
            '--daemon', 
            action='store_true', 
            help='Roda em background como um ninja silencioso'
        )
        
        # Comando stop
        subparsers.add_parser(
            'stop', 
            help='Para o monitoramento (hora do café!)'
        )
        
        # Comando add
        add_parser = subparsers.add_parser(
            'add', 
            help='Adiciona um repositório para monitoramento'
        )
        add_parser.add_argument(
            'path', 
            help='Caminho do repositório Git (tem que ser Git, né!)'
        )
        
        # Comando status
        subparsers.add_parser(
            'status', 
            help='Mostra o status atual (spoiler: provavelmente está tudo bem)'
        )
        
        # Comando list
        list_parser = subparsers.add_parser(
            'list', 
            help='Lista repositórios monitorados'
        )
        list_parser.add_argument(
            '--active-only', 
            action='store_true', 
            help='Só os repositórios ativos (os que prestam)'
        )
        
        # Comando orphans
        subparsers.add_parser(
            'orphans', 
            help='Mostra registros órfãos (coitadinhos sem issue pai)'
        )
        
        # Comando config
        config_parser = subparsers.add_parser(
            'config', 
            help='Configurações do Jira e outras coisas importantes'
        )
        config_parser.add_argument(
            '--jira-url', 
            help='URL do servidor Jira'
        )
        config_parser.add_argument(
            '--jira-user', 
            help='Usuário do Jira'
        )
        config_parser.add_argument(
            '--jira-token', 
            help='Token de API do Jira (guarde com carinho)'
        )
        config_parser.add_argument(
            '--show',
            action='store_true',
            help='Mostra configurações atuais'
        )
        config_parser.add_argument(
            '--test-jira',
            action='store_true',
            help='Testa conexão com Jira'
        )
        
        # Comando interactive
        subparsers.add_parser(
            'interactive',
            help='Interface interativa bonita (para os que gostam de cores)'
        )

        # Comando docs
        subparsers.add_parser(
            'docs',
            help='Abre a documentação no navegador'
        )
        
        # Comando stats
        subparsers.add_parser(
            'stats',
            help='Estatísticas detalhadas (para os nerds)'
        )

        # Comando daemon
        daemon_parser = subparsers.add_parser(
            'daemon',
            help='Executa como daemon (serviço em background)'
        )
        daemon_parser.add_argument(
            '--log-level',
            choices=['debug', 'info', 'warning', 'error'],
            default='info',
            help='Nível de log para o daemon'
        )

        # Comando status-issue
        status_parser = subparsers.add_parser(
            'status-issue',
            help='Gerencia status de issues no Jira'
        )
        status_parser.add_argument(
            'issue_key',
            help='Chave da issue (ex: PROJ-123)'
        )
        status_parser.add_argument(
            'new_status',
            help='Novo status da issue'
        )
        status_parser.add_argument(
            '--comment',
            help='Comentário opcional para a transição'
        )

        # Comando automation
        automation_parser = subparsers.add_parser(
            'automation',
            help='Gerencia automação de status de issues'
        )
        automation_subparsers = automation_parser.add_subparsers(dest='automation_action', help='Ações de automação')

        # Subcomando show
        automation_subparsers.add_parser(
            'show',
            help='Mostra regras de automação atuais'
        )

        # Subcomando enable
        enable_parser = automation_subparsers.add_parser(
            'enable',
            help='Habilita automação de status'
        )
        enable_parser.add_argument(
            'rule_name',
            nargs='?',
            choices=['on_work_start', 'on_first_commit', 'on_work_complete'],
            help='Nome da regra específica para habilitar'
        )

        # Subcomando disable
        disable_parser = automation_subparsers.add_parser(
            'disable',
            help='Desabilita automação de status'
        )
        disable_parser.add_argument(
            'rule_name',
            nargs='?',
            choices=['on_work_start', 'on_first_commit', 'on_work_complete'],
            help='Nome da regra específica para desabilitar'
        )

        # Subcomando reset
        automation_subparsers.add_parser(
            'reset',
            help='Reseta regras para os padrões'
        )

        # Subcomando auto-revert
        revert_parser = automation_subparsers.add_parser(
            'auto-revert',
            help='Configura reversão automática de status'
        )
        revert_parser.add_argument(
            'action',
            choices=['enable', 'disable', 'status'],
            help='Ação: enable (habilitar), disable (desabilitar), status (mostrar status)'
        )

        # Subcomando configure
        configure_parser = automation_subparsers.add_parser(
            'configure',
            help='Configura regras baseadas no seu Jira'
        )
        configure_parser.add_argument(
            '--project',
            help='Chave do projeto para descobrir status (ex: PROJ)'
        )
        configure_parser.add_argument(
            '--issue',
            help='Issue exemplo para descobrir workflow (ex: PROJ-123)'
        )
        configure_parser.add_argument(
            '--apply',
            action='store_true',
            help='Aplica automaticamente a configuração sugerida'
        )

        # Comando jira-status
        jira_status_parser = subparsers.add_parser(
            'jira-status',
            help='Descobre status e workflows do Jira'
        )
        jira_status_subparsers = jira_status_parser.add_subparsers(dest='jira_status_action', help='Ações de status')

        # Subcomando projects
        jira_status_subparsers.add_parser(
            'projects',
            help='Lista projetos acessíveis'
        )

        # Subcomando list
        list_status_parser = jira_status_subparsers.add_parser(
            'list',
            help='Lista status de um projeto'
        )
        list_status_parser.add_argument(
            'project_key',
            help='Chave do projeto (ex: PROJ)'
        )

        # Subcomando workflow
        workflow_parser = jira_status_subparsers.add_parser(
            'workflow',
            help='Mostra workflow de uma issue'
        )
        workflow_parser.add_argument(
            'issue_key',
            help='Chave da issue (ex: PROJ-123)'
        )
        
        return parser
    
    def handle_start(self, args):
        """Inicia o monitoramento."""
        print("Iniciando Dev Peace...")
        
        try:
            self.monitor.start_monitoring(args.paths)
            
            if args.daemon:
                print("Modo daemon ativado - Dev Peace está observando silenciosamente...")
                # TODO: Implementar modo daemon
            else:
                print("Dev Peace está observando seus repositórios...")
                print("Pressione Ctrl+C para parar")
                
                try:
                    while self.monitor.is_running:
                        import time
                        time.sleep(1)
                except KeyboardInterrupt:
                    print("\nParando Dev Peace...")
                    self.monitor.stop_monitoring()
                    print("Dev Peace parado com sucesso!")
                    
        except Exception as e:
            print(f"Erro ao iniciar monitoramento: {e}")
            return 1
        
        return 0
    
    def handle_stop(self, args):
        """Para o monitoramento."""
        print("Parando Dev Peace...")
        self.monitor.stop_monitoring()
        print("Dev Peace parado com sucesso!")
        return 0
    
    def handle_add(self, args):
        """Adiciona repositório."""
        path = Path(args.path).resolve()
        
        if not path.exists():
            print(f"Caminho não existe: {path}")
            return 1
        
        print(f"Adicionando repositório: {path}")
        
        if self.monitor.add_repository(str(path)):
            print("Repositório adicionado com sucesso!")
            return 0
        else:
            print("Erro ao adicionar repositório")
            return 1
    
    def handle_status(self, args):
        """Mostra status atual."""
        stats = self.monitor.get_repository_stats()
        
        print("Status do Dev Peace")
        print("=" * 30)
        print(f"Status: {'Rodando' if stats['is_running'] else 'Parado'}")
        print(f"Repositórios: {stats['total_repositories']} total, {stats['active_repositories']} ativos")
        print(f"Sessões ativas: {stats['active_sessions']}")
        print(f"Registros órfãos: {stats['orphan_records']}")
        print(f"Caminhos monitorados: {stats['monitored_paths']}")
        
        # Mostra sessões ativas
        active_sessions = self.monitor.get_active_sessions()
        if active_sessions:
            print("\nSessões ativas:")
            for session in active_sessions:
                print(f"  * {session.branch_name} - {session.jira_issue or 'Sem issue'}")
        
        return 0
    
    def handle_list(self, args):
        """Lista repositórios."""
        repositories = self.db.get_all_repositories()
        
        if args.active_only:
            repositories = [r for r in repositories if r.is_active]
        
        if not repositories:
            print("Nenhum repositório encontrado")
            return 0
        
        print(f"Repositórios {'ativos' if args.active_only else 'monitorados'}:")
        print("=" * 50)
        
        for repo in repositories:
            status = "[Ativo]" if repo.is_active else "[Inativo]"
            print(f"{status} {repo.name}")
            print(f"   Local: {repo.path}")
            if repo.last_activity:
                print(f"   Ultima atividade: {repo.last_activity}")
            print()
        
        return 0
    
    def handle_orphans(self, args):
        """Mostra registros órfãos."""
        orphans = self.db.get_orphan_records()
        
        if not orphans:
            print("Nenhum registro órfão! Tudo organizado!")
            return 0
        
        print("Registros órfãos (sem issue pai):")
        print("=" * 40)
        
        for orphan in orphans:
            print(f"Branch: {orphan.branch_name}")
            print(f"   Tempo: {orphan.total_minutes} minutos")
            print(f"   Atividades: {orphan.activities_count}")
            print(f"   Criado: {orphan.created_at}")
            print()
        
        print("Dica: Use 'dev-peace interactive' para associar issues manualmente")
        return 0
    
    def handle_config(self, args):
        """Gerencia configurações."""
        if args.show:
            config = self.config.get_all_settings()
            print("Configurações atuais:")
            print("=" * 30)
            for key, value in config.items():
                if 'token' in key.lower() or 'password' in key.lower():
                    value = '*' * len(str(value)) if value else 'Não configurado'
                print(f"{key}: {value}")
            return 0
        
        # Atualiza configurações
        if args.jira_url:
            self.config.set_setting('jira_url', args.jira_url)
            print(f"URL do Jira configurada: {args.jira_url}")
        
        if args.jira_user:
            self.config.set_setting('jira_user', args.jira_user)
            print(f"Usuário do Jira configurado: {args.jira_user}")
        
        if args.jira_token:
            self.config.set_setting('jira_token', args.jira_token)
            print("Token do Jira configurado")

        # Testa conexão se solicitado
        if args.test_jira:
            self._test_jira_connection()

        return 0

    def _test_jira_connection(self):
        """Testa conexão com Jira."""
        from ..jira_integration.client import JiraClient

        print("Testando conexão com Jira...")

        jira_config = self.config.get_jira_config()
        if not all(jira_config.values()):
            print("Jira não está configurado completamente")
            print("Use: dev-peace config --jira-url <url> --jira-user <user> --jira-token <token>")
            return

        try:
            jira = JiraClient(jira_config['url'], jira_config['user'], jira_config['token'])
            if jira.connect():
                print("Conexão com Jira estabelecida com sucesso!")

                # Busca algumas issues como teste
                print("Buscando suas issues...")
                issues = jira.get_my_issues()
                if issues:
                    print(f"Encontradas {len(issues)} issues atribuídas a você")
                    for issue in issues[:3]:  # Mostra apenas as 3 primeiras
                        print(f"  * {issue['key']} - {issue['summary']}")
                else:
                    print("Nenhuma issue encontrada")
            else:
                print("Falha na conexão com Jira")
                print("Verifique suas credenciais e URL")
        except Exception as e:
            print(f"Erro ao testar conexão: {e}")
    
    def handle_interactive(self, args):
        """Inicia interface interativa."""
        return self.interactive.run()

    def handle_docs(self, args):
        """Abre a documentação no navegador."""
        import webbrowser
        import os
        from pathlib import Path

        # Encontra o arquivo de documentação
        current_dir = Path(__file__).parent.parent.parent.parent
        docs_path = current_dir / "docs" / "index.html"

        if not docs_path.exists():
            print("Arquivo de documentação não encontrado")
            print(f"Procurado em: {docs_path}")
            return 1

        try:
            # Abre no navegador padrão
            file_url = f"file://{docs_path.absolute()}"
            webbrowser.open(file_url)
            print("Documentação aberta no navegador!")
            print(f"URL: {file_url}")
            return 0
        except Exception as e:
            print(f"Erro ao abrir documentação: {e}")
            print(f"Abra manualmente: {docs_path}")
            return 1
    
    def handle_stats(self, args):
        """Mostra estatísticas detalhadas."""
        # TODO: Implementar estatísticas detalhadas
        print("Estatísticas detalhadas em breve...")
        return 0

    def handle_daemon(self, args):
        """Executa como daemon."""
        import signal
        import sys

        # Configura logging para daemon
        log_level = getattr(logging, args.log_level.upper())
        root_logger = logging.getLogger()
        root_logger.setLevel(log_level)

        # Remove handlers existentes para evitar duplicação
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        # Adiciona handler para systemd journal
        journal_handler = logging.StreamHandler(sys.stdout)
        journal_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        root_logger.addHandler(journal_handler)

        logger.info("Dev Peace daemon iniciado")
        logger.info(f"Nível de log: {args.log_level}")

        # Handler para sinais
        def signal_handler(signum, frame):
            logger.info(f"Recebido sinal {signum}, finalizando daemon...")
            self.monitor.stop_monitoring()
            sys.exit(0)

        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGHUP, signal_handler)

        try:
            # Inicia monitoramento
            self.monitor.start_monitoring()
            logger.info("Monitoramento iniciado em modo daemon")

            # Loop principal do daemon
            while self.monitor.is_running:
                import time
                time.sleep(1)

        except Exception as e:
            logger.error(f"Erro no daemon: {e}")
            return 1

        logger.info("Dev Peace daemon finalizado")
        return 0

    def handle_status_issue(self, args):
        """Gerencia status de issues no Jira."""
        from ..jira_integration.client import JiraClient

        # Verifica configuração do Jira
        jira_config = self.config.get_jira_config()
        if not all(jira_config.values()):
            print("Jira não está configurado")
            print("Use: dev-peace config --jira-url <url> --jira-user <user> --jira-token <token>")
            return 1

        try:
            # Conecta ao Jira
            jira = JiraClient(jira_config['url'], jira_config['user'], jira_config['token'])
            if not jira.connect():
                print("Falha na conexão com Jira")
                return 1

            print(f"Alterando status da issue {args.issue_key} para '{args.new_status}'...")

            # Busca a issue
            issue_info = jira.get_issue(args.issue_key)
            if not issue_info:
                print(f"Issue {args.issue_key} não encontrada")
                return 1

            print(f"Issue encontrada: {issue_info['summary']}")
            print(f"Status atual: {issue_info['status']}")

            # Tenta fazer a transição
            success = jira.transition_issue(args.issue_key, args.new_status)

            if success:
                print(f"Status alterado para '{args.new_status}' com sucesso!")
                if args.comment:
                    print(f"Comentário adicionado: {args.comment}")
            else:
                print(f"Erro ao alterar status para '{args.new_status}'")
                print("Verifique se a transição é válida para esta issue")
                return 1

        except Exception as e:
            print(f"Erro ao gerenciar status da issue: {e}")
            return 1

        return 0

    def handle_automation(self, args):
        """Gerencia automação de status."""
        from ..core.status_manager import StatusManager

        if not args.automation_action:
            print("Ação de automação não especificada")
            print("Use: dev-peace automation --help")
            return 1

        status_manager = StatusManager(self.config)

        if args.automation_action == 'show':
            return self._show_automation_rules(status_manager)
        elif args.automation_action == 'enable':
            return self._enable_automation_rule(status_manager, args.rule_name)
        elif args.automation_action == 'disable':
            return self._disable_automation_rule(status_manager, args.rule_name)
        elif args.automation_action == 'reset':
            return self._reset_automation_rules(status_manager)
        elif args.automation_action == 'configure':
            return self._configure_automation_rules(status_manager, args)
        elif args.automation_action == 'auto-revert':
            return self._handle_auto_revert(status_manager, args)
        else:
            print(f"Ação não reconhecida: {args.automation_action}")
            return 1

    def _show_automation_rules(self, status_manager):
        """Mostra regras de automação atuais."""
        rules = status_manager.status_rules

        print("Regras de Automação de Status")
        print("=" * 40)
        print(f"Status geral: {'[Habilitado]' if rules.get('enabled') else '[Desabilitado]'}")

        # Mostra configuração de reversão automática
        auto_revert = rules.get('auto_revert_on_session_end', False)
        print(f"Reversão automática: {'[Habilitada]' if auto_revert else '[Desabilitada]'}")
        if auto_revert:
            print("   Status será revertido automaticamente quando sessão for finalizada")
        print()

        for rule_name, rule_config in rules.get('rules', {}).items():
            status = "[Ativo]" if rule_config.get('enabled') else "[Inativo]"
            print(f"{status} {rule_name.replace('_', ' ').title()}")
            print(f"   De: {rule_config.get('from_status', [])}")
            print(f"   Para: {rule_config.get('to_status', 'N/A')}")
            print()

        return 0

    def _enable_automation_rule(self, status_manager, rule_name):
        """Habilita regra de automação."""
        rules = status_manager.status_rules.copy()

        if rule_name:
            # Habilita regra específica
            if rule_name in rules.get('rules', {}):
                rules['rules'][rule_name]['enabled'] = True
                status_manager.save_status_rules(rules)
                print(f"Regra '{rule_name}' habilitada")
            else:
                print(f"Regra '{rule_name}' não encontrada")
                return 1
        else:
            # Habilita automação geral
            rules['enabled'] = True
            status_manager.save_status_rules(rules)
            print("Automação de status habilitada")

        return 0

    def _disable_automation_rule(self, status_manager, rule_name):
        """Desabilita regra de automação."""
        rules = status_manager.status_rules.copy()

        if rule_name:
            # Desabilita regra específica
            if rule_name in rules.get('rules', {}):
                rules['rules'][rule_name]['enabled'] = False
                status_manager.save_status_rules(rules)
                print(f"Regra '{rule_name}' desabilitada")
            else:
                print(f"Regra '{rule_name}' não encontrada")
                return 1
        else:
            # Desabilita automação geral
            rules['enabled'] = False
            status_manager.save_status_rules(rules)
            print("Automação de status desabilitada")

        return 0

    def _reset_automation_rules(self, status_manager):
        """Reseta regras para os padrões."""
        status_manager.reset_to_defaults()
        print("Regras de automação resetadas para os padrões")
        return 0

    def _configure_automation_rules(self, status_manager, args):
        """Configura regras baseadas no Jira real."""
        from ..jira_integration.client import JiraClient

        # Verifica configuração do Jira
        jira_config = self.config.get_jira_config()
        if not all(jira_config.values()):
            print("Jira não está configurado")
            return 1

        try:
            # Conecta ao Jira
            jira = JiraClient(jira_config['url'], jira_config['user'], jira_config['token'])
            if not jira.connect():
                print("Falha na conexão com Jira")
                return 1

            print("Descobrindo status do seu Jira...")

            # Se foi fornecida uma issue específica
            if args.issue:
                workflow_info = jira.get_issue_workflow_statuses(args.issue)
                if workflow_info:
                    print(f"\nIssue: {args.issue}")
                    print(f"Status atual: {workflow_info['current_status']}")
                    print(f"Projeto: {workflow_info['project']}")
                    print(f"Tipo: {workflow_info['issue_type']}")
                    print("\nStatus possíveis:")
                    for status in sorted(set(workflow_info['all_possible_statuses'])):
                        print(f"  * {status}")

                    # Sugere configuração baseada nos status encontrados
                    self._suggest_automation_config(status_manager, workflow_info['all_possible_statuses'], args.apply)
                else:
                    print(f"Não foi possível obter informações da issue {args.issue}")
                    return 1

            # Se foi fornecido um projeto
            elif args.project:
                statuses = jira.get_project_statuses(args.project)
                if statuses:
                    print(f"\nProjeto: {args.project}")
                    print("Status disponíveis:")
                    status_names = [s['name'] for s in statuses]
                    for status in status_names:
                        print(f"  * {status}")

                    # Sugere configuração baseada nos status encontrados
                    self._suggest_automation_config(status_manager, status_names, args.apply)
                else:
                    print(f"Não foi possível obter status do projeto {args.project}")
                    return 1

            else:
                print("Forneça --project ou --issue para descobrir status")
                print("Exemplo: dev-peace automation configure --project PROJ")
                print("Exemplo: dev-peace automation configure --issue PROJ-123")
                return 1

        except Exception as e:
            print(f"Erro ao configurar automação: {e}")
            return 1

        return 0

    def _handle_auto_revert(self, status_manager, args):
        """Gerencia configuração de reversão automática."""
        rules = status_manager.status_rules.copy()

        if args.action == 'status':
            # Mostra status atual
            auto_revert = rules.get('auto_revert_on_session_end', False)
            print("Reversão Automática de Status")
            print("=" * 35)
            print(f"Status: {'[Habilitada]' if auto_revert else '[Desabilitada]'}")

            if auto_revert:
                print("\nComo funciona:")
                print("* Quando você inicia trabalho em uma issue, o status original é salvo")
                print("* Se o status for alterado automaticamente (ex: Fila desenvolvimento -> Implementando)")
                print("* Quando a sessão for finalizada, o status volta automaticamente ao original")
                print("* Exemplo: Implementando -> Fila desenvolvimento")
            else:
                print("\nPara habilitar:")
                print("dev-peace automation auto-revert enable")

            return 0

        elif args.action == 'enable':
            # Habilita reversão automática
            rules['auto_revert_on_session_end'] = True
            status_manager.save_status_rules(rules)
            print("Reversão automática de status habilitada!")
            print("Agora o status será revertido automaticamente quando sessões forem finalizadas")
            return 0

        elif args.action == 'disable':
            # Desabilita reversão automática
            rules['auto_revert_on_session_end'] = False
            status_manager.save_status_rules(rules)
            print("Reversão automática de status desabilitada")
            print("Status não serão mais revertidos automaticamente")
            return 0

        else:
            print(f"Ação não reconhecida: {args.action}")
            return 1

    def _suggest_automation_config(self, status_manager, available_statuses, apply_config=False):
        """Sugere configuração baseada nos status disponíveis."""
        print("\nSugestões de configuração:")

        # Mapeia status comuns (incluindo variações em português)
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
            print("\nConfiguração sugerida:")

            if 'todo' in found_statuses and 'in_progress' in found_statuses:
                print(f"Início de trabalho: {found_statuses['todo']} -> {found_statuses['in_progress']}")

            if 'in_progress' in found_statuses and 'done' in found_statuses:
                print(f"Finalização: {found_statuses['in_progress']} -> {found_statuses['done']}")

            if apply_config:
                # Aplica a configuração automaticamente
                print("\nConfigurando automaticamente...")
                rules = status_manager.status_rules.copy()

                if 'todo' in found_statuses and 'in_progress' in found_statuses:
                    rules['rules']['on_work_start']['from_status'] = [found_statuses['todo']]
                    rules['rules']['on_work_start']['to_status'] = found_statuses['in_progress']
                    print(f"Configurado início de trabalho: {found_statuses['todo']} -> {found_statuses['in_progress']}")

                if 'in_progress' in found_statuses and 'done' in found_statuses:
                    rules['rules']['on_work_complete']['from_status'] = [found_statuses['in_progress']]
                    rules['rules']['on_work_complete']['to_status'] = found_statuses['done']
                    print(f"Configurado finalização: {found_statuses['in_progress']} -> {found_statuses['done']}")

                # Salva as regras
                status_manager.save_status_rules(rules)
                print("Configuração salva com sucesso!")
            else:
                print("\nPara aplicar esta configuração automaticamente:")
                print("dev-peace automation configure --project <PROJETO> --apply")
                print("\nOu edite manualmente:")
                print("dev-peace config --show")
                print("Ou use a interface interativa: dev-peace interactive")
        else:
            print("Não foi possível mapear automaticamente os status")
            print("Configure manualmente usando os status listados acima")

    def handle_jira_status(self, args):
        """Gerencia descoberta de status do Jira."""
        from ..jira_integration.client import JiraClient

        if not args.jira_status_action:
            print("Ação não especificada")
            print("Use: dev-peace jira-status --help")
            return 1

        # Verifica configuração do Jira
        jira_config = self.config.get_jira_config()
        if not all(jira_config.values()):
            print("Jira não está configurado")
            return 1

        try:
            # Conecta ao Jira
            jira = JiraClient(jira_config['url'], jira_config['user'], jira_config['token'])
            if not jira.connect():
                print("Falha na conexão com Jira")
                return 1

            if args.jira_status_action == 'projects':
                return self._list_jira_projects(jira)
            elif args.jira_status_action == 'list':
                return self._list_project_statuses(jira, args.project_key)
            elif args.jira_status_action == 'workflow':
                return self._show_issue_workflow(jira, args.issue_key)
            else:
                print(f"Ação não reconhecida: {args.jira_status_action}")
                return 1

        except Exception as e:
            print(f"Erro ao acessar Jira: {e}")
            return 1

    def _list_jira_projects(self, jira):
        """Lista projetos do Jira."""
        print("Buscando projetos do Jira...")
        projects = jira.get_projects()

        if not projects:
            print("Nenhum projeto encontrado")
            return 0

        print(f"\nEncontrados {len(projects)} projetos:")
        print("=" * 50)

        for project in projects:
            print(f"Key: {project['key']} - {project['name']}")
            if project['description']:
                print(f"   Desc: {project['description']}")
            if project['lead']:
                print(f"   Lead: {project['lead']}")
            print()

        print("Dica: Para ver status de um projeto:")
        print("dev-peace jira-status list <CHAVE_PROJETO>")

        return 0

    def _list_project_statuses(self, jira, project_key):
        """Lista status de um projeto."""
        print(f"Buscando status do projeto {project_key}...")
        statuses = jira.get_project_statuses(project_key)

        if not statuses:
            print(f"Nenhum status encontrado para o projeto {project_key}")
            return 0

        print(f"\nStatus disponíveis no projeto {project_key}:")
        print("=" * 40)

        for status in statuses:
            print(f"Status: {status['name']}")

        print(f"\nDica: Para configurar automação baseada nestes status:")
        print(f"dev-peace automation configure --project {project_key}")

        return 0

    def _show_issue_workflow(self, jira, issue_key):
        """Mostra workflow de uma issue."""
        print(f"Analisando workflow da issue {issue_key}...")
        workflow_info = jira.get_issue_workflow_statuses(issue_key)

        if not workflow_info:
            print(f"Não foi possível obter informações da issue {issue_key}")
            return 1

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

        print(f"\nDica: Para configurar automação baseada nesta issue:")
        print(f"dev-peace automation configure --issue {issue_key}")

        return 0
    
    def run(self, args=None):
        """Executa o CLI."""
        parser = self.create_parser()
        parsed_args = parser.parse_args(args)
        
        if not parsed_args.command:
            parser.print_help()
            return 0
        
        # Mapeia comandos para handlers
        handlers = {
            'start': self.handle_start,
            'stop': self.handle_stop,
            'add': self.handle_add,
            'status': self.handle_status,
            'list': self.handle_list,
            'orphans': self.handle_orphans,
            'config': self.handle_config,
            'interactive': self.handle_interactive,
            'docs': self.handle_docs,
            'stats': self.handle_stats,
            'daemon': self.handle_daemon,
            'status-issue': self.handle_status_issue,
            'automation': self.handle_automation,
            'jira-status': self.handle_jira_status,
        }
        
        handler = handlers.get(parsed_args.command)
        if handler:
            return handler(parsed_args)
        else:
            print(f"Comando não implementado: {parsed_args.command}")
            return 1


def main():
    """Ponto de entrada principal."""
    cli = DevPeaceCLI()
    return cli.run()


if __name__ == '__main__':
    sys.exit(main())
