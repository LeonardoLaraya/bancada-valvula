# Bancada de teste da válvula proporcional

Painel local em português para ensaiar o sinal de comando da EPV2-5031F2 com Raspberry Pi 5 e L298N. A primeira carga é um multímetro. O painel mostra o percentual comandado e estima a tensão a partir da calibração. A bancada não mede tensão, pressão ou posição. Use-a fora do equipamento em operação, sem pessoas ou carga mecânica expostas a movimento.

## Montagem

Use um Pi 5 com sua fonte própria e Raspberry Pi OS de 64 bits, uma ponte L298N com canal A, fonte de bancada de 10 VCC, multímetro em tensão contínua, cabos, um resistor de 100 Ω, dois resistores de 10 kΩ e um capacitor eletrolítico de 100 µF/25 V. Para a segunda etapa, use a válvula e uma fonte de 24 VCC separada. Confira a identificação da variante e a orientação do conector na unidade. [Válvula proporcional Werk Schott](https://werk-schott.com.br/produto/valvula-proporcional/)

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

Fonte 24 V (+) ---------------------------------- marrom / 1 (etapa 2)
                                                  preto / 4 isolado
```

O positivo do capacitor fica no nó filtrado e o negativo no GND. A referência comum é necessária neste ensaio sem isolamento. Mantenha os positivos das fontes separados. **24 V nunca devem chegar ao Pi, aos GPIOs, ao filtro ou ao L298N desta montagem.** Deixe o canal B sem uso.

## Instalação no Raspberry Pi 5

Copie a pasta `bancada-valvula` inteira para o Pi. No terminal, dentro dela, configure o ambiente. Requer Python 3.11 ou superior. Os bindings Python de libgpiod 2.x são usados exclusivamente para o ENA. O PWM usa o sysfs do kernel.

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

## Ensaio com multímetro e calibração

1. Deixe a válvula desconectada e a fonte de 24 V desligada. Inspecione a montagem desenergizada. Coloque a ponta COM no comum e a ponta V no nó filtrado. Energize a bancada. Confirme **Desabilitado**, PWM 0% e tensão próxima de zero. Se houver tensão inesperada, desligue a alimentação de potência e confira a fiação.
2. Selecione cada percentual da tabela e clique em **Aplicar**. Arrastar a barra apenas atualiza a seleção. Aguarde a estabilização, leia o multímetro e anote a tensão. Observe também **PARAR E ZERAR** entre patamares e o retorno ao zero.
3. Em 100%, registre a tensão máxima **medida**. Se qualquer leitura superar 10 V, pare o ensaio, desligue a potência e investigue. Mantenha a válvula desconectada. O limite do formulário não limita a tensão física. Leituras não monotônicas ou zero residual significativo também exigem investigação.
4. Pare e confirme a descarga. Digite o valor de 100% em **Tensão máxima medida** e clique em **Salvar calibração**. O painel aceita 0,1–10,0 V e registra a data. Repita os patamares para comparar leitura e estimativa. O valor inicial de 10,0 V vem marcado como **não calibrado**.
5. Somente depois da verificação, desligue as fontes, confirme o zero, conecte o branco ao nó e o azul ao comum. Conecte o marrom ao +24 V e mantenha o preto isolado. Reinicie com a saída desabilitada e recomece em 0%. Confira a tensão com a carga conectada. Qualquer ensaio pneumático exige controlar separadamente a alimentação e a descarga de ar.

| Seleção | Estimativa se a máxima medida for 8,70 V | Leitura no seu multímetro |
|---:|---:|---|
| 0% | 0,00 V | ______ V |
| 25% | 2,18 V | ______ V |
| 50% | 4,35 V | ______ V |
| 75% | 6,53 V | ______ V |
| 100% | 8,70 V | ______ V |

**Tensão estimada = tensão máxima medida × percentual / 100.** A queda interna do L298N, a carga, a tolerância dos componentes e a ondulação influenciam a tensão real. Um multímetro em VCC indica principalmente o valor médio. Para demonstrar que também os picos permanecem abaixo de 10 V, examine o nó com osciloscópio antes de conectar a válvula.

## Parada e perda de comunicação

- **PARAR E ZERAR** envia 0% imediatamente. O estado fica **Parando** durante 1,5 s com a ponte ainda habilitada para descarregar o filtro. Em seguida, ENA vai a nível baixo e o painel indica **Desabilitado**. Aplicar 0% zera o comando com ENA habilitado.
- O navegador envia um heartbeat por segundo. Apenas a aba que aplicou o valor pode sustentá-lo. Após mais de 5 s sem seu heartbeat, o supervisor inicia a mesma parada e registra o motivo. Outra aba pode parar a qualquer momento. Uma aba suspensa também pode provocar o timeout.
- Após falha de comunicação, a interface oculta a leitura aplicada e, ao reconectar, solicita a parada. Retomar exige um novo clique em Aplicar. Comandos antigos perdem a validade após a parada.
- Ctrl+C, SIGTERM, encerramento normal e falhas internas passam pela rotina de parada. Falhas de hardware bloqueiam novas aplicações até a inspeção e o reinício. Se a escrita de 0% falhar, o controlador tenta baixar ENA imediatamente. Uma falha elétrica ou a interrupção forçada do processo pode impedir a sequência. Mantenha o corte físico de energia acessível. Zerar o sinal elétrico não confirma pressão zero.
- Este circuito L298N + filtro é um **teste provisório de bancada**. O watchdog depende do sistema operacional. A aplicação não substitui um circuito de segurança, uma saída analógica industrial nem a medição física do sinal.

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

## Diagnóstico

| Sintoma | O que verificar |
|---|---|
| GPIO18 aparece como entrada ou outra função | Confirme a seção ativa de config.txt, o overlay, reinicialização e conflitos com áudio ou outros overlays. Rode o script de verificação. |
| Nenhum chip correspondente | Confira `/sys/class/pwm`, o símbolo `/proc/device-tree/__symbols__/rp1_pwm0` e os links `device/of_node`. Use Raspberry Pi OS com kernel e firmware compatíveis. |
| GPIO ocupado, acesso negado ou `Device or resource busy` | Feche o programa que usa os pinos. Use as permissões adequadas. Um canal exportado por outro consumidor é recusado. Após interrupção forçada, desligue a potência e reinicie o Pi para limpar a exportação. |
| Falha ao importar gpiod | Use o Python da venv do projeto e instale `requirements-pi.txt`. A API requerida é libgpiod 2.x. |
| Tensão fixa ou diferente da esperada | Confira GND comum, jumper ENA, IN2, posição das pontas, polaridade do capacitor e alimentação lógica do módulo. Confira o valor **aplicado** e meça novamente com a válvula desconectada. |
| Interface indica Erro ou Sem comunicação | Veja os eventos e o terminal. Se o estado físico estiver incerto, corte a potência. Corrija a causa e reinicie a partir de 0%. |
| Porta ocupada ou Chromium não abriu | Use `--port 5080` e abra a URL impressa no terminal do Pi. |
| JSON inválido | Com a bancada desenergizada, confira os três campos ou guarde o arquivo com outro nome para voltar ao padrão não calibrado. |

## Testes de software

```bash
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m pytest -q
.venv/bin/ruff check .
node --check valvula/static/painel.js  # opcional, requer Node.js
bash -n run.sh && bash -n scripts/setup_pi.sh && bash -n scripts/check_hardware.sh
```

O pytest exercita mock, API, limites, falhas de E/S, concorrência, persistência, watchdog e identificação de chips com uma árvore de dispositivos de teste. Para ensaiar o painel, execute `./run.sh --mock`, salve 8,7 V e selecione 50%. Confira que a saída continua em 0% até Aplicar. Após aplicar, confira 4,35 V, acione PARAR E ZERAR e observe os dois estados da parada. Repita e feche a aba para provocar o watchdog, acompanhando o terminal.

Na verificação de entrega em Windows, os 44 testes pytest passaram, incluindo a parada por SIGINT e SIGTERM em mock e a idempotência da edição de um config.txt temporário. Ruff, a análise sintática do JavaScript e a análise Bash dos scripts passaram. No Chromium, foram exercitados seleção sem aplicar, calibração, parada, fechamento da aba, perda e recuperação de comunicação e apresentação em larguras de 360, 800 e 1280 px. O terminal registrou o encerramento por Ctrl+C com PWM zero, descarga e ENA baixo.

As verificações de software não medem os pinos, a descarga real, a tensão de pico ou a pressão. A validação física é o ensaio com os instrumentos e a montagem descritos acima.
