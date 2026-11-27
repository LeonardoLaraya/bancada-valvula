# Bancada de teste da válvula proporcional EPV2-5031F2

Interface local em português para selecionar um comando de 0 a 100%, aplicá-lo à válvula e acompanhar a tensão estimada. No PC, o modo simulado permite experimentar o painel. No Raspberry Pi 5, a aplicação Flask controla o canal A do L298N com PWM de hardware de 1 kHz no GPIO18 e habilitação no GPIO23.

**Estado da validação:** o painel e as sequências de controle foram testados em simulação. A tensão, a descarga do filtro e a resposta pneumática ainda precisam ser medidas na montagem. Comece com a válvula desconectada. Durante todo o ensaio, mantenha a cadeira vazia e o mecanismo fora do alcance de pessoas.

Use somente o processo deste repositório durante o ensaio. O sistema da cadeira em React/Node tem funções de movimento, como homing, e pode disputar os GPIOs. O painel da bancada comanda exclusivamente o sinal da EPV2. O percentual representa o duty cycle do PWM. A leitura de pressão é feita no manômetro.

**Roteiro:** [simular no PC](#modo-simulado) · [montar o circuito](#montagem) · [configurar o Pi](#instalação-no-raspberry-pi-5) · [medir e calibrar](#ensaio-com-multímetro-e-calibração) · [testar a válvula](#ensaio-com-a-válvula) · [diagnosticar falhas](#diagnóstico)

## Obter o projeto

Em cada computador, use Git com uma conta que tenha acesso ao repositório privado. Execute os comandos seguintes em um terminal:

```bash
git clone https://github.com/LeonardoLaraya/bancada-valvula.git
cd bancada-valvula
```

Se já tiver a pasta, abra um terminal nela. Também é possível copiar o projeto para o Pi por pendrive, deixando a pasta `.venv` no computador de origem. Crie um ambiente Python 3.11 ou superior em cada máquina.

## Modo simulado

Em Linux ou macOS, entre na pasta da aplicação e execute:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
chmod +x run.sh
./run.sh --mock --open-browser
```

No Windows com Python instalado:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m valvula --mock --open-browser
```

O indicativo **MODO SIMULADO** identifica a simulação. Os comandos ENA/PWM são registrados no terminal. A interface, a persistência de calibração e os tempos de parada são os mesmos nos dois modos. O simulador usa seu próprio arquivo de calibração. Sem `--mock`, erros de hardware encerram a inicialização.

**Primeiro teste no painel:** salve 8,7 V em **Tensão máxima medida** e selecione 50%. Confira a seleção de 4,35 V enquanto a saída aplicada continua em 0%. Clique em **Aplicar** e observe 50% e 4,35 V na saída. Clique em **PARAR E ZERAR** para acompanhar a descarga.

## Montagem

| Etapa | Material |
|---|---|
| Controle | Raspberry Pi 5, fonte USB-C própria e Raspberry Pi OS de 64 bits |
| Potência | Módulo L298N com terminais identificados, fonte regulada de 10 VCC e cabos presos em bornes |
| Filtro e ENA | 100 Ω em série com a saída, capacitor eletrolítico de 100 µF/25 V e dois resistores de 10 kΩ de ¼ W. Para o resistor de 100 Ω, use ½ W ou mais para dar margem à dissipação durante o PWM. |
| Medição | Multímetro em VCC e osciloscópio para verificar ondulação e picos |
| Ensaio com a válvula | EPV2-5031F2 com conector identificado, fonte separada de 24 VCC com limitação de corrente e fusível no positivo. O roteiro de bancada prevê 0,5 A como referência. Confirme o dimensionamento para a fonte, a fiação e a unidade. |
| Ensaio com ar | Ar filtrado, regulador de alimentação, manômetro na saída, mangueiras compatíveis e meio de bloquear e aliviar o ar |

### Pinagem e jumpers

Confira a numeração no conector e a continuidade do cabo com as fontes desligadas. As cores da tabela correspondem ao cabo previsto para a variante de entrada 0–10 V. [Válvula proporcional Werk Schott](https://werk-schott.com.br/produto/valvula-proporcional/)

| Origem | Destino | Função |
|---|---|---|
| Pi BCM18, pino físico 12 | IN1 | PWM de hardware, RP1 PWM0 canal 2 |
| Pi BCM23, pino físico 16 | ENA | Habilitação ativa em nível alto |
| Pi GND, pino físico 6 | GND comum | Referência dos sinais |
| GND comum | IN2 | Entrada fixa em nível baixo |
| Marrom, pino 1 da válvula | +24 V da fonte separada | Alimentação |
| Branco, pino 2 | Nó filtrado, após a validação | Comando de 0–10 V |
| Azul, pino 3 | GND comum | Retorno |
| Preto, pino 4 | Isolado individualmente | Monitor de 1–5 V, fora do ensaio |

Com as fontes desligadas, localize **ENA** na serigrafia do módulo e retire a pequena ponte que une ENA à alimentação lógica. Ligue BCM23 ao contato de sinal ENA e coloque **10 kΩ entre esse contato e GND**. O resistor mantém o canal desabilitado enquanto o Pi inicia ou libera o GPIO. Identifique o jumper do regulador de 5 V separadamente. As placas variam. Confira como a sua fornece os 5 V internos para a lógica com alimentação de potência de 10 V. O borne de 5 V do módulo deve ficar sem ligação com o Pi. O L298 aceita nível alto a partir de 2,3 V nas entradas e no enable, compatível com os sinais de 3,3 V do Pi. [Folha de dados do L298, tabela 4](https://www.st.com/resource/en/datasheet/l298.pdf)

```text
Pi 5 (fonte própria)               Módulo L298N
  pino 12 / GPIO18 --------------> IN1
  pino 16 / GPIO23 -----+--------> ENA   [jumper ENA removido]
                        |
                     [10 kΩ]
                        |
GND comum --------------+--------> IN2
Fonte 10 V (+) ------------------> VS    [borne de potência, às vezes "+12V"]
                                   5 V   [sem ligação ao Pi]
                                   OUT2  [livre]
                                   OUT1 ----[100 Ω]----o----- ponta V do multímetro
                                                       |      (depois: branco / 2)
                                                       |
                                                +------+------+
                                                |             |
                                              (+)             |
                                         [100 µF / 25 V]   [10 kΩ]
                                              (−)             |
                                                |             |
GND comum --------------------------------------+-------------+
   |------- pino 6 do Pi                 |------- GND do L298N
   |------- negativo da fonte 10 V       |------- COM do multímetro
   |------- negativo da fonte 24 V       '------- azul / 3 da válvula (etapa 2)

Fonte 24 V (+) ----[fusível]--------------------- marrom / 1 (etapa 2)
                                                  preto / 4 isolado
```

O positivo do capacitor fica no nó filtrado e o negativo no GND. A referência comum é necessária neste ensaio sem isolamento. Mantenha os positivos das fontes separados. **24 V nunca devem chegar ao Pi, aos GPIOs, ao filtro ou ao L298N desta montagem.** Deixe o canal B sem uso.

## Instalação no Raspberry Pi 5

Com os 10 V e 24 V desligados, abra um terminal na pasta do projeto no Pi e configure o ambiente. Os bindings Python de libgpiod 2.x são usados exclusivamente para o ENA. O PWM usa o sysfs do kernel.

```bash
sudo apt update
sudo apt install python3-venv python3-dev build-essential raspi-utils
python3 -m venv --system-site-packages .venv
.venv/bin/python -m pip install -r requirements-pi.txt
chmod +x run.sh scripts/*.sh
sudo ./scripts/setup_pi.sh
```

O script guarda uma cópia de `/boot/firmware/config.txt` antes de modificá-lo e acrescenta a diretiva `dtoverlay=pwm-2chan` em uma seção ativa. Pode ser executado novamente. Se encontrar uma configuração personalizada do overlay, solicita a conferência dos pinos. A reinicialização é manual.

```bash
sudo reboot
# Após voltar ao sistema, entre novamente na pasta bancada-valvula.
./scripts/check_hardware.sh
sudo ./run.sh
```

A verificação executa `pinctrl get 18`, lista `/sys/class/pwm/pwmchip*` e confere a função `PWM0_CHAN2`. O backend resolve o símbolo `rp1_pwm0` da árvore de dispositivos ativa, compara-o com o nó de cada chip e verifica a existência do canal 2. Um chip ausente, ambíguo, já ocupado ou com função de pino incorreta impede a operação. O número em `pwmchipN` depende do kernel. O overlay também configura um segundo pino PWM (normalmente GPIO19). Reserve esses recursos e BCM23 para a bancada. [Árvore de dispositivos do RP1](https://github.com/raspberrypi/linux/blob/rpi-6.12.y/arch/arm64/boot/dts/broadcom/rp1.dtsi) · [PWM no sysfs do Linux](https://docs.kernel.org/driver-api/pwm.html) · [Mapeamento de canais do Pi 5](https://github.com/Pioreactor/rpi_hardware_pwm)

Abra [o painel local](http://127.0.0.1:5000) no Pi. Para abrir automaticamente na sessão gráfica com Chromium instalado, use `./run.sh --open-browser` se seu usuário já tiver as permissões de hardware. Com sudo, use `sudo --preserve-env=DISPLAY,WAYLAND_DISPLAY,XDG_RUNTIME_DIR,XAUTHORITY ./run.sh --open-browser` na sessão do operador. O Chromium roda com a identidade do operador. Em um terminal sem sessão gráfica, abra a URL manualmente no Pi. Para trocar a porta, acrescente `--port 5080`.

## Atalho na tela do Raspberry

Depois de instalar o projeto e configurar o PWM, crie o atalho uma vez no terminal do usuário da área de trabalho:

```bash
cd ~/bancada-valvula
python3 scripts/instalar_atalho.py
```

Abra **Bancada da válvula** na área de trabalho. O terminal pode solicitar a senha do Raspberry e deve permanecer aberto enquanto o painel estiver em uso. O navegador abre em seguida. Se o navegador não abrir automaticamente, acesse `http://127.0.0.1:5000` no Raspberry. Para encerrar, use **PARAR E ZERAR** no painel e depois Ctrl+C no terminal. Se ocorrer um erro, o terminal mostra a mensagem e aguarda Enter antes de fechar.

## Ensaio com multímetro e calibração

Antes de energizar, confira a montagem:

- [ ] Válvula e ar desconectados, 24 V desligados e corte físico de energia acessível.
- [ ] Jumper ENA removido, resistor de 10 kΩ entre ENA e GND e GPIO23 de uso exclusivo da bancada.
- [ ] GPIO18 ligado ao IN1, IN2 no GND e resistor de 100 Ω entre OUT1 e o nó de medição.
- [ ] Positivo do capacitor no nó, negativo no comum e resistor de descarga em paralelo com o capacitor.
- [ ] Pontas do multímetro em **COM** e **V**, escala VCC. Ponta preta no comum, vermelha no nó filtrado. Nenhuma saída do L298N ligada ao Pi.

1. Ligue primeiro o Pi e inicie a aplicação em modo real. Confira **Desabilitado** e 0%. Ligue os 10 V da ponte e confirme tensão próxima de zero no multímetro. Se o painel indicar simulação, interrompa o ensaio físico.
2. Selecione cada percentual da tabela e clique em **Aplicar**. Arrastar a barra apenas atualiza a seleção. Aguarde a estabilização, leia o multímetro e anote a tensão. Observe também **PARAR E ZERAR** entre patamares e o retorno ao zero.
3. Em 100%, registre a tensão máxima **medida**. Se qualquer leitura superar 10 V, pare o ensaio, desligue a potência e investigue. Mantenha a válvula desconectada. O limite do formulário não limita a tensão física. Leituras não monotônicas ou zero residual significativo também exigem investigação.
4. Pare e confirme a descarga. Digite o valor de 100% em **Tensão máxima medida** e clique em **Salvar calibração**. O painel aceita 0,1–10,0 V e registra a data. Repita os patamares para comparar leitura e estimativa. O valor inicial de 10,0 V vem marcado como **não calibrado**.
5. Verifique a parada também ao fechar a aba em um patamar baixo. Acompanhe o watchdog no terminal e o retorno a aproximadamente 0 V no instrumento. Prossiga para a válvula somente após confirmar a faixa e a descarga.

| Seleção | Estimativa se a máxima medida for 8,70 V | Leitura no seu multímetro |
|---:|---:|---|
| 0% | 0,00 V | ______ V |
| 10% | 0,87 V | ______ V |
| 25% | 2,18 V | ______ V |
| 50% | 4,35 V | ______ V |
| 75% | 6,53 V | ______ V |
| 100% | 8,70 V | ______ V |

**Tensão estimada = tensão máxima medida × percentual / 100.** A queda interna do L298N, a carga, a tolerância dos componentes e a ondulação influenciam a tensão real. Um multímetro em VCC indica principalmente o valor médio. Para demonstrar que também os picos permanecem abaixo de 10 V, examine o nó com osciloscópio antes de conectar a válvula.

## Ensaio com a válvula

### Primeiro, com o ar fechado

1. Acione **PARAR E ZERAR**, confirme a descarga, desligue as fontes e mantenha a alimentação de ar fechada e a linha despressurizada.
2. Confira a pinagem por continuidade. Ligue marrom/1 ao +24 V pelo fusível, azul/3 ao comum e branco/2 ao nó filtrado. Isole preto/4 individualmente. A saída de monitoramento de 1–5 V e o OUT1 da ponte devem ficar afastados dos GPIOs de 3,3 V.
3. Ligue o Pi e confira **Desabilitado**, 0%. Energize a ponte em 10 V e depois a válvula em 24 V. Observe o display e o consumo. O catálogo lista 0,12 A em 24 V para as variantes EPV2-5031F2-LC/SB. Use a identificação da unidade para interpretar o consumo. [Catálogo Werk Schott, válvula proporcional](https://www.werk-schott.com.br/wp-content/uploads/2025/11/valvula_pneumaticas.pdf)
4. Com o multímetro entre branco e azul, aplique 5% e depois 10%, um patamar por vez. Compare com o ensaio sem carga. Pare, confira o retorno ao zero e investigue qualquer alarme, aquecimento ou corrente inesperada antes de admitir ar.

### Depois, com ar filtrado e manômetro

1. Com a linha despressurizada, ligue o regulador de alimentação a **IN** e o manômetro a **OUT**. Deixe a exaustão livre. Para a primeira leitura, mantenha o atuador da cadeira desconectado.
2. Comece em 0% e abra o ar gradualmente, com a pressão limitada pelo regulador. O roteiro usa cerca de **2 bar de alimentação** como ponto inicial, condicionado aos limites do conjunto. Para as variantes LC/SB citadas, o fabricante indica alimentação máxima de 1,0 MPa (10 bar) e alimentação mínima de 0,1 MPa (1 bar) acima da pressão de saída pretendida. Respeite o componente de menor pressão admissível. [Catálogo Werk Schott](https://www.werk-schott.com.br/wp-content/uploads/2025/11/valvula_pneumaticas.pdf)
3. Aplique 5%, depois 10%. Registre tensão no branco e pressão em OUT a cada patamar. Avance a 20% somente se a margem de alimentação permitir a pressão pretendida. Se a resposta saturar, investigue a alimentação e a exaustão antes de aumentar o comando.
4. Teste a parada no patamar baixo. Observe a queda de tensão e, separadamente, a indicação do manômetro. O filtro, a válvula e o volume pneumático têm tempos de resposta diferentes. Em caso de perda de controle, use o corte físico e alivie a linha.

### Ordem de desligamento

1. Acione **PARAR E ZERAR** e confirme **Desabilitado** e aproximadamente 0 V no multímetro.
2. Feche o ar, alivie a tubulação pelo dispositivo apropriado e confira a pressão no manômetro antes de tocar nas mangueiras.
3. Desligue os 24 V da válvula e depois os 10 V da ponte.
4. Encerre o servidor com **Ctrl+C** e desligue o Pi pelo sistema operacional.

## Parada e perda de comunicação

- **PARAR E ZERAR** envia 0% imediatamente. O estado fica **Parando** durante 1,5 s com a ponte ainda habilitada para descarregar o filtro. Em seguida, ENA vai a nível baixo e o painel indica **Desabilitado**. Aplicar 0% zera o comando com ENA habilitado.
- O navegador envia um heartbeat por segundo. Apenas a aba que aplicou o valor pode sustentá-lo. Após mais de 5 s sem seu heartbeat, o supervisor inicia a mesma parada e registra o motivo. Outra aba pode parar a qualquer momento. Uma aba suspensa também pode provocar o timeout.
- Após falha de comunicação, a interface oculta a leitura aplicada e, ao reconectar, solicita a parada. Retomar exige um novo clique em Aplicar. Comandos antigos perdem a validade após a parada.
- Ctrl+C, SIGTERM, encerramento normal e falhas internas passam pela rotina de parada. Falhas de hardware bloqueiam novas aplicações até a inspeção e o reinício. Se a escrita de 0% falhar, o controlador tenta baixar ENA imediatamente. Uma falha elétrica ou a interrupção forçada do processo pode impedir a sequência. Mantenha o corte físico de energia acessível. Zerar o sinal elétrico não confirma pressão zero.
- Este circuito L298N + filtro é um **teste provisório de bancada**. O watchdog depende do sistema operacional. A aplicação não substitui um circuito de segurança, uma saída analógica industrial nem a medição física do sinal.

## Diagnóstico

| Sintoma | O que verificar |
|---|---|
| GPIO18 aparece como entrada ou outra função | Confirme a seção ativa de config.txt, o overlay, reinicialização e conflitos com áudio ou outros overlays. Rode o script de verificação. |
| Nenhum chip correspondente | Confira `/sys/class/pwm`, o símbolo `/proc/device-tree/__symbols__/rp1_pwm0` e os links `device/of_node`. Use Raspberry Pi OS com kernel e firmware compatíveis. |
| GPIO ocupado, acesso negado ou `Device or resource busy` | Feche o programa que usa os pinos. Use as permissões adequadas. Um canal exportado por outro consumidor é recusado. Após interrupção forçada, desligue a potência e reinicie o Pi para limpar a exportação. |
| Falha ao importar gpiod | Use o Python da venv do projeto e instale `requirements-pi.txt`. A API requerida é libgpiod 2.x. |
| Saída sempre em zero | Confira o modo real, valor aplicado, ENA, alimentação lógica do módulo, 10 V em VS e ligação entre GPIO18 e IN1. Com a montagem desligada, inspecione o filtro quanto a curto ou capacitor invertido. |
| Saída permanece alta após parar | Corte a potência. Confira jumper ENA, resistor para GND, IN1 flutuante, função do GPIO18 e se ENA cai depois da descarga. |
| Tensão baixa ou oscilante | Confira escala VCC, valor dos resistores, alimentação sob carga, capacitor e GND comum. Observe frequência e ondulação no osciloscópio. Mantenha a fonte em 10 V, mesmo quando a queda do L298N reduzir o máximo medido. |
| Válvula energiza, mas a pressão não acompanha o comando | Meça branco em relação ao azul e marrom em relação ao azul. Confira variante, portas IN/OUT, pressão disponível e exaustão. |
| Pi reinicia, módulo aquece rapidamente ou há cheiro, fumaça ou ruído anormal | Corte a alimentação de potência e isole o ar. Com tudo desligado, procure inversão de polaridade, curto em OUT1, conexões frouxas ou retorno de tensão aos GPIOs. |
| Interface indica Erro ou Sem comunicação | Veja os eventos e o terminal. Se o estado físico estiver incerto, corte a potência. Corrija a causa e reinicie a partir de 0%. |
| Porta ocupada ou Chromium não abriu | Use `--port 5080` e abra a URL impressa no terminal do Pi. |
| JSON inválido | Com a bancada desenergizada, confira os três campos ou guarde o arquivo com outro nome para voltar ao padrão não calibrado. |

## Arquivos e API

| Arquivo | Responsabilidade |
|---|---|
| `valvula/hardware.py` | Contrato HardwareController e implementações RaspberryPiHardware / MockHardware |
| `valvula/control.py` | Estado, lock, prioridade de parada, watchdog e eventos |
| `valvula/config.py` | Validação de números finitos, estimativa e gravação atômica |
| `valvula/web.py`, `valvula/__main__.py` | Flask, servidor exclusivo de loopback, sinais e encerramento |
| `valvula/templates/`, `valvula/static/` | Painel responsivo em HTML, CSS e JavaScript locais |
| `scripts/`, `run.sh`, `tests/` | Instalação do overlay, diagnóstico, execução e testes |

A calibração fica em `data/calibracao.json` no hardware e `data/mock.json` na simulação. O arquivo é criado ao salvar a primeira calibração. Os campos são `max_voltage`, `frequency` (padrão 1000 Hz) e `calibrated_at` (ISO 8601, UTC). Para ajustar a frequência intencionalmente, pare o servidor, edite o JSON e reinicie. A opção `--config CAMINHO` permite escolher outro arquivo. O duty e o estado do canal existem apenas na memória.

| Método e caminho | Corpo JSON | Resultado |
|---|---|---|
| GET /api/state | — | Estado, calibração e eventos |
| POST /api/heartbeat | `{"client":"identificador-da-aba"}` | Estado e versão corrente do comando (`epoch`) |
| POST /api/apply | `{"client":"identificador-da-aba","epoch":"valor-recebido","percent":50}` | Saída aplicada após validação |
| POST /api/stop | `{}` | Comando zerado e descarga iniciada |
| POST /api/calibration | `{"max_voltage":8.7}` | Calibração salva e estimativas atualizadas |

Use o executável do projeto em processo único. A aplicação coordena os pinos em memória e rejeita a posse simultânea da linha ENA. O servidor escuta em 127.0.0.1, com debug e recarga desativados.

## Testes de software

```bash
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m pytest -q
.venv/bin/ruff check .
node --check valvula/static/painel.js  # opcional, requer Node.js
bash -n run.sh && bash -n scripts/setup_pi.sh && bash -n scripts/check_hardware.sh
```

O pytest exercita mock, API, limites, falhas de E/S, concorrência, persistência, watchdog e identificação de chips com uma árvore de dispositivos de teste.

Na verificação de entrega em Windows, os 44 testes pytest passaram, incluindo a parada por SIGINT e SIGTERM em mock e a idempotência da edição de um config.txt temporário. Ruff, a análise sintática do JavaScript e a análise Bash dos scripts passaram. No Chromium, foram exercitados seleção sem aplicar, calibração, parada, fechamento da aba, perda e recuperação de comunicação e apresentação em larguras de 360, 800 e 1280 px. O terminal registrou o encerramento por Ctrl+C com PWM zero, descarga e ENA baixo.

As verificações de software não medem os pinos, a descarga real, a tensão de pico ou a pressão. A validação física é o ensaio com os instrumentos e a montagem descritos acima.
