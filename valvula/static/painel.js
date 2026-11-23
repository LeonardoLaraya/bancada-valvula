"use strict";
const el = id => document.getElementById(id);
const client = crypto.randomUUID();
const fmt = (v, digits = 0) => v == null ? "—" : v.toLocaleString("pt-BR", {
  minimumFractionDigits: digits, maximumFractionDigits: digits || 2
});
let state, revision = -1, online = false, busy = false, polling = false;
let needsStop = false, recovering = false, lastCalibration, generation = 0;

async function request(route, data) {
  const response = await fetch("/api/" + route, {
    method: "POST", headers: {"Content-Type": "application/json"},
    body: JSON.stringify(data), cache: "no-store", signal: AbortSignal.timeout(1800)
  });
  const json = await response.json();
  if (!response.ok) {
    const error = new Error(json.error || "Falha ao consultar a bancada.");
    error.status = response.status;
    throw error;
  }
  return json;
}
function selection() {
  const value = Number(el("slider").value);
  el("selected").value = fmt(value);
  el("selectedV").textContent = state ? fmt(state.config.max_voltage * value / 100, 2) + " V" : "—";
}
function buttons() {
  el("apply").disabled = !online || busy || needsStop ||
    !["Habilitado", "Desabilitado"].includes(state?.phase);
  el("save").disabled = !online || busy || needsStop;
}
function render(next) {
  if (state && state.instance !== next.instance) {
    location.reload();
    return;
  }
  if (next.revision < revision) return;
  state = next;
  revision = next.revision;
  el("mode").textContent = next.mock ? "MODO SIMULADO" : "HARDWARE REAL";
  el("mode").classList.toggle("sim", next.mock);
  el("phase").textContent = el("phase").dataset.phase = next.phase;
  el("applied").textContent = fmt(next.percent);
  el("appliedV").textContent = fmt(next.volts, 2) + " V";
  el("meter").hidden = next.percent == null;
  el("meter").value = next.percent || 0;
  const c = next.config;
  el("freq").textContent = fmt(c.frequency) + " Hz";
  const date = c.calibrated_at;
  el("cal-status").textContent = date ?
    "Última calibração em " + new Date(date).toLocaleString("pt-BR") :
    "Não calibrado · referência inicial de 10,0 V";
  if (lastCalibration !== date) {
    el("maximum").value = c.max_voltage;
    lastCalibration = date;
  }
  const rows = next.events.map(e => {
    const row = document.createElement("li"), t = document.createElement("time");
    t.dateTime = e.time;
    t.textContent = new Date(e.time).toLocaleTimeString("pt-BR");
    row.append(t, document.createTextNode(e.message));
    return row;
  });
  el("events").replaceChildren(...rows);
  selection();
  buttons();
}
function lost() {
  generation++;
  online = false;
  needsStop = true;
  revision = -1;
  el("phase").textContent = "Sem comunicação";
  el("phase").dataset.phase = "Erro";
  el("applied").textContent = el("appliedV").textContent = "—";
  el("meter").hidden = true;
  el("feedback").textContent = "Comunicação interrompida. Aguardando confirmação da parada.";
  buttons();
}
async function stop() {
  const current = ++generation;
  needsStop = true;
  el("slider").value = 0;
  selection();
  buttons();
  try {
    const next = await request("stop", {});
    if (current !== generation) return;
    needsStop = false;
    online = false; // Wait for a new heartbeat before enabling Apply.
    el("feedback").textContent = "";
    render(next);
  } catch {
    if (current === generation) lost();
  }
}
async function poll() {
  if (polling || recovering) return;
  if (needsStop) {
    recovering = true;
    try { await stop(); } finally { recovering = false; }
    return;
  }
  polling = true;
  const current = generation;
  try {
    const next = await request("heartbeat", {client});
    if (current !== generation) return;
    online = true;
    render(next);
    buttons();
  } catch {
    if (current === generation) lost();
  } finally { polling = false; }
}
async function command(route, data) {
  if (!online || needsStop || busy) return;
  const current = generation;
  busy = true;
  buttons();
  try {
    const next = await request(route, data);
    if (generation === current) {
      el("feedback").textContent = "";
      render(next);
    }
  } catch (error) {
    if (generation === current) {
      if ([400, 409].includes(error.status)) el("feedback").textContent = error.message;
      else lost();
    }
  } finally { busy = false; buttons(); }
}
el("slider").oninput = selection;
el("apply").onclick = () => command("apply", {client, epoch: state.epoch, percent: Number(el("slider").value)});
el("stop").onclick = stop;
el("cal").onsubmit = event => {
  event.preventDefault();
  command("calibration", {max_voltage: el("maximum").valueAsNumber});
};
poll();
setInterval(poll, 1000);
