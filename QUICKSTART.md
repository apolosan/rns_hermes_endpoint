# QUICKSTART — Hermes for Reticulum

Guia mínimo para colocar o bridge no ar em **menos de 10 minutos**.

## Pré-requisitos

- Linux (ou macOS) com Python **3.11+**
- [Hermes Agent](https://github.com/NousResearch/hermes-agent) instalado e testado:

```bash
hermes chat -q "responda apenas OK"
```

- (Opcional) VPS com porta **37428/TCP** liberada no firewall, se o nó for acessível pela internet

## 1. Clonar e instalar

```bash
git clone https://github.com/apolosan/rns_hermes_endpoint.git
cd rns_hermes_endpoint
bash install.sh
source venv/bin/activate
```

O `install.sh` cria o `venv`, instala o pacote, prepara `~/.lxmf/storage` e copia `config/reticulum.conf` para `~/.reticulum/config` quando ainda não existir.

## 2. Configurar ambiente

```bash
cp config/env.example .env
```

Edite `.env` — no mínimo:

```bash
# Caminho do hermes, se não estiver no PATH
HERMES_BIN=/caminho/para/hermes

# Seu hash LXMF do Sideband (Sideband → Settings → Identity)
HERMES_RETICUM_ALLOW_ALL=false
HERMES_RETICUM_ALLOWED_USERS=SEU_HASH_LXMF_AQUI
```

## 3. Ajustar Reticulum (se necessário)

Arquivo: `~/.reticulum/config` (ou `config/reticulum.conf` no repositório como referência).

**Servidor TCP** — escuta conexões na sua máquina:

```ini
[[TCP Server Interface]]
  type = TCPServerInterface
  enabled = yes
  listen_ip = 0.0.0.0
  listen_port = 37428
```

**Cliente TCP** — conecta a um peer existente na mesh (opcional):

```ini
[[TCP Client]]
  type = TCPClientInterface
  enabled = yes
  target_host = YOUR_MESH_PEER_HOST
  target_port = YOUR_MESH_PEER_PORT
```

Firewall (exemplo):

```bash
sudo ufw allow 37428/tcp
```

## 4. Iniciar o bridge

```bash
hermes-reticulum run
```

Na saída, anote o **endereço LXMF** (hash de 32 caracteres hex).

Alternativa em background:

```bash
./start.sh start
./start.sh status
./start.sh stop
```

## 5. Conectar no Sideband

1. Instale o [Sideband](https://github.com/markqvist/Sideband/releases/latest) no Android
2. Configure interface de rede (TCP para o IP:37428 do servidor, ou LoRa)
3. Adicione o endereço LXMF do bridge como **contato**
4. Envie uma mensagem de teste

## Verificação rápida

```bash
hermes-reticulum address    # endereço LXMF
hermes-reticulum status     # estado do bridge
hermes-reticulum run -v     # log detalhado para depuração
```

## Problemas comuns

| Sintoma | Solução |
|---------|---------|
| `hermes: command not found` | Defina `HERMES_BIN` no `.env` |
| Mensagem ignorada | Confirme seu hash em `HERMES_RETICUM_ALLOWED_USERS` |
| Sideband não conecta | Verifique IP, porta 37428 e firewall |
| Erro de identidade LXMF | Apague `~/.lxmf/storage` **somente** se puder regenerar contatos |

## Próximos passos

- Detalhes completos: [README.md](README.md)
- Serviço persistente: arquivos em `config/hermes-reticulum*.service`
- Desenvolvimento e testes: `pip install -e ".[dev]" && pytest tests/ -v`
