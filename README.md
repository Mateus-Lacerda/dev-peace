# 🕊️ Dev Peace

**O observador zen que transforma seu caos de desenvolvimento em worklogs organizados!**

Cansado de esquecer de registrar suas horas no Jira? Farto de tentar lembrar o que você fez ontem? Dev Peace está aqui para trazer paz à sua vida de dev!

Ele observa silenciosamente seus repositórios, detecta quando você entra neles, monitora suas modificações, registra seus commits e ainda por cima conversa com o Jira para você. É quase como ter um assistente pessoal, mas sem o salário!

## ✨ Funcionalidades

- 👁️ **Monitoramento automático** de repositórios Git
- 🔍 **Detecção inteligente** de entrada em repositórios
- 🌿 **Extração automática** de issues do Jira do nome da branch
- ⏱️ **Registro automático** de tempo de trabalho
- 📝 **Worklogs automáticos** no Jira
- 💬 **Comentários automáticos** de commits nas issues
- 👻 **Gerenciamento de registros órfãos** (sem issue pai)
- 🎨 **Interface interativa bonita** com InquirerPy
- 🤖 **CLI poderoso** com comandos intuitivos

## 🚀 Instalação

```bash
# Clone o repositório
git clone https://github.com/Mateus-Lacerda/dev-peace.git
cd dev-peace

# Instale usando o Makefile (recomendado)
make install

# Instale o comando globalmente (opcional)
make install-global

# Instale como serviço (daemon) para rodar sempre em background
# Detecta automaticamente se é Linux (systemd) ou macOS (launchd)
make service
```

## 🎯 Como usar

### Configuração inicial

```bash
# Configure o Jira
dev-peace config --jira-url https://sua-empresa.atlassian.net \
                  --jira-user seu.email@empresa.com \
                  --jira-token seu-token-api

# Adicione um repositório para monitoramento
dev-peace add /caminho/para/seu/repositorio
```

### Comandos principais

```bash
# Inicia o monitoramento (modo zen ativado)
dev-peace start

# Vê o que está rolando
dev-peace status

# Interface bonita para os preguiçosos
dev-peace interactive

# Vê os registros perdidos na vida
dev-peace orphans

# Lista repositórios monitorados
dev-peace list

# Para o monitoramento (hora do café!)
dev-peace stop
```

## 🌿 Como funciona

1. **Detecção de entrada**: Monitora abertura de `.git/HEAD` e `.git/index`
2. **Extração de issue**: Analisa nome da branch no formato `tipo/PROJ-123`
3. **Monitoramento de atividades**: Registra modificações de arquivos e commits
4. **Integração Jira**: Busca a issue e registra worklogs automaticamente
5. **Registros órfãos**: Salva sessões sem issue para associação manual posterior

## 📋 Padrões de branch suportados

- `feature/PROJ-123`
- `bugfix/PROJ-123-descricao`
- `PROJ-123`
- `hotfix/PROJ123`

## 🎨 Interface interativa

Execute `dev-peace interactive` para acessar uma interface bonita com:

- 📊 Status em tempo real
- 📁 Gerenciamento de repositórios
- 👻 Associação de registros órfãos
- ⚙️ Configurações do Jira
- 🔗 Testes de conectividade

## 🤝 Contribuindo

Contribuições são bem-vindas! Por favor:

1. Fork o projeto
2. Crie uma branch para sua feature (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

## 📄 Licença

Este projeto está licenciado sob a Licença MIT - veja o arquivo [LICENSE](LICENSE) para detalhes.

## 🙏 Agradecimentos

- Aos desenvolvedores que esquecem de registrar horas (todos nós)
- Ao Jira por existir (mesmo sendo complicado às vezes)
- Ao Git por ser incrível
- À comunidade Python por todas as bibliotecas fantásticas

---

**Que a paz esteja com seu código! 🧘‍♂️**