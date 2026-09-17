# trader-bot

Bot de day trade algorítmico para operar mini índice (WIN) na B3, via
**XP / Profit Pro** (ProfitDLL da Nelogica), com estratégia de
cruzamento de médias móveis.

## ⚠️ Aviso de risco

Este bot pode enviar ordens reais com dinheiro real quando `MODE=real`.
Trading algorítmico envolve risco de perda financeira, incluindo perdas
maiores que o capital investido em derivativos como WIN/WDO. Nada aqui
é recomendação de investimento. Você é o único responsável por validar
a estratégia, configurar limites de risco adequados e monitorar o bot
enquanto ele opera. **Nunca rode em conta real sem antes validar
exaustivamente em modo simulado e no ambiente de simulação da
Nelogica.**

## Como funciona

O projeto separa três camadas para permitir testar a lógica sem
depender do Windows nem de uma conta real:

- `trader_bot/strategy.py` — lógica pura de sinal (cruzamento de
  médias móveis). Sem dependências externas, 100% testável.
- `trader_bot/risk_manager.py` — controles de risco: posição máxima,
  perda máxima diária, stop-loss e take-profit em pontos. Toda ordem
  passa por aqui antes de ser enviada.
- `trader_bot/market_data.py` + `trader_bot/broker.py` — interfaces de
  dados de mercado e execução. `SimulatedMarketData`/`SimulatedBroker`
  rodam em qualquer lugar (inclusive Linux/CI) com preços sintéticos.
  `trader_bot/profit_dll_gateway.py` implementa as versões reais via
  ProfitDLL e **só pode ser importado no Windows**.
- `trader_bot/bot.py` — orquestra tudo, escolhendo simulado ou real
  conforme `MODE` no `.env`.

## Setup

```bash
cd trader-bot
python -m venv venv
venv\Scripts\activate        # Windows
# ou: source venv/bin/activate   # Linux/Mac (só funciona em modo simulado)
pip install -r requirements.txt
cp .env.example .env
```

### Rodando em modo simulado (recomendado para começar, roda em qualquer SO)

```bash
pytest                 # roda os testes unitários de estratégia e risco
python -m trader_bot.bot
```

Isso usa um feed de preços sintético (random walk) e uma corretora
simulada — nenhuma ordem real é enviada, nenhum requisito do Windows
ou da ProfitDLL. Serve para validar a lógica de entrada/saída e os
limites de risco.

### Rodando em modo real (Windows + Profit Pro obrigatórios)

Pré-requisitos:

1. Conta XP com Profit Pro habilitado.
2. `ProfitDLL64.dll` fornecida pela Nelogica/XP (peça ao suporte da XP
   ou baixe pelo canal oficial da Nelogica), copiada para dentro da
   pasta `trader-bot/`.
3. Chave de ativação da API (activation key) fornecida pela
   Nelogica/XP para sua conta.
4. **Leia o `Manual ProfitDLL`** (PDF fornecido pela Nelogica,
   correspondente à versão exata da sua DLL) e confira cada assinatura
   de função em `trader_bot/profit_dll_gateway.py` contra o manual —
   os nomes de função e a ordem dos parâmetros documentados ali usam a
   API pública, mas variam entre versões da DLL. Isso está marcado com
   comentários `TODO(verify)` no código.
5. Teste primeiro no **ambiente de simulação da Nelogica** (dados e
   execução simulados, mas usando a infraestrutura real da API) antes
   de qualquer conta real.

Depois de validar tudo isso, edite `.env`:

```
MODE=real
PROFIT_DLL_PATH=ProfitDLL64.dll
PROFIT_ACTIVATION_KEY=sua_chave
PROFIT_LOGIN=seu_login_xp
PROFIT_PASSWORD=sua_senha
TICKER=WINZ25   # atualize para o vencimento vigente
```

E rode, no Windows, com o Profit Pro instalado:

```bash
python -m trader_bot.bot
```

## Configuração da estratégia (`.env`)

| Variável | Descrição | Padrão |
|---|---|---|
| `MODE` | `simulated` ou `real` | `simulated` |
| `TICKER` | Contrato negociado | `WINFUT` |
| `MA_FAST` / `MA_SLOW` | Períodos das médias móveis | `9` / `21` |
| `ORDER_QTY` | Contratos por ordem | `1` |
| `MAX_POSITION` | Posição máxima absoluta permitida | `1` |
| `MAX_DAILY_LOSS` | Perda diária máxima (P&L, número negativo) antes de parar | `-500` |
| `STOP_LOSS_POINTS` | Stop-loss por posição, em pontos | `500` |
| `TAKE_PROFIT_POINTS` | Take-profit por posição, em pontos | `1000` |

Comece sempre com `MAX_POSITION=1` e `ORDER_QTY=1` até ter confiança
total no comportamento do bot.

## Alternativa: estratégia nativa dentro do Profit (NTSL)

Além do bot Python (que roda fora do Profit, via ProfitDLL), este
projeto também inclui `ntsl/ma_crossover.ntl`: a mesma lógica de
cruzamento de médias móveis (9/21), escrita em NTSL, para rodar
**dentro** do módulo Estrategista do próprio Profit Pro.

Como usar:

1. Abra Profit Pro > Ferramentas > Estrategista > Nova Estratégia.
2. Cole o conteúdo de `ntsl/ma_crossover.ntl` e compile.
3. Se houver erro de compilação, a sintaxe NTSL pode ter mudado na sua
   versão do Profit — ajuste os nomes de função conforme o erro indicar
   (a referência NTSL fica disponível no menu de Ajuda do Profit).
4. Configure ativo, quantidade e stop na própria tela do Estrategista e
   salve. É esse passo que gera o arquivo de configuração da estratégia
   dentro do Profit (`.psf`) — ele não deve ser editado manualmente.
5. Teste na conta simulador do Profit antes de qualquer conta real.

**Escolha um caminho só.** Rodar o bot Python (`MODE=real`) e a
estratégia NTSL dentro do Profit ao mesmo tempo, no mesmo ativo e
conta, faz os dois enviarem ordens de forma independente — você
acabaria com posição dobrada ou conflitante.

## Limitações conhecidas

- As assinaturas ctypes em `profit_dll_gateway.py` são baseadas na
  API publicamente documentada da ProfitDLL, mas **não foram testadas
  contra uma DLL real** neste ambiente (que é Linux, sem acesso ao
  Profit Pro). Trate esse arquivo como um ponto de partida a ser
  validado e ajustado por você contra o manual da sua versão antes de
  usar em modo real.
- O gerenciamento de posição em `risk_manager.py` assume no máximo uma
  posição por vez neste ticker (não faz média ponderada de múltiplos
  preços de entrada). Adequado para um bot de 1 contrato; revise antes
  de aumentar `MAX_POSITION`.
- Sem reconexão automática em caso de queda da conexão com a
  ProfitDLL — monitore o bot enquanto ele roda.
