# 🧪 Análise 5W2H — Hermes for Reticulum

**Data:** 2026-06-19
**Objetivo:** Esgotar todas as questões, riscos e cenários de falha antes da instalação e configuração.

---

## 1. WHAT — O que é o projeto?

### 1.1 Perguntas sobre o produto
| # | Pergunta | Resposta | Status |
|---|----------|----------|--------|
| W1 | O que o projeto faz? | Bridge entre Hermes Agent e Reticulum/LXMF | ✅ Definido |
| W2 | Quais são os componentes principais? | LXMFBridge, HermesClient, ACL, CLI, Plugin Adapter | ✅ Implementado |
| W3 | Qual protocolo de comunicação? | LXMF sobre Reticulum (TCP/LoRa/I2P) | ✅ Definido |
| W4 | O projeto é um daemon ou CLI? | Ambos — CLI `hermes-reticulum run` ou systemd service | ✅ Implementado |
| W5 | O que diferencia de um simples webhook? | Criptografia E2E, mesh networking, off-grid via LoRa | ✅ Valor definido |

### 1.2 Perguntas sobre escopo
| # | Pergunta | Resposta | Status |
|---|----------|----------|--------|
| W6 | O projeto suporta múltiplos usuários? | Sim, ACL controla quem pode interagir | ⚠️ Verificar limites |
| W7 | Suporta mensagens de grupo? | Não — LXMF é point-to-point por padrão | ❌ Não implementado |
| W8 | Suporta arquivos/imagem? | Não — apenas texto puro | ⚠️ Limitação conhecida |
| W9 | Suporta históricos de conversa? | Sim, via sessões do Hermes | ⅆ Depende do Hermes |
| W10 | O projeto funciona sem Hermes instalado? | Não — depende do hermes CLI | ⚠️ Não validado |

---

## 2. WHO — Quem usa e impacta?

### 2.1 Stakeholders
| # | Pergunta | Resposta | Status |
|---|----------|----------|--------|
| H1 | Quem é o usuário final? | Einar (via Sideband no Android) | ✅ |
| H2 | Quem administra o servidor? | Einar (VPS Debian 13) | ✅ |
| H3 | Outros podem usar? | Sim, se AllowAll=true ou estiverem na allowlist | ⚠️ |
| H4 | Exige conhecimento técnico? | Sim — Reticulum, CLI, systemd | ⚠️ |

### 2.2 Usuários do Sideband
| # | Pergunta | Resposta | Status |
|---|----------|----------|--------|
| H5 | Sideband precisa de config especial? | Apenas adicionar o hash LXMF como contato | ✅ |
| H6 | Sideband funciona em todas versões Android? | Depende do APK — verificar compatibilidade | ❌ Não verificado |
| H7 | Múltiplos Sideband podem se conectar? | Sim, se a allowlist permitir | ✅ |

---

## 3. WHEN — Quando executar e quando falha?

### 3.1 Timing
| # | Pergunta | Resposta | Risco |
|---|----------|----------|-------|
| T1 | Quando o bridge inicia? | Ao executar `hermes-reticulum run` | 🟢 |
| T2 | Quando uma mensagem é recebida? | Callback síncrono no thread do RNS | 🟡 Thread safety |
| T3 | Quanto tempo leva o reply do Hermes? | Depende do LLM — 5s a 300s | 🔴 Timeout |
| T4 | A identidade é gerada quando? | Na primeira execução | 🟢 |
| T5 | O announce acontece quando? | No startup e manualmente | 🟢 |
| T6 | Quando a identidade expira? | Nunca — persiste em disco | 🟢 |

### 3.2 Cenários de Timeout
| # | Pergunta | Resposta | Risco |
|---|----------|----------|-------|
| T7 | O que acontece se o Hermes demorar > timeout? | Retorna mensagem de erro ao usuário | 🟡 UX |
| T8 | O que acontece se a rede Reticulum cair? | Mensagens ficam em fila no LXM Router | 🟡 |
| T9 | O que acontece se o Sideband estiver offline? | LXMF tenta reenvio ou via propagation node | 🟡 |
| T10 | Quanto tempo o LXM Router mantém mensagens? | MESSAGE_EXPIRY (padrão ~48h) | 🟡 |

---

## 4. WHERE — Onde executa?

### 4.1 Ambiente
| # | Pergunta | Resposta | Risco |
|---|----------|----------|-------|
| R1 | Onde roda o bridge? | VPS Debian 13 (161.97.99.90) | 🟢 |
| R2 | Qual porta TCP? | 37428 (configurável) | 🔴 Firewall |
| R3 | A VPS tem IP público? | Sim (161.97.99.90) | 🟢 |
| R4 | Onde ficam os dados? | ~/.lxmf/storage/ | 🟡 Backup |
| R5 | Onde fica o config RNS? | ~/.reticulum/config | 🟡 Backup |
| R6 | Onde ficam os logs? | stdout → journalctl (systemd) | 🟢 |

### 4.2 Rede
| # | Pergunta | Resposta | Risco |
|---|----------|----------|-------|
| R7 | A porta 37428 está aberta? | **NÃO VERIFICADO** | 🔴 Crítico |
| R8 | O firewall permite TCP 37428? | **NÃO VERIFICADO** | 🔴 Crítico |
| R9 | Há NAT entre a VPS e a Internet? | IP público direto — OK | 🟢 |
| R10 | Sideband consegue alcançar a VPS? | Via TCP se a porta estiver aberta | 🔴 |
| R11 | Há propagação nodes disponíveis? | Depende da rede Reticulum pública | 🟡 |

---

## 5. WHY — Por que escolher essa abordagem?

### 5.1 Justificativa
| # | Pergunta | Resposta | Risco |
|---|----------|----------|-------|
| Y1 | Por que Reticulum e não outro protocolo? | Criptografia E2E, mesh, LoRa nativo, sem servidor | 🟢 |
| Y2 | Por que LXMF e não RNS Links direto? | LXMF é o protocolo do Sideband — compatibilidade | 🟢 |
| Y3 | Por que subprocess hermes CLI? | Mais simples que import direto; funciona com qualquer instalação | 🟡 Performance |
| Y4 | Por que systemd service? | Auto-restart, logging, persistência | 🟢 |

### 5.2 Alternativas consideradas
| # | Pergunta | Resposta | Decisão |
|---|----------|----------|---------|
| Y5 | Por que não usar hermes chat API diretamente? | API interna pode mudar; CLI é estável | CLI escolhido |
| Y6 | Por que não usar lxmd daemon? | lxmd não permite lógica customizada de reply | Bridge custom |
| Y7 | Por que não plugin puro do Hermes? | Plugin precisa do core mesmo sem gateway rodando | Standalone |

---

## 6. HOW — Como funciona cada parte?

### 6.1 Fluxo de Mensagem (CRÍTICO)

```
Sideband → LXMF msg → Reticulum (TCP) → LXM Router → callback → ACL → hermes chat -q → reply → LXM Router → Sideband
```

**Perguntas sobre o fluxo:**

| # | Pergunta | Resposta | Risco |
|---|----------|----------|-------|
| HW1 | O callback do LXM Router é thread-safe? | **NÃO** — roda no thread do RNS, não no main thread | 🔴 Crítico |
| HW2 | hermes chat -q é bloqueante? | Sim — subprocess.run() bloqueia até completion | 🔴 Crítico |
| HW3 | hermes chat -q cria sessão nova cada vez? | **NÃO** — reutiliza sessão por source=reticulum | 🟢 Bom |
| HW4 | O que acontece se hermes crashar durante reply? | Timeout → mensagem de erro ao usuário | 🟡 |
| HW5 | hermes chat -q suporta multi-turn? | Sim, via sessão — mas o CLI cria nova instância | 🟡 |
| HW6 | O subprocess hermes herda variáveis de ambiente? | Sim, via os.environ | 🟢 |
| HW7 | O hermes binary está no PATH? | **NÃO** — está em /opt/hermes/.venv/bin/hermes | 🔴 Crítico |

### 6.2 Segurança
| # | Pergunta | Resposta | Risco |
|---|----------|----------|-------|
| HW8 | A identidade é persistida com permissões seguras? | Depende do filesystem — verificar | 🟡 |
| HW9 | O allowlist aceita hashes inválidos? | Sim, ignora com warning — não bloqueia | 🟡 |
| HW10 | Mensagens ficam em disco? | Sim, em ~/.lxmf/storage/ | 🟡 |
| HW11 | O TLS protege o tráfego TCP? | **NÃO** — Reticulum usa criptografia própria, não TLS | 🟡 (OK, E2E) |

### 6.3 Estado e Concorrência
| # | Pergunta | Resposta | Risco |
|---|----------|----------|-------|
| HW12 | O bridge é multi-thread? | LXM Router usa threads internamente | 🟡 |
| HW13 | Múltiplas mensagens simultâneas? | hermes_client usa subprocess — serializa por sessão | 🟡 |
| HW14 | O que acontece com 10 mensagens simultâneas? | 10 subprocess hermes rodando — RAM/disk I/O | 🔴 |
| HW15 | O bridge sobrevive a restart do RNS? | Sim, reinicia e re-anuncia | 🟢 |
| HW16 | Identidade persiste entre restarts? | Sim, salva em disco | 🟢 |

---

## 7. HOW MUCH — Custos e limites?

### 7.1 Recursos
| # | Pergunta | Resposta | Risco |
|---|----------|----------|-------|
| HM1 | Quanto RAM consome? | RNS ~30MB + hermes ~200MB por subprocess | 🟡 |
| HD2 | Quanto disco para mensagens? | ~1KB por mensagem + overhead RNS | 🟢 |
| HD3 | Quanto CPU? | Mínimo — I/O bound | 🟢 |
| HD4 | Quanto bandwidth por mensagem? | ~200-500 bytes (LXMF overhead 111 bytes) | 🟢 |

### 7.2 Limites Técnicos
| # | Pergunta | Resposta | Risco |
|---|----------|----------|-------|
| HD5 | Tamanho máximo de mensagem LXMF? | ~4KB via link, ~250 bytes via LoRa | 🟡 |
| HD6 | Quantos usuários simultâneos? | Ilimitado tecnicamente, mas hermes serializa | 🟡 |
| HD7 | Latência máxima aceitável? | LoRa: 5-30s, TCP: <1s | 🟡 |
| HD8 | Requisitos de memória do servidor? | 512MB+ RAM recomendado | 🟢 |

---

## 🔴 PROBLEMAS CRÍTICOS ENCONTRADOS

### C1: hermes binary não está no PATH
```bash
# Problema: hermes está em /opt/hermes/.venv/bin/hermes
# Mas o venv do projeto não tem hermes no PATH
# O HermesClient vai falhar com FileNotFoundError
```
**Correção necessária:** Detectar automaticamente o caminho do hermes ou exigir configuração.

### C2: Callback do LXM Router não é thread-safe
```python
# O callback é chamado dentro do thread do RNS
# mas hermes_client.chat() é bloqueante (subprocess.run)
# Isso pode causar deadlock ou bloquear o loop de eventos do RNS
```
**Correção necessária:** Rodar o hermes_client.chat() em thread separada.

### C3: hermes chat -q pode não ter sessão persistente
```bash
# Cada chamada hermes chat -q pode criar sessão nova
# O agente não terá contexto entre mensagens
```
**Verificar:** Se `--source reticulum` mantém sessão entre chamadas.

### C4: Porta TCP 37428 pode estar bloqueada
```bash
# VPS pode ter firewall bloqueando a porta
# Sideband não conseguirá conectar
```
**Ação:** Verificar firewall e abrir porta.

### C5: Sem tratamento de sinais (SIGTERM/SIGINT) no run_forever
```python
# O run_forever usa time.sleep(1) em loop
# signal.pause() é melhor para Linux mas não cross-platform
```

---

## 🟡 PROBLEMAS MÉDIOS

| # | Problema | Impacto | Correção |
|---|---------|---------|----------|
| M1 | Sem graceful shutdown do LXM Router | Mensagens em trânsito podem ser perdidas | Adicionar cleanup |
| M2 | Sem retry automático em falha de envio | Mensagens podem falhar silenciosamente | Adicionar retry |
| M3 | Sem limitação de taxa (rate limiting) | Abuso possível | Adicionar cooldown |
| M4 | Logs misturados (RNS + hermes) | Difícil debug | Configurar loggers separados |
| M5 | Sem health check endpoint | Difícil monitorar | Adicionar /health |
| M6 | ACL não recarrega em runtime | Precisa restart para mudar | Hot reload |
| M7 | Sem suporte a voice messages | Sideband suporta, mas bridge não | Future work |
| M8 | Sem suportar lxm:// URIs | Poderia aceitar URIs diretamente | Future work |

---

## 🧪 TESTES A REALIZAR ANTES DA INSTALAÇÃO

### T1: Verificar porta TCP
```bash
# Na VPS, verificar se a porta está disponível
ss -tlnp | grep 37428
# Verificar firewall
iptables -L -n | grep 37428
# Ou ufw
ufw status | grep 37428
```

### T2: Testar hermes CLI
```bash
# Verificar se hermes funciona com --source reticulum
/opt/hermes/.venv/bin/hermes chat -q "teste" -Q --source reticulum
# Verificar se a sessão é reutilizada
/opt/hermes/.venv/bin/hermes chat -q "continuacao" -Q --source reticulum --continue
```

### T3: Testar RNS standalone
```bash
# Verificar se RNS funciona sem erros
python3 -c "import RNS; r = RNS.Reticulum(); print('OK')"
```

### T4: Testar LXMF standalone
```bash
# Verificar se LXMF funciona
python3 -c "import LXMF; r = LXMF.LXMRouter(storagepath='/tmp/test_lxmf'); print('OK')"
```

### T5: Testar identidade
```bash
# Gerar identidade e verificar
python3 -c "
import RNS
r = RNS.Reticulum()
ident = RNS.Identity()
print('Address:', RNS.prettyhexrep(ident.hash))
"
```

### T6: Testar envio LXMF
```bash
# Testar criação de mensagem
python3 -c "
import RNS, LXMF
r = RNS.Reticulum()
router = LXMF.LXMRouter(storagepath='/tmp/test_lxmf2')
ident = RNS.Identity()
dest = router.register_delivery_identity(ident, display_name='Test')
print('Destination:', RNS.prettyhexrep(dest.hash))
"
```

### T7: Testar subprocess hermes
```bash
# Verificar que hermes responde corretamente
python3 -c "
import subprocess
r = subprocess.run(
    ['/opt/hermes/.venv/bin/hermes', 'chat', '-q', 'diga apenas OK', '-Q'],
    capture_output=True, text=True, timeout=30
)
print('Exit:', r.returncode)
print('Reply:', r.stdout.strip()[:100])
"
```

---

## ✅ CHECKLIST PRÉ-INSTALAÇÃO

- [ ] Porta TCP 37428 aberta no firewall da VPS
- [ ] `hermes` CLI acessível (caminho configurado)
- [ ] `rns` e `lxmf` pip packages funcionais
- [ ] Identidade pode ser gerada e persistida
- [ ] Callback de mensagem funciona thread-safe
- [ ] Subprocess hermes retorna reply em tempo hábil
- [ ] ACL funciona (allowlist/blocklist)
- [ ] CLI `hermes-reticulum` funciona: run, status, address
- [ ] Systemd service inicia corretamente
- [ ] Logs são visíveis via journalctl
- [ ] Graceful shutdown funciona (SIGTERM)
- [ ] Sideband consegue descobrir o endereço LXMF
- [ ] Mensagem end-to-end funciona (Sideband → Hermes → Sideband)
- [ ] Identidade persiste entre restarts
- [ ] Múltiplas mensagens simultâneas não causam crash
