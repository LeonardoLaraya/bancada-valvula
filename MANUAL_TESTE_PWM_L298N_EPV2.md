# Manual de teste — Raspberry Pi 5, L298N e EPV2-5031F2

> **BLOQUEIO DE SEGURANÇA:** o código atualmente presente neste repositório **não está pronto para ser ligado à válvula proporcional**. Leia a seção [Estado atual do software](#estado-atual-do-software) antes de energizar qualquer componente.

## 1. Objetivo

Este ensaio usa o Raspberry Pi 5 para gerar PWM, uma ponte H L298N alimentada em 10 V e um filtro RC para produzir uma tensão média destinada à entrada 0–10 V da válvula proporcional EPV2-5031F2.

O conjunto L298N + filtro é apenas uma montagem provisória de bancada. Não substitui um conversor PWM/0–10 V industrial, isolamento galvânico, parada de emergência física ou validação de segurança.

## 2. Componentes necessários

- Raspberry Pi 5 e fonte USB-C apropriada.
- Módulo L298N com identificação legível de `ENA`, `IN1`, `IN2`, `OUT1`, `GND`, alimentação de potência e jumper do regulador de 5 V.
- Fonte regulada de 10 VCC para a potência do L298N.
- Fonte regulada de 24 VCC para a EPV2, preferencialmente com limitação de corrente.
- Válvula EPV2-5031F2 e cabo/conector correto.
- Multímetro em bom estado.
- Resistor de 100 ohms, no mínimo 1/4 W.
- Capacitor eletrolítico de 100 microfarads, no mínimo 25 V.
- Dois resistores de 10 quilohms, no mínimo 1/4 W:
  - um para descarregar o filtro;
  - um para manter `ENA` desligado durante a inicialização.
- Fusível de aproximadamente 0,5 A no ramo de 24 V da válvula.
- Cabos, bornes e conectores firmes; não usar fios apenas encostados.
- Filtro/regulador pneumático, manômetro e mangueiras compatíveis.

## 3. Identificação dos sinais

### Raspberry Pi 5

| Função planejada | BCM | Pino físico |
|---|---:|---:|
| PWM para `IN1` | GPIO18 | 12 |
| Habilitação `ENA` | GPIO23 | 16 |
| Terra | GND | 6 |

Os GPIOs trabalham com 3,3 V e não toleram 5 V, 10 V ou 24 V.

### L298N — canal A

| Terminal | Função neste teste |
|---|---|
| `ENA` | Habilita/desabilita o canal A |
| `IN1` | Recebe PWM do GPIO18 |
| `IN2` | Permanece ligado ao GND |
| `OUT1` | Alimenta o filtro RC |
| `OUT2` | Não utilizado |
| `GND` | Terra comum |
| `12V`, `VS` ou equivalente | Recebe +10 V da fonte de teste |
| `5V` | Não conectar ao Raspberry |

Há normalmente dois jumpers diferentes:

- **Jumper `ENA`: remover**, pois `ENA` será controlado pelo GPIO23.
- **Jumper do regulador `5V-EN`:** só manter se o manual da placa permitir que o regulador lógico seja alimentado pela entrada de 10 V. Não confundir esse jumper com `ENA`.

### EPV2-5031F2

| Pino | Cor do cabo original | Função |
|---:|---|---|
| 1 | Marrom | +24 VCC |
| 2 | Branco | Entrada analógica 0–10 V |
| 3 | Azul | 0 V/comum |
| 4 | Preto | Monitor analógico 1–5 V |

As cores só podem ser consideradas válidas no cabo correto. Confirme continuidade e numeração antes de energizar. O fio preto permanece isolado neste teste.

## 4. Esquema elétrico

### Controle e alimentação da ponte

```text
Raspberry Pi 5                       L298N
------------------------------------------------
GPIO18, pino 12 -------------------- IN1
GPIO23, pino 16 -------------------- ENA
GND, pino 6 ------------------------ GND
                                      IN2 ---- GND

Fonte 10 V (+) --------------------- VS/12V
Fonte 10 V (-) --------------------- GND

OUT2 -------------------------------- não conectar
5V do L298N ------------------------- não conectar ao Pi
```

Instale um resistor de 10 kohms entre `ENA` e GND. Ele mantém o canal desabilitado enquanto o Raspberry inicia ou está desligado.

### Filtro de saída

```text
OUT1 do L298N ---- 100 ohms ----+---- SIG_0_10V
                                |
                                +---- (+) 100 uF / 25 V
                                |          (-)
                                |           |
                                +---- 10 kohms
                                |           |
GND comum ----------------------+-----------+---- COMUM
```

- O resistor de 100 ohms não possui polaridade.
- O capacitor eletrolítico possui polaridade.
- Positivo do capacitor em `SIG_0_10V`.
- Negativo do capacitor no `COMUM`.
- A faixa impressa no corpo do capacitor normalmente identifica o terminal negativo.

### Medição inicial

```text
Multímetro vermelho ---- SIG_0_10V
Multímetro preto ------- COMUM
Escala ----------------- tensão contínua (VCC)
```

### Ligação posterior da válvula

Só faça esta etapa depois de validar toda a faixa com multímetro.

```text
Fonte 24 V (+) -- fusível 0,5 A ------- marrom/pino 1
Fonte 24 V (-) ------------------------- azul/pino 3
SIG_0_10V ------------------------------ branco/pino 2
Preto/pino 4 --------------------------- isolado
```

Para esta montagem não isolada, os seguintes pontos precisam formar o mesmo comum:

- GND do Raspberry;
- GND do L298N;
- negativo da fonte de 10 V;
- negativo da fonte de 24 V;
- azul/pino 3 da EPV2;
- negativo do capacitor.

Nunca una os positivos das fontes.

## 5. Parte pneumática

- Use somente ar comprimido filtrado.
- Ligue a alimentação pneumática à porta `IN`.
- Ligue manômetro/atuador à porta `OUT`.
- Não obstrua a exaustão.
- A pressão máxima de alimentação especificada é 1,0 MPa, aproximadamente 10 bar.
- Comece o ensaio com pressão de alimentação baixa, aproximadamente 2 bar.
- Mantenha pessoas afastadas das partes móveis.
- Não sente na cadeira durante desenvolvimento, calibração ou diagnóstico.
- Feche a alimentação e alivie a pressão antes de modificar mangueiras.

## 6. Estado atual do software

O repositório atual é uma aplicação React + Node/Express, mas não corresponde ao controlador de teste definido para GPIO18/GPIO23.

### Divergências críticas encontradas

1. `back/src/Services/gpioService.js` usa GPIO12, pino físico 32, como PWM; o projeto definido usa GPIO18, pino físico 12.
2. O PWM atual é implementado com `setTimeout` e período de 20 ms, isto é, cerca de 50 Hz. Não é PWM de hardware de 1 kHz.
3. GPIO23 já está atribuído à `valvula4`; portanto não controla `ENA`.
4. Não existe controle separado de `ENA`.
5. O código fixa `gpiochipOpen(4)`, que pode mudar conforme kernel e configuração do Raspberry Pi 5.
6. Se GPIO falhar, o backend entra silenciosamente em modo simulado e continua aceitando comandos.
7. Não existe calibração da tensão máxima nem exibição de volts estimados.
8. Não existe heartbeat para zerar a saída se a tela ou comunicação falhar.
9. A tela representa o comando como “peso em kg” e envia o mesmo número como percentual PWM.
10. O botão de aplicar em `Funcionalidades.tsx` também envia comandos para encosto e limitador.
11. O botão de ligar/desligar executa `homing`, energizando válvulas de retração por aproximadamente 10 segundos.
12. A emergência é apenas por software; não existe parada física independente.

### Consequência

**Não rode a interface atual com a cadeira, L298N ou válvulas conectadas.** Primeiro deve ser criada/corrigida uma tela exclusiva de teste, sem homing, encosto ou limitador, e o backend deve implementar PWM de hardware no GPIO18 e `ENA` no GPIO23.

## 7. Como instalar e abrir o projeto atual — somente simulação

Estas instruções servem apenas para visualizar a aplicação sem hardware.

### Requisitos

- Git.
- Node.js compatível com Vite 7; verifique com `node --version`.
- npm.

### Clone e instalação

```bash
git clone <URL-DO-REPOSITORIO>
cd Projeto-Cadeira-Software
npm run install:all
```

### Executar

```bash
npm run dev
```

O backend usa normalmente:

```text
http://localhost:4000
```

O frontend Vite normalmente abre em:

```text
http://localhost:5173
```

A página de funcionalidades é:

```text
http://localhost:5173/funcionalidades
```

O terminal do backend precisa indicar claramente que está em simulação. Não considere uma resposta HTTP de sucesso como comprovação de acionamento físico.

## 8. Comportamento necessário da interface corrigida

A versão própria para o teste deve possuir:

- barra de 0 a 100%;
- seleção sem aplicação imediata;
- botão `Aplicar` exclusivo para o PWM;
- botão `PARAR E ZERAR` sempre disponível;
- percentual selecionado e percentual aplicado separados;
- tensão estimada claramente identificada como estimativa;
- campo de calibração da tensão máxima medida;
- estado `Desabilitado`, `Habilitado`, `Parando`, `Erro` ou `Simulação`;
- início sempre em 0% e `ENA` desligado;
- PWM de hardware em GPIO18;
- `ENA` em GPIO23;
- heartbeat que pare a saída se a interface desaparecer;
- erro de GPIO bloqueante; nunca fallback silencioso para simulação em execução real;
- nenhuma chamada de homing, encosto, limitador ou outras válvulas.

A estimativa deve usar:

```text
V_estimado = V_max_medido * percentual / 100
```

Exemplo: se 100% produzir 8,7 V, então 50% deve ser mostrado como aproximadamente 4,35 V.

## 9. Procedimento de teste com multímetro

### Preparação

1. Desligue todas as fontes.
2. Desconecte a válvula e toda a parte pneumática.
3. Confira o GPIO pelo número BCM e pelo pino físico.
4. Remova apenas o jumper `ENA`.
5. Monte o resistor de 10 kohms de `ENA` para GND.
6. Monte o filtro RC e confira a polaridade do capacitor.
7. Coloque o multímetro entre `SIG_0_10V` e `COMUM`.
8. Confirme que o fio preto da válvula está isolado.

### Energização

1. Ligue somente o Raspberry.
2. Inicie a interface corrigida.
3. Confirme 0% e estado desabilitado.
4. Ligue a fonte de 10 V do L298N.
5. Confirme novamente que a saída está próxima de 0 V.

### Pontos de medição

Aplique um valor por vez e aguarde a estabilização:

| PWM | Tensão ideal se `Vmax=10 V` | Anotar tensão real |
|---:|---:|---:|
| 0% | 0,00 V | ____ V |
| 10% | 1,00 V | ____ V |
| 25% | 2,50 V | ____ V |
| 50% | 5,00 V | ____ V |
| 75% | 7,50 V | ____ V |
| 100% | 10,00 V | ____ V |

O L298N possui queda interna, portanto 100% provavelmente produzirá menos de 10 V. Isso não é necessariamente defeito.

Interrompa o teste se:

- a saída ultrapassar 10,0 V;
- a tensão não responder ao percentual;
- o Raspberry reiniciar;
- o L298N, capacitor ou fios aquecerem rapidamente;
- houver cheiro, ruído, fumaça ou instabilidade;
- a interface indicar modo simulado;
- `ENA` permanecer ativo após `Parar`.

Depois de cada ponto, use `Parar e zerar` e confirme que a saída retorna para perto de 0 V.

### Calibração

1. Anote a tensão real em 100%.
2. Insira esse valor como tensão máxima medida.
3. Repita 25%, 50% e 75%.
4. Compare medido e estimado.
5. Para este protótipo, diferenças grandes ou comportamento não linear impedem o teste com a válvula.

## 10. Teste elétrico com a válvula

Somente depois de aprovar o teste anterior:

1. Pare e desligue tudo.
2. Ligue marrom ao +24 V através do fusível.
3. Ligue azul ao comum.
4. Ligue branco à saída filtrada.
5. Deixe preto isolado.
6. Mantenha a alimentação pneumática fechada.
7. Ligue o Raspberry e confirme 0%.
8. Ligue a fonte de 10 V.
9. Ligue os 24 V da válvula.
10. Verifique o display e o consumo; o valor nominal publicado é cerca de 0,12 A em 24 V.
11. Aplique somente 5% e depois 10%, verificando tensão e comportamento.
12. Pare e confirme retorno para 0 V.

Não avance se a válvula indicar erro, aquecer anormalmente ou consumir corrente muito acima do esperado.

## 11. Teste pneumático inicial

1. Comece com comando em 0%.
2. Ajuste a alimentação pneumática para aproximadamente 2 bar.
3. Confirme todas as conexões e a exaustão.
4. Aplique 5%, depois 10% e depois 20%.
5. Observe o manômetro; não coloque mãos no mecanismo.
6. Não aplique 100% com pessoa ou carga na cadeira.
7. Teste o botão de parada em baixa pressão.
8. Confirme que o comportamento após falha de software é aceitável antes de aumentar a pressão.

## 12. Ordem de desligamento

1. Acione `Parar e zerar`.
2. Confirme aproximadamente 0 V no multímetro.
3. Feche o ar e alivie a tubulação.
4. Desligue os 24 V da válvula.
5. Desligue os 10 V do L298N.
6. Encerre o backend.
7. Desligue o Raspberry pelo sistema operacional.

## 13. O que pode queimar

### Raspberry Pi

Pode ser danificado por:

- aplicar 5 V, 10 V ou 24 V em qualquer GPIO;
- conectar o terminal 5 V do L298N ao GPIO ou à alimentação do Pi;
- inverter GND e sinal;
- conectar `OUT1` ao Raspberry;
- conectar o fio preto de 1–5 V diretamente ao GPIO;
- curto entre dois GPIOs configurados como saída;
- conectar/desconectar fios energizados.

### Entrada analógica da válvula

Pode ser danificada por:

- ligar 24 V ao fio branco;
- trocar branco e marrom;
- ultrapassar 10 V na entrada;
- usar conector com pinagem diferente sem verificar continuidade;
- picos causados por fiação longa, frouxa ou sem referência comum.

### L298N

Pode ser danificado ou superaquecer por:

- curto em `OUT1`;
- alimentação invertida;
- confundir a entrada de potência com o terminal de 5 V;
- retirar o jumper lógico sem fornecer alimentação lógica apropriada;
- operar sem ventilação enquanto aquece;
- fios soltos encostando no dissipador ou em outros terminais.

### Capacitor

Um eletrolítico invertido pode aquecer, vazar ou romper. Nunca energize antes de conferir positivo, negativo e tensão nominal.

### Parte pneumática

Riscos incluem soltura de mangueira, movimento inesperado, esmagamento e queda rápida de pressão. Não faça ensaio com pessoa na cadeira.

## 14. Diagnóstico de falhas

### Interface abre, mas a tensão não muda

- Verifique se o backend entrou em simulação.
- Verifique se o PWM real está no GPIO correto.
- Verifique `ENA`, `IN1`, `IN2` e GND comum.
- Verifique a fonte de 10 V.
- Verifique se o jumper removido foi `ENA`, não o jumper do regulador lógico.

### Saída fica sempre em 0 V

- `ENA` pode estar baixo.
- O L298N pode estar sem alimentação lógica.
- `IN1` pode estar no pino errado.
- O backend pode estar em simulação.
- O filtro pode estar em curto ou o capacitor invertido/danificado.

### Saída fica sempre alta

- PWM preso em 100%.
- GPIO errado ou configuração PWM incorreta.
- `IN1` flutuando.
- Falha na sequência de parada.

### Valor medido é menor que o esperado

- Queda interna normal do L298N.
- Fonte de 10 V abaixo do nominal.
- Carga do filtro/válvula.
- Resistor com valor errado.
- Multímetro em escala ou modo incorreto.

Use o valor real em 100% para calibrar; nunca compense elevando a fonte acima de 10 V sem reavaliar os picos aplicados à válvula.

### Valor oscila

- PWM por software com jitter.
- Frequência inadequada.
- Falta ou mau contato no capacitor.
- GND ruim.
- Fonte instável.
- Aplicação executando outras rotas/atuadores simultaneamente.

### Válvula liga, mas não regula pressão

- Entrada pneumática e saída invertidas.
- Falta de pressão de alimentação.
- Comando branco sem referência ao azul.
- Alimentação de 24 V ausente.
- Filtro produzindo tensão diferente da indicada.
- Exaustão obstruída.
- Modelo/pinagem diferente da identificada.

### Raspberry reinicia ou trava

- Ruído ou retorno elétrico do circuito de potência.
- Fonte inadequada.
- GND mal conectado.
- Tensão indevida atingindo GPIO.

Desligue imediatamente a ponte e a válvula. Não continue tentando por software.

## 15. Limitações conhecidas

- Multímetro mostra principalmente o valor médio, não revela todos os picos e ripple; osciloscópio é superior.
- O L298N não é um DAC e sua queda depende de carga e temperatura.
- O filtro RC reduz ripple, mas não torna o conjunto uma saída industrial calibrada.
- O Linux não é um controlador de segurança em tempo real.
- Botão na tela não substitui chave física que corte energia/ar.
- Perda de energia pode produzir comportamento pneumático diferente de uma parada comandada.
- A EPV possui seu próprio erro, histerese e limite de pressão; mais resolução de PWM não garante mais precisão mecânica.

## 16. Checklist antes de qualquer teste real

- [ ] Software corrigido para GPIO18 PWM de hardware.
- [ ] GPIO23 exclusivo para `ENA`, sem conflito com `valvula4`.
- [ ] Tela exclusiva de teste, sem homing nem outros movimentos.
- [ ] Falha de GPIO bloqueia o modo real.
- [ ] PWM inicia em 0%.
- [ ] `ENA` inicia baixo.
- [ ] Resistor de 10 kohms instalado em `ENA`.
- [ ] Filtro 100 ohms + 100 uF/25 V + 10 kohms montado.
- [ ] Polaridade do capacitor confirmada.
- [ ] Válvula desconectada durante calibração inicial.
- [ ] Multímetro conectado corretamente.
- [ ] Fonte do L298N ajustada para 10 V.
- [ ] Terminal 5 V do L298N não conectado ao Pi.
- [ ] Toda a faixa medida e abaixo de 10 V.
- [ ] Pinagem do conector da válvula confirmada.
- [ ] Fio preto isolado.
- [ ] Fusível instalado no ramo de 24 V.
- [ ] Pressão inicial limitada.
- [ ] Nenhuma pessoa na cadeira.
- [ ] Existe meio físico de cortar energia e ar.

