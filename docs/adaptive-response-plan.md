# 🧠 Sistema de Resposta Adaptativa — Hermes for Reticulum

**Objetivo:** Detectar automaticamente a velocidade/qualidade do canal entre o cliente e o endpoint, e adaptar o tamanho e a taxa de resposta do agente para cada canal (LoRa vs TCP).

**Viabilidade:** ✅ Altamente viável — o RNS/LXMF já fornece toda a telemetria necessária.

---

## Descobertas da API (dados reais do RNS/LXMF)

### Métricas disponíveis no recebimento

| Métrica | Fonte | O que mede |
|---------|-------|------------|
| `message.rssi` | LXMessage | Potência do sinal recebido (dBm) |
| `message.snr` | LXMessage | Relação sinal/ruído (dB) |
| `message.method` | LXMessage | Transporte: `DIRECT`=2, `OPPORTUNISTIC`=1, `PROPAGATED`=3 |
| `message.requested_delivery` | LXMessage | True se veio via link (TCP/LoRa direto) |
| `message.transport_encryption` | LXMessage | Tipo de criptografia usada |

### Métricas disponíveis via Transport (estáticas por destino)

| Métrica | Fonte | O que mede |
|---------|-------|------------|
| `Transport.next_hop_interface_bitrate(hash)` | Transport | **Bitrate real** do próximo hop (bps) |
| `Transport.next_hop_interface_hw_mtu(hash)` | Transport | **MTU hardware** do próximo hop (bytes) |
| `Transport.hops_to(hash)` | Transport | Número de **hops** até o destino |
| `Transport.next_hop_per_byte_latency(hash)` | Transport | Latência por byte (segundos/byte) |
| `Transport.next_hop_per_bit_latency(hash)` | Transport | Latência por bit |

### Limites de payload por método de entrega

| Método | MDU | Conteúdo máximo |
|--------|-----|-----------------|
| Link direto (criptografado) | 431 bytes | 319 bytes |
| Plain packet | 464 bytes | 368 bytes |
| Encrypted packet | 391 bytes | 295 bytes |
| LoRa (SF10, 125kHz) | ~250 bytes | ~140 bytes |

---

## 5W2H — Análise Completa

### 1. WHAT — O que é o sistema adaptativo?

| # | Pergunta | Resposta |
|---|----------|----------|
| W1 | O que o sistema faz? | Detecta o canal e ajusta automaticamente tamanho/resposta |
| W2 | Quais variáveis adapta? | Tamanho máximo de resposta, tokens, verbosidade, formato |
| W3 | Onde acontece a adaptação? | No bridge (antes de enviar ao Hermes) e no pós-processamento (antes de enviar reply) |
| W4 | É transparente para o usuário? | Sim — o usuário não percebe, apenas recebe respostas adequadas |
| W5 | Substitui a config manual? | Não — complementa. Config manual tem prioridade |

### 2. WHO — Quem se beneficia?

| # | Pergunta | Resposta |
|---|----------|----------|
| H1 | Quem define os limites? | O endpoint (bridge) com base na telemetria |
| H2 | O agente Hermes sabe do canal? | Sim — via system prompt injetado dinamicamente |
| H3 | Usuários TCP são afetados? | Não — recebem respostas completas |
| H4 | Usuários LoRa são afetados? | Sim — recebem respostas comprimidas/otimizadas |

### 3. WHEN — Quando a adaptação acontece?

| # | Pergunta | Resposta |
|---|----------|----------|
| T1 | Quando detecta o canal? | **Antes** de chamar Hermes (pré-chamada) |
| T2 | Quando adapta a resposta? | **Depois** de receber do Hermes, **antes** de enviar via LXMF |
| T3 | A detecção é por mensagem? | Sim — cada mensagem pode ter canal diferente |
| T4 | A detecção é cacheada? | Sim — bitrate por destino é cacheado com TTL |

### 4. WHERE — Onde no fluxo?

| # | Pergunta | Resposta |
|---|----------|----------|
| R1 | Onde coleta métricas? | No callback `_on_lxmf_message` (RSSI, SNR, método) |
| R2 | Onde consulta bitrate? | `Transport.next_hop_interface_bitrate(dest_hash)` |
| R3 | Onde aplica limites? | No system prompt do hermes chat (via `-q` flag) |
| R4 | Onde trunca resposta? | No `send_reply()` antes de criar LXMessage |

### 5. WHY — Por que é necessário?

| # | Pergunta | Resposta |
|---|----------|----------|
| Y1 | Por que não resposta fixa? | LoRa: 250 bytes/pacote vs TCP: 1500 bytes. Resposta fixa falha em LoRa |
| Y2 | Por que não truncar só? | Truncar perde contexto. Adaptar o prompt preserva qualidade |
| Y3 | Por que detectar automaticamente? | Usuário não sabe informar o canal. Auto-detect elimina config |
| Y4 | Qual o custo de NÃO fazer? | LoRa: mensagens truncadas, timeouts, perda de informação |

### 6. HOW — Como implementar?

| # | Pergunta | Resposta |
|---|----------|----------|
| HW1 | Coleta de métricas | RSSI + SNR + método do LXMessage + bitrate do Transport |
| HW2 | Classificação do canal | LoRa (bitrate <100kbps) vs TCP (bitrate >1Mbps) |
| HW3 | Perfis de resposta | `lora_low`, `lora_mid`, `tcp_fast`, `tcp_default` |
| HW4 | Adaptação do prompt | System prompt dinâmico com instruções de tamanho |
| HW5 | Truncamento inteligente | Respeitar limites MDU do LXMF por método |

### 7. HOW MUCH — Quanto custa?

| # | Pergunta | Resposta |
|---|----------|----------|
| HM1 | Overhead de processamento | Negligível — 1 chamada estática por mensagem |
| HM2 | Overhead de memória | ~100 bytes por destino cacheado |
| HM3 | Economia de tokens | ~60-80% em LoRa (respostas 3-5x menores) |
| HM4 | Redução de latência | ~5-20x em LoRa (menos pacotes = menos retransmissões) |

---

## Perfis de Resposta

### Definição dos Perfis

```python
PROFILES = {
    # LoRa com sinal fraco (RSSI < -110 dBm ou SNR < 5 dB)
    "lora_constrained": {
        "max_response_chars": 200,       # ~3 pacotes LoRa
        "max_tokens_prompt": 100,        # Prompt curto
        "verbosity": "minimal",          # Sem exemplos, sem explicações
        "format": "plain",               # Sem markdown
        "split_long": True,              # Divide em múltiplas mensagens
        "send_delay_ms": 2000,           # Intervalo entre partes
        "instruction": (
            "Responda em até 3 frases curtas. "
            "Sem formatação. Sem exemplos. "
            "Vá direto ao ponto. Máximo 200 caracteres."
        ),
    },

    # LoRa com sinal bom (RSSI > -110 dBm ou SNR > 5 dB)
    "lora_standard": {
        "max_response_chars": 500,       # ~7 pacotes LoRa
        "max_tokens_prompt": 200,
        "verbosity": "concise",
        "format": "plain",
        "split_long": True,
        "send_delay_ms": 1500,
        "instruction": (
            "Responda de forma concisa em até 5 frases. "
            "Sem formatação markdown. "
            "Se a resposta tem mais de 500 caracteres, divida em partes."
        ),
    },

    # TCP com boa conexão
    "tcp_default": {
        "max_response_chars": 4000,      # ~6 pacotes TCP
        "max_tokens_prompt": 2000,
        "verbosity": "normal",
        "format": "plain_text",          # TCP mas LXMF = sem markdown
        "split_long": True,
        "send_delay_ms": 500,
        "instruction": (
            "Responda de forma clara e completa. "
            "Use texto simples (sem markdown). "
            "Máximo 4000 caracteres."
        ),
    },

    # Fallback / desconhecido
    "default": {
        "max_response_chars": 1000,
        "max_tokens_prompt": 500,
        "verbosity": "normal",
        "format": "plain",
        "split_long": True,
        "send_delay_ms": 1000,
        "instruction": (
            "Responda de forma clara. "
            "Máximo 1000 caracteres."
        ),
    },
}
```

### Algoritmo de Classificação

```
Mensagem recebida
  │
  ├─ Extrair: rssi, snr, method, bitrate (via Transport)
  │
  ├─ Classificar canal:
  │   ├─ bitrate < 50.000 bps  → LoRa
  │   ├─ bitrate >= 50.000 bps → TCP/Outro
  │   └─ bitrate = None        → Inferir pelo método
  │       ├─ method = OPPORTUNISTIC → LoRa (single packet)
  │       ├─ method = DIRECT        → TCP (link estabelecido)
  │       └─ method = PROPAGATED    → Via propagation node
  │
  ├─ Se LoRa:
  │   ├─ RSSI < -110 ou SNR < 5  → lora_constrained
  │   └─ RSSI >= -110 e SNR >= 5 → lora_standard
  │
  ├─ Se TCP:
  │   └─ tcp_default
  │
  └─ Selecionar perfil → Aplicar ao prompt + truncamento
```

---

## Arquitetura da Implementação

### Componentes

```
┌─────────────────────────────────────────────────────┐
│  _on_lxmf_message (callback)                        │
│  ├── 1. Extrair métricas do LXMessage               │
│  │      rssi, snr, method, stamp_cost               │
│  ├── 2. Consultar Transport (bitrate, hops)          │
│  │      Transport.next_hop_interface_bitrate(hash)   │
│  ├── 3. Classificar canal → selecionar perfil        │
│  │      ChannelProfiler.classify(metrics)            │
│  └── 4. Passar perfil ao handler                     │
│         handle(src, content, profile)                │
└──────────────────────┬──────────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────────┐
│  handle (message handler)                            │
│  ├── 5. Construir prompt com instrução do perfil     │
│  │      f"{profile.instruction}\n\n{content}"        │
│  ├── 6. Chamar Hermes com timeout ajustado           │
│  │      hermes.chat(prompt, timeout=profile.timeout) │
│  └── 7. Retornar reply (raw — truncação no próximo)  │
└──────────────────────┬──────────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────────┐
│  _process_and_reply                                  │
│  ├── 8. Truncar reply ao max_response_chars          │
│  │      if len(reply) > profile.max_response_chars   │
│  ├── 9. Dividir em partes se necessário              │
│  │      split_message(reply, max_chars)              │
│  └── 10. Enviar cada parte com delay                 │
│          bridge.send_reply(dest, part)                │
│          time.sleep(profile.send_delay_ms / 1000)    │
└─────────────────────────────────────────────────────┘
```

### Novos Arquivos

| Arquivo | Responsabilidade |
|---------|-----------------|
| `src/hermes_reticulum/core/profiler.py` | ChannelProfiler — classificação e perfis |
| `src/hermes_reticulum/core/adapter.py` | Adaptador de prompt e resposta |

### Alterações em Arquivos Existentes

| Arquivo | Mudança |
|---------|---------|
| `core/bridge.py` | Passar métricas ao handler; usar profiler |
| `core/hermes_client.py` | Aceitar profile; construir prompt adaptativo |
| `tests/test_profiler.py` | Testes do profiler |

---

## Fluxo Detalhado (pseudocódigo)

```python
# 1. No callback de recebimento
def _on_lxmf_message(self, message):
    metrics = ChannelMetrics.from_lxmessage(message)
    # metrics.rssi, metrics.snr, metrics.method, metrics.bitrate

    profile = self.profiler.classify(metrics)
    # profile.max_response_chars, profile.instruction, etc.

    self._pool.submit(self._process_and_reply, src, content, profile)

# 2. No handler
def handle(src, content, profile):
    # Construir prompt com instrução adaptativa
    prompt = f"{profile.instruction}\n\nUsuário: {content}"
    reply = hermes.chat(prompt)
    return reply

# 3. No envio
def _process_and_reply(self, src, content, profile):
    reply = self._message_handler(src, content)

    if reply:
        # Truncar
        truncated = truncate_to_limit(reply, profile.max_response_chars)

        # Dividir se necessário
        parts = split_message(truncated, profile.max_response_chars)

        for i, part in enumerate(parts):
            if i > 0:
                time.sleep(profile.send_delay_ms / 1000)
            self.send_reply(src, part)
```

---

## Métricas Coletadas por Mensagem

```python
@dataclass
class ChannelMetrics:
    rssi: float | None        # dBm (-30 a -120)
    snr: float | None         # dB (-10 a +15)
    method: int               # DIRECT=2, OPPORTUNISTIC=1, PROPAGATED=3
    bitrate: int | None       # bps (via Transport)
    hw_mtu: int | None        # bytes (via Transport)
    hops: int | None          # número de hops
    source_hash: str          # hash do remetente

    @classmethod
    def from_lxmessage(cls, message) -> "ChannelMetrics":
        src = message.source_hash.hex()
        bitrate = RNS.Transport.next_hop_interface_bitrate(message.source_hash)
        mtu = RNS.Transport.next_hop_interface_hw_mtu(message.source_hash)
        hops = RNS.Transport.hops_to(message.source_hash)

        return cls(
            rssi=getattr(message, 'rssi', None),
            snr=getattr(message, 'snr', None),
            method=getattr(message, 'method', 0),
            bitrate=bitrate,
            hw_mtu=mtu,
            hops=hops,
            source_hash=src,
        )
```

---

## Classificador de Canal

```python
LORA_BITRATE_THRESHOLD = 50_000  # 50 kbps — acima disso = TCP

class ChannelProfiler:
    def __init__(self, profiles: dict = None):
        self.profiles = profiles or DEFAULT_PROFILES
        self._cache: dict[str, ChannelProfile] = {}
        self._cache_ttl = 300  # 5 minutos

    def classify(self, metrics: ChannelMetrics) -> ChannelProfile:
        # Cache hit?
        cached = self._get_cached(metrics.source_hash)
        if cached:
            return cached

        # Classificar
        if metrics.bitrate is not None:
            is_lora = metrics.bitrate < LORA_BITRATE_THRESHOLD
        else:
            # Inferir pelo método
            is_lora = metrics.method == LXMF.LXMessage.OPPORTUNISTIC

        if is_lora:
            if metrics.rssi is not None and metrics.rssi < -110:
                profile = self.profiles["lora_constrained"]
            elif metrics.snr is not None and metrics.snr < 5:
                profile = self.profiles["lora_constrained"]
            else:
                profile = self.profiles["lora_standard"]
        else:
            profile = self.profiles["tcp_default"]

        # Cache
        self._cache[metrics.source_hash] = (profile, time.time())

        return profile
```

---

## Truncamento Inteligente

```python
def truncate_to_limit(text: str, max_chars: int) -> str:
    """Trunca respeitando limites de sentença."""
    if len(text) <= max_chars:
        return text

    # Cortar na última sentença completa dentro do limite
    truncated = text[:max_chars]

    # Tentar cortar em ponto final
    last_period = truncated.rfind('.')
    if last_period > max_chars * 0.5:  # Pelo menos 50% do texto
        return truncated[:last_period + 1]

    # Cortar em espaço (palavra inteira)
    last_space = truncated.rfind(' ')
    if last_space > max_chars * 0.5:
        return truncated[:last_space] + "..."

    # Fallback: truncar abruptamente
    return truncated + "..."

def split_message(text: str, max_chars: int) -> list[str]:
    """Divide mensagem longa em partes menores."""
    if len(text) <= max_chars:
        return [text]

    parts = []
    remaining = text

    while remaining:
        if len(remaining) <= max_chars:
            parts.append(remaining)
            break

        # Cortar em limite inteligente
        cut = truncate_to_limit(remaining, max_chars)
        parts.append(cut)
        remaining = remaining[len(cut):].lstrip()

    # Numerar partes se múltiplas
    if len(parts) > 1:
        parts = [f"[{i+1}/{len(parts)}] {p}" for i, p in enumerate(parts)]

    return parts
```

---

## Testes

| # | Teste | Esperado |
|---|-------|----------|
| T1 | RSSI=-90, SNR=10, bitrate=300 → perfil | `lora_standard` |
| T2 | RSSI=-115, SNR=3, bitrate=300 → perfil | `lora_constrained` |
| T3 | bitrate=1000000 → perfil | `tcp_default` |
| T4 | method=OPPORTUNISTIC, sem bitrate → perfil | `lora_standard` |
| T5 | method=DIRECT, sem bitrate → perfil | `tcp_default` |
| T6 | truncate("Hello world. How are you?", 15) | `"Hello world."` |
| T7 | truncate("Short", 100) | `"Short"` |
| T8 | split_message(texto_1000, 300) | 4 partes numeradas |
| T9 | Cache: mesma origem → mesmo perfil | True |
| T10 | Cache expira após TTL | True |

---

## Ganho Estimado

| Cenário | Antes | Depois | Ganho |
|---------|-------|--------|-------|
| LoRa: resposta típica | 1500 chars (6 pacotes) | 200 chars (3 pacotes) | **70% menos bandwidth** |
| LoRa: latência por resposta | 30-60s | 5-15s | **4x mais rápido** |
| LoRa: tokens Hermes | ~500 tokens | ~100 tokens | **80% menos custo** |
| TCP: resposta típica | 1500 chars | 4000 chars | **Mais信息量** |
| TCP: latência | <1s | <1s | Sem mudança |

---

## Conclusão

O sistema é **altamente viável** porque:
1. **Toda a telemetria já existe** no RNS/LXMF (bitrate, RSSI, SNR, MTU)
2. **O custo de implementação é baixo** — 2 novos arquivos + alterações menores
3. **O ganho é significativo** — 70% menos bandwidth, 4x mais rápido em LoRa
4. **É transparente** — o usuário não percebe a adaptação
5. **É backwards-compatible** — funciona igual sem as métricas (fallback)
