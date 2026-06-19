# Hermes for Reticulum

Ponte entre o [Hermes Agent](https://github.com/NousResearch/hermes-agent) e a rede mesh [Reticulum](https://reticulum.network) via [LXMF](https://github.com/markqvist/lxmf). Converse com seu agente de IA pelo [Sideband](https://github.com/markqvist/Sideband) — inclusive off-grid por LoRa.

```
Sideband (Android)                    Hermes Agent (servidor)
┌──────────────┐    LoRa / TCP / I2P   ┌──────────────────┐
│  Mensagem    │ ◄══════ Reticulum ═══► │  Agente de IA    │
│              │    LXMF (criptografado)│                  │
└──────────────┘                        └──────────────────┘
```

## O que é?

Este projeto implementa um bridge LXMF que encaminha mensagens da rede Reticulum para o Hermes Agent e devolve as respostas. Principais benefícios:

- **Chat com IA em qualquer lugar** — inclusive sem internet, via rádio LoRa
- **Criptografia ponta a ponta** (Curve25519 + AES-128)
- **Sem infraestrutura central** — sem servidores proprietários nem cadastros
- **Compatível com Sideband** (Android, Linux, macOS, Windows)

## Requisitos

| Item | Versão / detalhe |
|------|------------------|
| Python | 3.11 ou superior |
| Hermes Agent | Instalado e funcional (`hermes chat -q "test"`) |
| Servidor (opcional) | IP público com porta TCP aberta (padrão: 37428) |

## Início rápido

Para subir em poucos minutos, siga o [QUICKSTART.md](QUICKSTART.md).

## Instalação

```bash
# 1. Clonar o repositório
git clone https://github.com/apolosan/rns_hermes_endpoint.git
cd rns_hermes_endpoint

# 2. Instalar (cria venv e dependências)
bash install.sh

# 3. Ativar o ambiente virtual
source venv/bin/activate

# 4. Configurar variáveis de ambiente
cp config/env.example .env
# Edite .env conforme sua instalação

# 5. Configurar Reticulum (interface TCP Server)
#    O instalador copia config/reticulum.conf para ~/.reticulum/config se não existir.
#    Ajuste listen_port e, se necessário, o peer TCP Client:
#
#    [[TCP Server Interface]]
#      type = TCPServerInterface
#      listen_ip = 0.0.0.0
#      listen_port = 37428
#
#    [[TCP Client]]
#      target_host = YOUR_MESH_PEER_HOST
#      target_port = YOUR_MESH_PEER_PORT

# 6. Liberar porta no firewall (se expuser o nó na internet)
sudo ufw allow 37428/tcp

# 7. Iniciar o bridge
hermes-reticulum run

# 8. Anotar o endereço LXMF exibido na inicialização
#    Adicione-o como contato no Sideband
```

## Comandos

```bash
hermes-reticulum run              # Inicia o bridge
hermes-reticulum run --verbose    # Log detalhado
hermes-reticulum address          # Exibe endereço LXMF
hermes-reticulum status           # Status do bridge

# Opções customizadas
hermes-reticulum run \
  --display-name "Meu Agente" \
  --stamp-cost 4 \
  --timeout 120 \
  --hermes-bin /caminho/para/hermes
```

## Arquitetura

```
┌─────────────────────────────────────────────────────────┐
│  Sideband (Android / Linux)                             │
│  └── Cliente LXMF → Stack Reticulum → LoRa/TCP/I2P      │
└─────────────────────┬───────────────────────────────────┘
                      │ mensagens LXMF (criptografadas)
                      ▼
┌─────────────────────────────────────────────────────────┐
│  Servidor / VPS                                         │
│  ┌─────────────────────────────────────────────────┐    │
│  │  Daemon Reticulum (interface TCP :37428)        │    │
│  └────────────────────┬────────────────────────────┘    │
│                       ▼                                  │
│  ┌─────────────────────────────────────────────────┐    │
│  │  Hermes for Reticulum (este projeto)            │    │
│  │  ├── LXMFBridge      — recepção LXMF           │    │
│  │  ├── HermesClient    — subprocesso hermes CLI  │    │
│  │  └── AccessControl   — filtro de remetentes    │    │
│  └────────────────────┬────────────────────────────┘    │
│                       ▼                                  │
│  ┌─────────────────────────────────────────────────┐    │
│  │  Hermes Agent (LLM, tools, memória, skills)     │    │
│  └─────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
```

## Configuração

### Variáveis de ambiente

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `RETICULUM_DISPLAY_NAME` | `Hermes for Reticulum` | Nome exibido na rede |
| `RETICULUM_STORAGE` | `~/.lxmf/storage` | Armazenamento LXMF |
| `RETICULUM_STAMP_COST` | `8` | Custo de stamp (controle de banda) |
| `RETICULUM_CONFIG` | `~/.reticulum` | Diretório de config Reticulum |
| `HERMES_BIN` | *(auto-detectado)* | Caminho do binário `hermes` |
| `HERMES_TIMEOUT` | `300` | Timeout do Hermes (segundos) |
| `HERMES_RETICUM_ALLOW_ALL` | `false` | Permitir qualquer remetente |
| `HERMES_RETICUM_ALLOWED_USERS` | *(vazio)* | Allowlist de hashes LXMF |
| `HERMES_RETICUM_BLOCKED_USERS` | *(vazio)* | Blocklist de hashes LXMF |

Modelo completo em [config/env.example](config/env.example).

### Detecção do binário Hermes

Ordem de busca automática:

1. `hermes` no `PATH`
2. `/opt/hermes/.venv/bin/hermes`
3. `/opt/hermes/bin/hermes`
4. `~/.hermes/bin/hermes`
5. `~/.local/bin/hermes`

Override: `--hermes-bin` ou variável `HERMES_BIN`.

### Controle de acesso

Por padrão, apenas endereços na allowlist podem interagir (`HERMES_RETICUM_ALLOW_ALL=false`).

```bash
# Em .env
HERMES_RETICUM_ALLOW_ALL=false
HERMES_RETICUM_ALLOWED_USERS=hash_lxmf_do_sideband,outro_hash_opcional
```

O hash LXMF aparece em Sideband → Settings → Identity.

## Serviço systemd

Ajuste os caminhos em `config/hermes-reticulum*.service` antes de instalar.

### Nível de usuário (sem root)

```bash
mkdir -p ~/.config/systemd/user/
cp config/hermes-reticulum.user.service ~/.config/systemd/user/hermes-reticulum.service
# Edite WorkingDirectory, Environment e ExecStart para seus caminhos
systemctl --user daemon-reload
systemctl --user enable --now hermes-reticulum
journalctl --user -u hermes-reticulum -f
```

### Nível de sistema (root)

```bash
sudo cp config/hermes-reticulum.service /etc/systemd/system/
# Edite caminhos e usuário do serviço conforme o deploy
sudo systemctl daemon-reload
sudo systemctl enable --now hermes-reticulum
```

## Conectar pelo Sideband (Android)

1. Instale o [Sideband](https://github.com/markqvist/Sideband/releases/latest)
2. Configure uma interface de rede (Wi-Fi/TCP ou LoRa)
3. Adicione o endereço LXMF do bridge como contato
4. Envie uma mensagem — o agente responde via Hermes

## Desenvolvimento

```bash
git clone https://github.com/apolosan/rns_hermes_endpoint.git
cd rns_hermes_endpoint

python -m venv venv
source venv/bin/activate
pip install -e ".[dev]"

python -m pytest tests/ -v
ruff check src/ tests/
```

## Como funciona

1. Sideband envia mensagem LXMF para o hash do bridge
2. Reticulum roteia (LoRa, TCP ou I2P)
3. LXM Router valida assinatura e descriptografa
4. Thread pool processa em worker (não bloqueante)
5. AccessControl verifica remetente
6. HermesClient executa `hermes chat -q "<mensagem>"`
7. Resposta retorna como mensagem LXMF ao Sideband

## Segurança

- Criptografia ponta a ponta (Curve25519 + AES-128)
- Forward secrecy via links efêmeros
- Assinaturas Ed25519 nas mensagens
- Controle de acesso por hash de identidade
- Pool de threads limita processamento concorrente
- O hash LXMF é público na rede (equivalente a um identificador de contato)

## Licença

MIT

## Créditos

- [Reticulum](https://reticulum.network) — stack de rede mesh
- [LXMF](https://github.com/markqvist/lxmf) — protocolo de mensagens
- [Sideband](https://github.com/markqvist/Sideband) — cliente móvel
- [Hermes Agent](https://github.com/NousResearch/hermes-agent) — agente de IA
