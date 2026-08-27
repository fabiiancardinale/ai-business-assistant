const { useState, useEffect, useRef, useCallback } = React;

/* ========================= estado global simple ========================= */
const LS = {
  get api() { return localStorage.getItem("zp_api") || "http://localhost:8000"; },
  set api(v) { localStorage.setItem("zp_api", v); },
  get token() { return localStorage.getItem("zp_token") || ""; },
  set token(v) { v ? localStorage.setItem("zp_token", v) : localStorage.removeItem("zp_token"); },
  get company() { return localStorage.getItem("zp_company") || ""; },
  set company(v) { v ? localStorage.setItem("zp_company", v) : localStorage.removeItem("zp_company"); },
};

async function api(method, path, body) {
  const headers = { "Content-Type": "application/json" };
  if (LS.token) headers["Authorization"] = "Bearer " + LS.token;
  if (LS.company) headers["X-Company-Id"] = LS.company;
  const res = await fetch(LS.api + path, {
    method, headers, body: body ? JSON.stringify(body) : undefined,
  });
  const text = await res.text();
  let data = null;
  try { data = text ? JSON.parse(text) : null; } catch (e) { data = text; }
  if (!res.ok) throw new Error((data && data.detail) || ("Error " + res.status));
  return data;
}

async function apiUpload(path, formData) {
  const headers = {};
  if (LS.token) headers["Authorization"] = "Bearer " + LS.token;
  if (LS.company) headers["X-Company-Id"] = LS.company;
  const res = await fetch(LS.api + path, { method: "POST", headers, body: formData });
  const data = await res.json().catch(() => null);
  if (!res.ok) throw new Error((data && data.detail) || ("Error " + res.status));
  return data;
}

/* ========================= UI helpers ========================= */
function Card({ title, sub, right, children }) {
  return (
    <div className="bg-slate-800/60 border border-slate-700 rounded-xl p-5 mb-5">
      {(title || right) && (
        <div className="flex items-center justify-between mb-3">
          <div>
            {title && <h2 className="text-white font-semibold">{title}</h2>}
            {sub && <p className="text-slate-400 text-sm">{sub}</p>}
          </div>
          {right}
        </div>
      )}
      {children}
    </div>
  );
}
function Btn({ children, onClick, kind = "primary", type = "button", disabled }) {
  const cls = {
    primary: "bg-amber-400 text-slate-900 hover:bg-amber-300",
    ghost: "bg-slate-700 text-slate-100 hover:bg-slate-600",
    danger: "bg-transparent text-red-300 border border-red-400/40 hover:bg-red-500/10",
  }[kind];
  return (
    <button type={type} onClick={onClick} disabled={disabled}
      className={"px-4 py-2 rounded-lg text-sm font-semibold disabled:opacity-50 " + cls}>
      {children}
    </button>
  );
}
function Field({ label, children, hint }) {
  return (
    <label className="block mb-3">
      <span className="block text-sm text-slate-300 mb-1">{label}</span>
      {children}
      {hint && <span className="block text-xs text-slate-500 mt-1">{hint}</span>}
    </label>
  );
}
const inputCls = "w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-100 outline-none focus:border-amber-400";

/* ========================= LOGIN ========================= */
function Login({ onLogged }) {
  const [mode, setMode] = useState("login");
  const [apiBase, setApiBase] = useState(LS.api);
  const [form, setForm] = useState({ name: "", email: "", password: "", company_name: "" });
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(false);
  const upd = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  async function submit(e) {
    e.preventDefault();
    setErr(""); setLoading(true);
    LS.api = apiBase.replace(/\/$/, "");
    try {
      if (mode === "register") {
        await api("POST", "/api/v1/auth/register", form);
      }
      const t = await api("POST", "/api/v1/auth/login", { email: form.email, password: form.password });
      LS.token = t.access_token;
      const me = await api("GET", "/api/v1/auth/me");
      if (me.companies && me.companies.length) LS.company = String(me.companies[0].company_id);
      onLogged(me);
    } catch (e2) { setErr(e2.message); }
    setLoading(false);
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <form onSubmit={submit} className="bg-slate-800 border border-slate-700 rounded-2xl p-8 w-full max-w-sm">
        <div className="text-center text-2xl font-extrabold mb-1">⚡ Zelekpress</div>
        <div className="text-center text-slate-400 text-sm mb-6">Panel de chatbots</div>
        {err && <div className="bg-red-500/10 border border-red-400/30 text-red-300 rounded-lg px-3 py-2 mb-4 text-sm">{err}</div>}
        {mode === "register" && (
          <>
            <Field label="Tu nombre"><input className={inputCls} value={form.name} onChange={upd("name")} required /></Field>
            <Field label="Empresa"><input className={inputCls} value={form.company_name} onChange={upd("company_name")} required /></Field>
          </>
        )}
        <Field label="Email"><input type="email" className={inputCls} value={form.email} onChange={upd("email")} required /></Field>
        <Field label="Contraseña"><input type="password" className={inputCls} value={form.password} onChange={upd("password")} required /></Field>
        <Field label="URL de la API" hint="Ej: http://localhost:8000 o https://api.zelekpress.com">
          <input className={inputCls} value={apiBase} onChange={(e) => setApiBase(e.target.value)} />
        </Field>
        <button type="submit" disabled={loading}
          className="w-full bg-amber-400 text-slate-900 font-bold rounded-lg py-2.5 mt-2 disabled:opacity-50">
          {loading ? "..." : mode === "login" ? "Ingresar" : "Crear cuenta"}
        </button>
        <div className="text-center text-slate-400 text-sm mt-4">
          {mode === "login"
            ? <span>¿No tenés cuenta? <a className="text-amber-400 cursor-pointer" onClick={() => setMode("register")}>Registrate</a></span>
            : <span>¿Ya tenés cuenta? <a className="text-amber-400 cursor-pointer" onClick={() => setMode("login")}>Ingresá</a></span>}
        </div>
      </form>
    </div>
  );
}

/* ========================= CHATBOTS ========================= */
function ChatbotsPage({ onOpen }) {
  const [bots, setBots] = useState([]);
  const [name, setName] = useState("");
  const [err, setErr] = useState("");
  const load = useCallback(() => api("GET", "/api/v1/chatbots").then(setBots).catch((e) => setErr(e.message)), []);
  useEffect(() => { load(); }, [load]);

  async function create() {
    if (!name.trim()) return;
    setErr("");
    try { await api("POST", "/api/v1/chatbots", { name_public: name.trim() }); setName(""); load(); }
    catch (e) { setErr(e.message); }
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-4">Chatbots</h1>
      {err && <div className="text-red-300 mb-3">{err}</div>}
      <Card title="Nuevo chatbot" sub="El plan Chatbot Básico permite 1.">
        <div className="flex gap-2">
          <input className={inputCls} placeholder="Nombre del asistente" value={name} onChange={(e) => setName(e.target.value)} />
          <Btn onClick={create}>Crear</Btn>
        </div>
      </Card>
      <div className="grid gap-3">
        {bots.map((b) => (
          <div key={b.id} onClick={() => onOpen(b.id)}
            className="bg-slate-800/60 border border-slate-700 rounded-xl p-4 flex items-center justify-between cursor-pointer hover:border-amber-400/50">
            <div>
              <div className="font-semibold text-white">{b.name_public}</div>
              <div className="text-slate-400 text-sm">{b.description || "—"} · <span className={b.status === "active" ? "text-emerald-400" : "text-slate-500"}>{b.status}</span></div>
            </div>
            <span className="text-slate-500">→</span>
          </div>
        ))}
        {!bots.length && <p className="text-slate-500">Todavía no tenés chatbots. Creá el primero arriba.</p>}
      </div>
    </div>
  );
}

/* ========================= DETALLE DE CHATBOT ========================= */
function ChatbotDetail({ id, onBack }) {
  const [tab, setTab] = useState("general");
  const [bot, setBot] = useState(null);
  useEffect(() => { api("GET", "/api/v1/chatbots/" + id).then(setBot); }, [id]);
  if (!bot) return <p className="text-slate-400">Cargando…</p>;

  const tabs = [["general", "General"], ["install", "Instalación"], ["settings", "Configuración"], ["appearance", "Apariencia"], ["knowledge", "Conocimiento"]];
  return (
    <div>
      <button onClick={onBack} className="text-slate-400 text-sm mb-3">← Volver a chatbots</button>
      <h1 className="text-2xl font-bold mb-4">{bot.name_public}</h1>
      <div className="flex gap-2 mb-5 flex-wrap">
        {tabs.map(([k, l]) => (
          <button key={k} onClick={() => setTab(k)}
            className={"px-3 py-1.5 rounded-lg text-sm " + (tab === k ? "bg-amber-400 text-slate-900 font-semibold" : "bg-slate-800 text-slate-300")}>{l}</button>
        ))}
      </div>
      {tab === "general" && <GeneralTab bot={bot} onChanged={setBot} onDeleted={onBack} />}
      {tab === "install" && <InstallTab bot={bot} />}
      {tab === "settings" && <SettingsTab id={id} />}
      {tab === "appearance" && <AppearanceTab id={id} />}
      {tab === "knowledge" && <KnowledgeTab id={id} />}
    </div>
  );
}

function GeneralTab({ bot, onChanged, onDeleted }) {
  const [name, setName] = useState(bot.name_public);
  const [desc, setDesc] = useState(bot.description || "");
  const [status, setStatus] = useState(bot.status);
  const [msg, setMsg] = useState("");
  async function save() {
    setMsg("");
    try {
      const r = await api("PATCH", "/api/v1/chatbots/" + bot.id, { name_public: name, description: desc, status });
      onChanged(r); setMsg("✓ Guardado");
    } catch (e) { setMsg("✕ " + e.message); }
  }
  async function del() {
    if (!confirm("¿Eliminar este chatbot? Se borran su conocimiento y conversaciones. No se puede deshacer.")) return;
    try { await api("DELETE", "/api/v1/chatbots/" + bot.id); onDeleted(); }
    catch (e) { setMsg("✕ " + e.message); }
  }
  return (
    <>
      <Card title="Datos del chatbot">
        <Field label="Nombre visible"><input className={inputCls} value={name} onChange={(e) => setName(e.target.value)} /></Field>
        <Field label="Descripción"><input className={inputCls} value={desc} onChange={(e) => setDesc(e.target.value)} /></Field>
        <Field label="Estado">
          <select className={inputCls} value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="active">Activo (visible en el sitio)</option>
            <option value="paused">Pausado (no responde)</option>
          </select>
        </Field>
        <div className="flex items-center gap-3"><Btn onClick={save}>Guardar cambios</Btn><span className="text-sm text-slate-400">{msg}</span></div>
      </Card>
      <Card title="Zona de peligro" sub="Eliminar el chatbot es permanente.">
        <Btn kind="danger" onClick={del}>Eliminar chatbot</Btn>
      </Card>
    </>
  );
}

function InstallTab({ bot }) {
  const snippet = `<script\n  src="${LS.api}/widget/widget.js"\n  data-chatbot-id="${bot.id}"\n  data-api="${LS.api}"><\/script>`;
  const [copied, setCopied] = useState(false);
  return (
    <Card title="Código de instalación" sub="Pegalo antes de </body> en el sitio del cliente.">
      <pre className="bg-slate-900 border border-slate-700 rounded-lg p-4 text-xs text-slate-300 overflow-x-auto whitespace-pre">{snippet}</pre>
      <div className="mt-3">
        <Btn onClick={() => { navigator.clipboard.writeText(snippet); setCopied(true); setTimeout(() => setCopied(false), 2000); }}>
          {copied ? "✓ Copiado" : "Copiar código"}
        </Btn>
      </div>
    </Card>
  );
}

function SettingsTab({ id }) {
  const [s, setS] = useState(null);
  const [msg, setMsg] = useState("");
  useEffect(() => { api("GET", "/api/v1/chatbots/" + id + "/settings").then(setS); }, [id]);
  if (!s) return <p className="text-slate-400">Cargando…</p>;
  const upd = (k) => (e) => setS({ ...s, [k]: e.target.value });
  async function save() {
    setMsg("");
    try {
      await api("PUT", "/api/v1/chatbots/" + id + "/settings", {
        system_prompt: s.system_prompt, personality: s.personality,
        greeting_message: s.greeting_message, temperature: parseFloat(s.temperature),
        max_tokens: parseInt(s.max_tokens), model: s.model || null,
      });
      setMsg("✓ Guardado");
    } catch (e) { setMsg("✕ " + e.message); }
  }
  return (
    <Card title="Comportamiento e IA">
      <Field label="Instrucciones del negocio (system prompt)" hint="Qué es, qué vende, tono, reglas.">
        <textarea rows={5} className={inputCls} value={s.system_prompt || ""} onChange={upd("system_prompt")} />
      </Field>
      <Field label="Personalidad"><input className={inputCls} value={s.personality || ""} onChange={upd("personality")} /></Field>
      <Field label="Mensaje de saludo"><input className={inputCls} value={s.greeting_message || ""} onChange={upd("greeting_message")} /></Field>
      <div className="grid grid-cols-3 gap-3">
        <Field label="Modelo"><input className={inputCls} value={s.model || ""} onChange={upd("model")} placeholder="llama-3.1-8b-instant" /></Field>
        <Field label="Temperatura"><input type="number" step="0.1" className={inputCls} value={s.temperature} onChange={upd("temperature")} /></Field>
        <Field label="Máx. tokens"><input type="number" className={inputCls} value={s.max_tokens} onChange={upd("max_tokens")} /></Field>
      </div>
      <div className="flex items-center gap-3"><Btn onClick={save}>Guardar</Btn><span className="text-sm text-slate-400">{msg}</span></div>
    </Card>
  );
}

function AppearanceTab({ id }) {
  const [ap, setAp] = useState(null);
  const [presets, setPresets] = useState([]);
  const [msg, setMsg] = useState("");
  useEffect(() => {
    api("GET", "/api/v1/chatbots/" + id + "/appearance").then((r) => setAp(r.appearance));
    api("GET", "/api/v1/themes/presets").then(setPresets).catch(() => {});
  }, [id]);
  if (!ap) return <p className="text-slate-400">Cargando…</p>;
  const c = ap.colors, h = ap.header, l = ap.launcher, ly = ap.layout;
  const setColor = (k) => (e) => setAp({ ...ap, colors: { ...c, [k]: e.target.value } });
  const setHeader = (k) => (e) => setAp({ ...ap, header: { ...h, [k]: e.target.value } });
  const setLauncher = (k, num) => (e) => setAp({ ...ap, launcher: { ...l, [k]: num ? parseInt(e.target.value) : e.target.value } });
  const setLayout = (k, num) => (e) => setAp({ ...ap, layout: { ...ly, [k]: num ? parseInt(e.target.value) : e.target.value } });
  async function save() {
    setMsg("");
    try {
      await api("PUT", "/api/v1/chatbots/" + id + "/appearance", { appearance: { colors: c, header: h, launcher: l, layout: ly } });
      setMsg("✓ Guardado");
    } catch (e) { setMsg("✕ " + e.message); }
  }
  async function applyPreset(key) {
    const r = await api("POST", "/api/v1/chatbots/" + id + "/appearance/apply-preset/" + key);
    setAp(r.appearance); setMsg("✓ Tema aplicado");
  }
  async function uploadImage(target, file) {
    setMsg("Subiendo…");
    try {
      const fd = new FormData(); fd.append("file", file);
      const r = await apiUpload("/api/v1/chatbots/" + id + "/appearance/image?target=" + target, fd);
      setAp(r.appearance); setMsg("✓ Imagen subida");
    } catch (e) { setMsg("✕ " + e.message); }
  }
  function clearImage() { setAp({ ...ap, launcher: { ...l, image: null } }); }

  return (
    <div className="grid md:grid-cols-2 gap-5">
      <div>
        <Card title="Temas">
          <div className="flex flex-wrap gap-2">
            {presets.map((p) => (
              <button key={p.key} onClick={() => applyPreset(p.key)}
                className="px-3 py-1.5 rounded-full text-sm bg-slate-800 border border-slate-700 hover:border-amber-400 text-slate-200">{p.label}</button>
            ))}
          </div>
        </Card>

        <Card title="Botón del chat (launcher)">
          <Field label="Ícono (emoji)" hint="Se usa si no subís una imagen.">
            <input className={inputCls} value={l.image ? "" : (l.icon || "")} onChange={setLauncher("icon")} maxLength={4} placeholder="💬" />
          </Field>
          <Field label="Imagen (PNG/JPG/WEBP)">
            <input type="file" accept="image/png,image/jpeg,image/webp"
              onChange={(e) => e.target.files[0] && uploadImage("launcher", e.target.files[0])} className="text-sm text-slate-300" />
          </Field>
          {l.image && (
            <div className="flex items-center gap-3 mb-3">
              <img src={LS.api + l.image} alt="" className="w-10 h-10 rounded-full object-cover border border-slate-600" />
              <button onClick={clearImage} className="text-red-300 text-sm">Quitar imagen</button>
            </div>
          )}
          <div className="grid grid-cols-2 gap-3">
            <Field label="Color del botón"><input type="color" value={l.color} onChange={setLauncher("color")} className="w-16 h-10 rounded" /></Field>
            <Field label="Tamaño (px)"><input type="range" min="48" max="80" value={l.size} onChange={setLauncher("size", true)} /></Field>
          </div>
        </Card>

        <Card title="Posición y tamaño">
          <div className="grid grid-cols-2 gap-3">
            <Field label="Lado">
              <select className={inputCls} value={ly.side} onChange={setLayout("side")}>
                <option value="right">Derecha</option>
                <option value="left">Izquierda</option>
              </select>
            </Field>
            <Field label="Radio de bordes"><input type="range" min="0" max="30" value={ly.radius} onChange={setLayout("radius", true)} /></Field>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Ancho del chat"><input type="range" min="300" max="440" value={ly.width} onChange={setLayout("width", true)} /></Field>
            <Field label="Alto del chat"><input type="range" min="420" max="640" value={ly.height} onChange={setLayout("height", true)} /></Field>
          </div>
        </Card>

        <Card title="Colores y header">
          <div className="grid grid-cols-2 gap-3">
            <Field label="Principal"><input type="color" value={c.primary} onChange={setColor("primary")} className="w-16 h-10 rounded" /></Field>
            <Field label="Fondo"><input type="color" value={c.background} onChange={setColor("background")} className="w-16 h-10 rounded" /></Field>
            <Field label="Burbuja usuario"><input type="color" value={c.user_bubble} onChange={setColor("user_bubble")} className="w-16 h-10 rounded" /></Field>
            <Field label="Burbuja bot"><input type="color" value={c.bot_bubble} onChange={setColor("bot_bubble")} className="w-16 h-10 rounded" /></Field>
          </div>
          <Field label="Título del header"><input className={inputCls} value={h.title} onChange={setHeader("title")} /></Field>
          <Field label="Subtítulo del header"><input className={inputCls} value={h.subtitle} onChange={setHeader("subtitle")} /></Field>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Fondo header"><input type="color" value={h.bg_color} onChange={setHeader("bg_color")} className="w-16 h-10 rounded" /></Field>
            <Field label="Texto header"><input type="color" value={h.text_color} onChange={setHeader("text_color")} className="w-16 h-10 rounded" /></Field>
          </div>
          <div className="flex items-center gap-3"><Btn onClick={save}>Guardar apariencia</Btn><span className="text-sm text-slate-400">{msg}</span></div>
        </Card>
      </div>
      <Card title="Vista previa">
        <ChatPreview ap={ap} />
      </Card>
    </div>
  );
}

function ChatPreview({ ap }) {
  const c = ap.colors, h = ap.header, l = ap.launcher;
  const imgSrc = l.image ? (l.image.startsWith("http") ? l.image : LS.api + l.image) : null;
  const logo = imgSrc
    ? <img src={imgSrc} alt="" style={{ width: "100%", height: "100%", objectFit: "cover", borderRadius: "50%" }} />
    : <span>{l.icon || "🤖"}</span>;
  return (
    <div className="rounded-xl overflow-hidden border border-slate-700" style={{ width: 320, background: c.background }}>
      <div style={{ background: h.bg_color, color: h.text_color, padding: "12px 14px", display: "flex", gap: 10, alignItems: "center" }}>
        <div style={{ width: 30, height: 30, borderRadius: "50%", background: imgSrc ? "transparent" : c.primary, overflow: "hidden", display: "flex", alignItems: "center", justifyContent: "center" }}>{logo}</div>
        <div><div style={{ fontWeight: 700, fontSize: 14 }}>{h.title}</div><div style={{ fontSize: 11, opacity: .8 }}>● {h.subtitle}</div></div>
      </div>
      <div style={{ padding: 14, display: "flex", flexDirection: "column", gap: 8, background: "#f8fafc" }}>
        <div style={{ alignSelf: "flex-start", background: c.bot_bubble, color: c.bot_text, padding: "8px 11px", borderRadius: "12px 12px 12px 4px", fontSize: 13, maxWidth: "80%" }}>{h.title ? "¡Hola! ¿En qué te ayudo?" : "Hola"}</div>
        <div style={{ alignSelf: "flex-end", background: c.user_bubble, color: c.user_text, padding: "8px 11px", borderRadius: "12px 12px 4px 12px", fontSize: 13, maxWidth: "80%" }}>Quiero info</div>
      </div>
      <div style={{ padding: 10, borderTop: "1px solid #e5e7eb", background: "#fff", display: "flex", gap: 6 }}>
        <div style={{ flex: 1, height: 34, border: "1px solid #d1d5db", borderRadius: 8 }}></div>
        <div style={{ width: 34, height: 34, borderRadius: 8, background: c.primary }}></div>
      </div>
    </div>
  );
}

function KnowledgeTab({ id }) {
  const [srcs, setSrcs] = useState([]);
  const [form, setForm] = useState({ name: "", content: "", url: "" });
  const [err, setErr] = useState("");
  const load = useCallback(() => api("GET", "/api/v1/chatbots/" + id + "/knowledge").then(setSrcs), [id]);
  useEffect(() => { load(); }, [load]);
  async function addText() {
    setErr("");
    try { await api("POST", "/api/v1/chatbots/" + id + "/knowledge/text", { type: "text", name: form.name || "Info", content: form.content }); setForm({ ...form, name: "", content: "" }); load(); }
    catch (e) { setErr(e.message); }
  }
  async function addUrl() {
    setErr("");
    try { await api("POST", "/api/v1/chatbots/" + id + "/knowledge/url", { name: form.name || form.url, url: form.url }); setForm({ ...form, url: "" }); load(); }
    catch (e) { setErr(e.message); }
  }
  async function del(sid) { await api("DELETE", "/api/v1/chatbots/" + id + "/knowledge/" + sid); load(); }
  return (
    <div>
      {err && <div className="text-red-300 mb-3">{err}</div>}
      <Card title="Agregar texto / FAQ">
        <Field label="Nombre"><input className={inputCls} value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></Field>
        <Field label="Contenido"><textarea rows={4} className={inputCls} value={form.content} onChange={(e) => setForm({ ...form, content: e.target.value })} /></Field>
        <Btn onClick={addText}>Agregar texto</Btn>
      </Card>
      <Card title="Agregar desde una URL">
        <div className="flex gap-2">
          <input className={inputCls} placeholder="https://…" value={form.url} onChange={(e) => setForm({ ...form, url: e.target.value })} />
          <Btn onClick={addUrl} kind="ghost">Agregar URL</Btn>
        </div>
      </Card>
      <Card title="Fuentes de conocimiento">
        {srcs.map((s) => (
          <div key={s.id} className="flex items-center justify-between border-b border-slate-700 py-2">
            <div><span className="text-white">{s.name}</span> <span className="text-xs text-slate-500">· {s.type} · {s.chunk_count} fragmentos · <span className={s.status === "ready" ? "text-emerald-400" : s.status === "error" ? "text-red-400" : "text-slate-400"}>{s.status}</span></span></div>
            <button onClick={() => del(s.id)} className="text-red-300 text-sm">Eliminar</button>
          </div>
        ))}
        {!srcs.length && <p className="text-slate-500">Sin fuentes todavía.</p>}
      </Card>
    </div>
  );
}

/* ========================= CONVERSACIONES ========================= */
function ConversationsPage() {
  const [list, setList] = useState([]);
  const [sel, setSel] = useState(null);
  const [detail, setDetail] = useState(null);
  const [reply, setReply] = useState("");
  const load = useCallback(() => api("GET", "/api/v1/conversations").then(setList), []);
  useEffect(() => { load(); const t = setInterval(load, 5000); return () => clearInterval(t); }, [load]);
  useEffect(() => { if (sel) api("GET", "/api/v1/conversations/" + sel).then(setDetail); }, [sel, list]);

  async function send() {
    if (!reply.trim()) return;
    await api("POST", "/api/v1/conversations/" + sel + "/reply", { content: reply.trim() });
    setReply(""); api("GET", "/api/v1/conversations/" + sel).then(setDetail);
  }
  async function act(a) { await api("POST", "/api/v1/conversations/" + sel + "/" + a); load(); api("GET", "/api/v1/conversations/" + sel).then(setDetail); }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-4">Conversaciones</h1>
      <div className="grid md:grid-cols-3 gap-4">
        <div className="bg-slate-800/60 border border-slate-700 rounded-xl p-2 max-h-[70vh] overflow-y-auto">
          {list.map((c) => (
            <div key={c.id} onClick={() => setSel(c.id)}
              className={"p-3 rounded-lg cursor-pointer " + (sel === c.id ? "bg-slate-700" : "hover:bg-slate-700/50")}>
              <div className="text-sm text-white">#{c.id} · <span className={"text-xs " + (c.status === "human" ? "text-amber-400" : c.status === "closed" ? "text-slate-500" : "text-emerald-400")}>{c.status}</span>{c.human_requested && <span className="text-amber-400"> · 👤 pide humano</span>}</div>
              <div className="text-xs text-slate-500">{c.last_message_at ? new Date(c.last_message_at).toLocaleString() : ""}</div>
            </div>
          ))}
          {!list.length && <p className="text-slate-500 p-3 text-sm">Sin conversaciones.</p>}
        </div>
        <div className="md:col-span-2 bg-slate-800/60 border border-slate-700 rounded-xl p-4 flex flex-col max-h-[70vh]">
          {!detail && <p className="text-slate-500">Elegí una conversación.</p>}
          {detail && (
            <>
              <div className="flex gap-2 mb-3 flex-wrap">
                <Btn kind="ghost" onClick={() => act("take")}>Tomar</Btn>
                <Btn kind="ghost" onClick={() => act("return-ai")}>Devolver a IA</Btn>
                <Btn kind="danger" onClick={() => act("close")}>Cerrar</Btn>
              </div>
              <div className="flex-1 overflow-y-auto flex flex-col gap-2 mb-3">
                {detail.messages.filter((m) => m.role !== "note").map((m) => (
                  <div key={m.id} className={"flex " + (m.role === "visitor" ? "justify-end" : "justify-start")}>
                    <div className={"max-w-[80%] px-3 py-2 rounded-lg text-sm " +
                      (m.role === "visitor" ? "bg-slate-900 text-slate-100" : m.role === "agent" ? "bg-amber-400 text-slate-900" : m.role === "system" ? "bg-slate-700/50 text-slate-400 italic" : "bg-slate-700 text-slate-100")}>
                      {m.content}
                    </div>
                  </div>
                ))}
              </div>
              <div className="flex gap-2">
                <input className={inputCls} placeholder="Responder como agente…" value={reply}
                  onChange={(e) => setReply(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter") send(); }} />
                <Btn onClick={send}>Enviar</Btn>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

/* ========================= LEADS ========================= */
function LeadsPage() {
  const [leads, setLeads] = useState([]);
  useEffect(() => { api("GET", "/api/v1/leads").then(setLeads); }, []);
  return (
    <div>
      <h1 className="text-2xl font-bold mb-4">Leads</h1>
      <Card>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead><tr className="text-slate-400 text-left"><th className="py-2">Nombre</th><th>Email</th><th>Teléfono</th><th>Estado</th><th>Fecha</th></tr></thead>
            <tbody>
              {leads.map((l) => (
                <tr key={l.id} className="border-t border-slate-700">
                  <td className="py-2 text-white">{l.name || "—"}</td>
                  <td className="text-slate-300">{l.email || "—"}</td>
                  <td className="text-slate-300">{l.phone || "—"}</td>
                  <td><span className="text-xs bg-blue-500/20 text-blue-300 px-2 py-0.5 rounded-full">{l.status}</span></td>
                  <td className="text-slate-500">{l.created_at ? new Date(l.created_at).toLocaleDateString() : ""}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {!leads.length && <p className="text-slate-500 py-3">Sin leads todavía.</p>}
        </div>
      </Card>
    </div>
  );
}

/* ========================= INTEGRACIONES ========================= */
function IntegracionesPage() {
  const [keys, setKeys] = useState([]);
  const [wh, setWh] = useState([]);
  const [events, setEvents] = useState([]);
  const [err, setErr] = useState("");
  const [newKey, setNewKey] = useState(null); // key completa mostrada una sola vez
  const [kf, setKf] = useState({ name: "", read: true, write: false });
  const [wf, setWf] = useState({ url: "", events: [] });

  const loadKeys = useCallback(() => api("GET", "/api/v1/integrations/api-keys").then(setKeys).catch((e) => setErr(e.message)), []);
  const loadWh = useCallback(() => api("GET", "/api/v1/integrations/webhooks").then((r) => { setWh(r.webhooks); setEvents(r.available_events); }).catch((e) => setErr(e.message)), []);
  useEffect(() => { loadKeys(); loadWh(); }, [loadKeys, loadWh]);

  async function createKey() {
    if (!kf.name.trim()) return;
    setErr("");
    const scopes = [kf.read && "read", kf.write && "write"].filter(Boolean);
    try {
      const r = await api("POST", "/api/v1/integrations/api-keys", { name: kf.name.trim(), scopes });
      setNewKey(r.key);
      setKf({ name: "", read: true, write: false });
      loadKeys();
    } catch (e) { setErr(e.message); }
  }
  async function revokeKey(k) {
    if (!confirm("¿Revocar la key " + k.name + "? Dejará de funcionar de inmediato.")) return;
    try { await api("DELETE", "/api/v1/integrations/api-keys/" + k.id); loadKeys(); } catch (e) { setErr(e.message); }
  }

  function toggleWfEvent(ev) {
    setWf((s) => ({ ...s, events: s.events.includes(ev) ? s.events.filter((e) => e !== ev) : [...s.events, ev] }));
  }
  async function createWh() {
    if (!wf.url.trim()) return;
    setErr("");
    try {
      await api("POST", "/api/v1/integrations/webhooks", { url: wf.url.trim(), events: wf.events });
      setWf({ url: "", events: [] });
      loadWh();
    } catch (e) { setErr(e.message); }
  }
  async function toggleWh(w) { try { await api("PATCH", "/api/v1/integrations/webhooks/" + w.id, { active: !w.active }); loadWh(); } catch (e) { setErr(e.message); } }
  async function delWh(w) { if (!confirm("¿Eliminar este webhook?")) return; try { await api("DELETE", "/api/v1/integrations/webhooks/" + w.id); loadWh(); } catch (e) { setErr(e.message); } }
  async function testWh(w) { try { await api("POST", "/api/v1/integrations/webhooks/" + w.id + "/test"); setTimeout(loadWh, 1500); } catch (e) { setErr(e.message); } }

  const copy = (t) => { navigator.clipboard && navigator.clipboard.writeText(t); };

  return (
    <div>
      <h1 className="text-2xl font-bold mb-1">Integraciones</h1>
      <p className="text-slate-400 mb-4 text-sm">Conectá el chatbot con tus sistemas: API keys para consumir la API, y webhooks para recibir eventos en tu servidor.</p>
      {err && <div className="text-red-300 mb-3">{err}</div>}

      {newKey && (
        <div className="bg-amber-400/10 border border-amber-400/40 rounded-xl p-4 mb-5">
          <p className="text-amber-200 text-sm mb-2 font-semibold">Guardá esta API key ahora — no se vuelve a mostrar.</p>
          <div className="flex items-center gap-2">
            <code className="flex-1 bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-amber-300 text-sm break-all">{newKey}</code>
            <Btn kind="ghost" onClick={() => copy(newKey)}>Copiar</Btn>
            <Btn kind="ghost" onClick={() => setNewKey(null)}>Listo</Btn>
          </div>
        </div>
      )}

      <Card title="Nueva API key">
        <div className="grid md:grid-cols-3 gap-3 items-end">
          <Field label="Nombre (para reconocerla)"><input className={inputCls} value={kf.name} onChange={(e) => setKf({ ...kf, name: e.target.value })} placeholder="Integración CRM" /></Field>
          <Field label="Permisos">
            <div className="flex gap-4 pt-2">
              <label className="flex items-center gap-2 text-slate-300 text-sm"><input type="checkbox" checked={kf.read} onChange={(e) => setKf({ ...kf, read: e.target.checked })} /> Lectura</label>
              <label className="flex items-center gap-2 text-slate-300 text-sm"><input type="checkbox" checked={kf.write} onChange={(e) => setKf({ ...kf, write: e.target.checked })} /> Escritura</label>
            </div>
          </Field>
          <div className="mb-3"><Btn onClick={createKey}>Generar key</Btn></div>
        </div>
      </Card>

      <Card title="API keys">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead><tr className="text-slate-400 text-left"><th className="py-2">Nombre</th><th>Prefijo</th><th>Permisos</th><th>Último uso</th><th>Estado</th><th></th></tr></thead>
            <tbody>
              {keys.map((k) => (
                <tr key={k.id} className="border-t border-slate-700">
                  <td className="py-2 text-white">{k.name}</td>
                  <td className="text-slate-400 font-mono text-xs">{k.prefix}…</td>
                  <td className="text-slate-300">{(k.scopes || []).join(", ")}</td>
                  <td className="text-slate-500">{k.last_used_at ? new Date(k.last_used_at).toLocaleString() : "nunca"}</td>
                  <td>{k.revoked ? <span className="text-xs text-red-300">revocada</span> : <span className="text-xs text-emerald-300">activa</span>}</td>
                  <td className="text-right">{!k.revoked && <Btn kind="danger" onClick={() => revokeKey(k)}>Revocar</Btn>}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {!keys.length && <p className="text-slate-500 py-3">Todavía no creaste ninguna API key.</p>}
        </div>
      </Card>

      <Card title="Nuevo webhook" sub="Recibí un POST firmado (HMAC-SHA256) cuando ocurra un evento.">
        <Field label="URL de destino"><input className={inputCls} value={wf.url} onChange={(e) => setWf({ ...wf, url: e.target.value })} placeholder="https://tu-servidor.com/webhooks/zelekpress" /></Field>
        <div className="flex flex-wrap gap-3 mb-3">
          {events.map((ev) => (
            <label key={ev} className="flex items-center gap-2 text-slate-300 text-sm bg-slate-900 border border-slate-700 rounded-lg px-3 py-1.5">
              <input type="checkbox" checked={wf.events.includes(ev)} onChange={() => toggleWfEvent(ev)} /> {ev}
            </label>
          ))}
        </div>
        <Btn onClick={createWh}>Crear webhook</Btn>
      </Card>

      <Card title="Webhooks">
        {wh.map((w) => (
          <div key={w.id} className="border border-slate-700 rounded-lg p-3 mb-3">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="text-white break-all">{w.url}</p>
                <p className="text-slate-400 text-xs mt-1">{(w.events || []).join(", ") || "sin eventos"}</p>
                <p className="text-slate-500 text-xs mt-1">
                  Última entrega: {w.last_delivery_at ? new Date(w.last_delivery_at).toLocaleString() : "—"}
                  {w.last_status != null && <span className={w.last_status >= 200 && w.last_status < 300 ? " text-emerald-300" : " text-red-300"}> · HTTP {w.last_status}</span>}
                  {w.last_error && <span className="text-red-300"> · {w.last_error}</span>}
                </p>
                <p className="text-slate-500 text-xs mt-1">Secret: <code className="text-slate-400">{w.secret}</code> <button className="text-amber-300 ml-1" onClick={() => copy(w.secret)}>copiar</button></p>
              </div>
              <div className="flex flex-col gap-2 shrink-0">
                <Btn kind="ghost" onClick={() => testWh(w)}>Probar</Btn>
                <Btn kind="ghost" onClick={() => toggleWh(w)}>{w.active ? "Pausar" : "Activar"}</Btn>
                <Btn kind="danger" onClick={() => delWh(w)}>Eliminar</Btn>
              </div>
            </div>
            {!w.active && <p className="text-amber-300 text-xs mt-2">Pausado — no recibe eventos.</p>}
          </div>
        ))}
        {!wh.length && <p className="text-slate-500 py-2">Todavía no configuraste webhooks.</p>}
      </Card>
    </div>
  );
}

/* ========================= ANALYTICS ========================= */
function UsageCard() {
  const [u, setU] = useState(null);
  useEffect(() => { api("GET", "/api/v1/analytics/usage").then(setU).catch(() => {}); }, []);
  if (!u) return null;
  const labels = { conversations: "Conversaciones", messages: "Mensajes", leads: "Leads" };
  return (
    <Card title="Uso del plan" sub={"Período " + u.period + (u.plan ? " · Plan: " + u.plan : " · Sin plan asignado")}>
      <div className="grid md:grid-cols-3 gap-4">
        {["conversations", "messages", "leads"].map((k) => {
          const it = u.items[k]; const pct = it.limit ? Math.min(100, Math.round((it.used / it.limit) * 100)) : 0;
          return (
            <div key={k}>
              <div className="flex justify-between text-sm mb-1">
                <span className="text-slate-300">{labels[k]}</span>
                <span className={it.over ? "text-red-400" : "text-slate-400"}>{it.used}{it.limit ? " / " + it.limit : ""}</span>
              </div>
              <div className="h-2 bg-slate-700 rounded-full overflow-hidden">
                <div className={"h-full " + (it.over ? "bg-red-500" : "bg-amber-400")} style={{ width: (it.limit ? pct : 0) + "%" }}></div>
              </div>
            </div>
          );
        })}
      </div>
    </Card>
  );
}

function AnalyticsPage() {
  const [ov, setOv] = useState(null);
  const [un, setUn] = useState([]);
  const [answer, setAnswer] = useState({});
  const load = useCallback(() => {
    api("GET", "/api/v1/analytics/overview").then(setOv);
    api("GET", "/api/v1/analytics/unanswered").then(setUn);
  }, []);
  useEffect(() => { load(); }, [load]);
  async function addKb(u) {
    const a = (answer[u.id] || "").trim();
    if (!a) return;
    await api("POST", "/api/v1/analytics/unanswered/" + u.id + "/add-to-knowledge", { answer: a });
    load();
  }
  const cards = ov ? [
    ["Conversaciones", ov.conversations], ["Mensajes", ov.messages], ["Leads", ov.leads],
    ["Pidieron humano", ov.human_requests], ["Sin respuesta", ov.unanswered],
  ] : [];
  return (
    <div>
      <h1 className="text-2xl font-bold mb-4">Analytics</h1>
      <UsageCard />
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-5">
        {cards.map(([l, n]) => (
          <div key={l} className="bg-slate-800/60 border border-slate-700 rounded-xl p-4">
            <div className="text-2xl font-extrabold text-white">{n}</div>
            <div className="text-slate-400 text-xs">{l}</div>
          </div>
        ))}
      </div>
      <Card title="Preguntas sin respuesta" sub="Lo que el bot no supo. Respondelas para sumarlas a la Knowledge Base.">
        {un.map((u) => (
          <div key={u.id} className="border-b border-slate-700 py-3">
            <div className="text-white text-sm mb-1">{u.question} <span className="text-xs text-slate-500">· {u.count}x</span></div>
            <div className="flex gap-2">
              <input className={inputCls} placeholder="Respuesta correcta…" value={answer[u.id] || ""} onChange={(e) => setAnswer({ ...answer, [u.id]: e.target.value })} />
              <Btn onClick={() => addKb(u)}>Agregar a KB</Btn>
            </div>
          </div>
        ))}
        {!un.length && <p className="text-slate-500">Nada pendiente. 🎉</p>}
      </Card>
    </div>
  );
}

/* ========================= PLANES (admin) ========================= */
function PlanesPage() {
  const [list, setList] = useState([]);
  const [f, setF] = useState({ name: "", price: "", chatbots: "1", conversations: "500", messages: "5000" });
  const [err, setErr] = useState("");
  const load = useCallback(() => api("GET", "/api/v1/admin/plans").then(setList).catch((e) => setErr(e.message)), []);
  useEffect(() => { load(); }, [load]);
  const upd = (k) => (e) => setF({ ...f, [k]: e.target.value });
  async function create() {
    if (!f.name.trim()) return;
    setErr("");
    try {
      await api("POST", "/api/v1/admin/plans", {
        name: f.name.trim(), price: parseFloat(f.price) || 0, currency: "CLP",
        limits: { chatbots: parseInt(f.chatbots) || 1, conversations: parseInt(f.conversations) || 0, messages: parseInt(f.messages) || 0 },
      });
      setF({ name: "", price: "", chatbots: "1", conversations: "500", messages: "5000" }); load();
    } catch (e) { setErr(e.message); }
  }
  async function del(p) { if (!confirm("¿Eliminar el plan " + p.name + "?")) return; try { await api("DELETE", "/api/v1/admin/plans/" + p.id); load(); } catch (e) { setErr(e.message); } }
  return (
    <div>
      <h1 className="text-2xl font-bold mb-4">Planes</h1>
      {err && <div className="text-red-300 mb-3">{err}</div>}
      <Card title="Nuevo plan">
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          <Field label="Nombre"><input className={inputCls} value={f.name} onChange={upd("name")} /></Field>
          <Field label="Precio (CLP)"><input type="number" className={inputCls} value={f.price} onChange={upd("price")} /></Field>
          <Field label="Chatbots"><input type="number" className={inputCls} value={f.chatbots} onChange={upd("chatbots")} /></Field>
          <Field label="Conversaciones/mes"><input type="number" className={inputCls} value={f.conversations} onChange={upd("conversations")} /></Field>
          <Field label="Mensajes/mes"><input type="number" className={inputCls} value={f.messages} onChange={upd("messages")} /></Field>
        </div>
        <Btn onClick={create}>Crear plan</Btn>
      </Card>
      <Card title="Planes disponibles">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead><tr className="text-slate-400 text-left"><th className="py-2">Plan</th><th>Precio</th><th>Chatbots</th><th>Conversaciones</th><th>Mensajes</th><th></th></tr></thead>
            <tbody>
              {list.map((p) => (
                <tr key={p.id} className="border-t border-slate-700">
                  <td className="py-2 text-white">{p.name}</td>
                  <td className="text-slate-300">${p.price} {p.currency}</td>
                  <td className="text-slate-300">{(p.limits || {}).chatbots ?? "—"}</td>
                  <td className="text-slate-300">{(p.limits || {}).conversations ?? "—"}</td>
                  <td className="text-slate-300">{(p.limits || {}).messages ?? "—"}</td>
                  <td className="text-right"><Btn kind="danger" onClick={() => del(p)}>Eliminar</Btn></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}

/* ========================= EMPRESAS (admin) ========================= */
function EmpresasPage({ onManage, onChanged }) {
  const [list, setList] = useState([]);
  const [plans, setPlans] = useState([]);
  const [name, setName] = useState("");
  const [err, setErr] = useState("");
  const load = useCallback(() => {
    api("GET", "/api/v1/admin/companies").then(setList).catch((e) => setErr(e.message));
    api("GET", "/api/v1/admin/plans").then(setPlans).catch(() => {});
  }, []);
  useEffect(() => { load(); }, [load]);
  async function assignPlan(companyId, planId) {
    try { await api("POST", "/api/v1/admin/companies/" + companyId + "/plan", { plan_id: parseInt(planId) }); load(); onChanged && onChanged(); }
    catch (e) { setErr(e.message); }
  }
  async function create() {
    if (!name.trim()) return;
    setErr("");
    try { await api("POST", "/api/v1/admin/companies", { name: name.trim() }); setName(""); load(); onChanged && onChanged(); }
    catch (e) { setErr(e.message); }
  }
  async function toggle(c) {
    try { await api("POST", "/api/v1/admin/companies/" + c.id + "/" + (c.status === "active" ? "suspend" : "activate")); load(); onChanged && onChanged(); }
    catch (e) { setErr(e.message); }
  }
  async function del(c) {
    if (!confirm('¿Eliminar la empresa "' + c.name + '" con todos sus chatbots, conversaciones y datos? No se puede deshacer.')) return;
    try { await api("DELETE", "/api/v1/admin/companies/" + c.id); load(); onChanged && onChanged(); }
    catch (e) { setErr(e.message); }
  }
  return (
    <div>
      <h1 className="text-2xl font-bold mb-4">Empresas</h1>
      {err && <div className="text-red-300 mb-3">{err}</div>}
      <Card title="Nueva empresa" sub="Dala de alta para después armarle su chatbot.">
        <div className="flex gap-2">
          <input className={inputCls} placeholder="Nombre de la empresa (ej: Ferretería López)" value={name}
            onChange={(e) => setName(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter") create(); }} />
          <Btn onClick={create}>Crear empresa</Btn>
        </div>
      </Card>
      <Card title="Todas las empresas">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead><tr className="text-slate-400 text-left"><th className="py-2">Empresa</th><th>Estado</th><th>Chatbots</th><th>Plan</th><th className="text-right">Acciones</th></tr></thead>
            <tbody>
              {list.map((c) => (
                <tr key={c.id} className="border-t border-slate-700">
                  <td className="py-2 text-white">{c.name}</td>
                  <td><span className={"text-xs px-2 py-0.5 rounded-full " + (c.status === "active" ? "bg-emerald-500/20 text-emerald-300" : "bg-slate-600/40 text-slate-400")}>{c.status}</span></td>
                  <td className="text-slate-300">{c.chatbots}</td>
                  <td>
                    <select value={c.plan_id || ""} onChange={(e) => assignPlan(c.id, e.target.value)}
                      className="bg-slate-900 border border-slate-700 rounded-lg px-2 py-1 text-xs text-slate-100">
                      <option value="">Sin plan</option>
                      {plans.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
                    </select>
                  </td>
                  <td>
                    <div className="flex gap-2 justify-end">
                      <Btn kind="primary" onClick={() => onManage(String(c.id))}>Gestionar</Btn>
                      <Btn kind="ghost" onClick={() => toggle(c)}>{c.status === "active" ? "Suspender" : "Activar"}</Btn>
                      <Btn kind="danger" onClick={() => del(c)}>Eliminar</Btn>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {!list.length && <p className="text-slate-500 py-3">No hay empresas. Creá la primera arriba.</p>}
        </div>
      </Card>
    </div>
  );
}

/* ========================= SHELL ========================= */
function Shell({ me, companies, companyId, onSelectCompany, onRefreshCompanies, onLogout }) {
  const isAdmin = me.user.is_platform_admin;
  const [page, setPage] = useState(isAdmin ? "empresas" : "chatbots");
  const [botId, setBotId] = useState(null);
  const baseNav = [["chatbots", "🤖 Chatbots"], ["conversations", "💬 Conversaciones"], ["leads", "📇 Leads"], ["analytics", "📊 Analytics"], ["integraciones", "🔌 Integraciones"]];
  const nav = isAdmin ? [["empresas", "🏢 Empresas"], ["planes", "💳 Planes"], ...baseNav] : baseNav;
  return (
    <div className="min-h-screen flex">
      <aside className="w-60 bg-slate-900 border-r border-slate-800 flex flex-col">
        <div className="p-5 font-extrabold text-lg border-b border-slate-800">⚡ Zelekpress</div>
        {companies.length > 0 ? (
          <div className="px-3 pt-3">
            <div className="text-xs text-slate-500 mb-1">Empresa activa</div>
            <select value={companyId} onChange={(e) => onSelectCompany(e.target.value)}
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-2 py-1.5 text-sm text-slate-100">
              <option value="">— Elegí una empresa —</option>
              {companies.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
          </div>
        ) : (
          <div className="px-3 pt-3 text-xs text-amber-400">Esta cuenta no tiene empresas.{me.user.is_platform_admin ? " Creá una desde una cuenta cliente." : ""}</div>
        )}
        <nav className="flex-1 p-2">
          {nav.map(([k, l]) => (
            <button key={k} onClick={() => { setPage(k); setBotId(null); }}
              className={"w-full text-left px-4 py-2.5 rounded-lg mb-1 " + (page === k ? "bg-slate-800 text-white" : "text-slate-400 hover:bg-slate-800/50")}>{l}</button>
          ))}
        </nav>
        <div className="p-4 border-t border-slate-800 text-sm text-slate-400">
          <div className="mb-2 truncate">{me.user.name}{me.user.is_platform_admin ? " (admin)" : ""}</div>
          <button onClick={onLogout} className="text-red-300">Salir</button>
        </div>
      </aside>
      <main key={(page === "empresas" || page === "planes") ? page : companyId} className="flex-1 p-8 overflow-y-auto max-w-5xl">
        {page === "empresas" ? (
          <EmpresasPage
            onManage={(id) => { onSelectCompany(id); setPage("chatbots"); setBotId(null); }}
            onChanged={onRefreshCompanies}
          />
        ) : page === "planes" ? (
          <PlanesPage />
        ) : (
          <>
            {companyId && (
              <div className="mb-5 inline-flex items-center gap-2 bg-amber-400/10 border border-amber-400/30 text-amber-300 rounded-lg px-3 py-1.5 text-sm">
                🏢 Gestionando: <strong className="text-amber-200">{(companies.find((c) => c.id === companyId) || {}).name || companyId}</strong>
              </div>
            )}
            {!companyId && (
              <div className="bg-slate-800/60 border border-slate-700 rounded-xl p-6 text-slate-300">
                <p className="mb-1 font-semibold">Elegí una empresa para empezar.</p>
                <p className="text-sm text-slate-400">Usá el desplegable <b>“Empresa activa”</b> arriba a la izquierda{isAdmin ? ", o entrá a 🏢 Empresas y tocá “Gestionar”" : ""}. Todo lo que crees o edites (chatbots, conocimiento, etc.) pertenece a la empresa seleccionada.</p>
              </div>
            )}
            {companyId && page === "chatbots" && !botId && <ChatbotsPage onOpen={setBotId} />}
            {companyId && page === "chatbots" && botId && <ChatbotDetail id={botId} onBack={() => setBotId(null)} />}
            {companyId && page === "conversations" && <ConversationsPage />}
            {companyId && page === "leads" && <LeadsPage />}
            {companyId && page === "analytics" && <AnalyticsPage />}
            {companyId && page === "integraciones" && <IntegracionesPage />}
          </>
        )}
      </main>
    </div>
  );
}

/* ========================= APP ========================= */
function App() {
  const [me, setMe] = useState(null);
  const [companies, setCompanies] = useState([]);
  const [companyId, setCompanyId] = useState(LS.company || "");
  const [checking, setChecking] = useState(true);

  // Lista de empresas visibles: el cliente ve la(s) suya(s); el Super Admin
  // ve TODAS las de la plataforma.
  async function fetchCompanies(m) {
    let comps = (m.companies || []).map((c) => ({ id: String(c.company_id), name: c.company_name }));
    if (m.user.is_platform_admin) {
      try {
        const all = await api("GET", "/api/v1/admin/companies");
        comps = all.map((c) => ({ id: String(c.id), name: c.name }));
      } catch (e) { /* sin permiso o vacío */ }
    }
    return comps;
  }

  async function loadSession() {
    const m = await api("GET", "/api/v1/auth/me");
    const comps = await fetchCompanies(m);
    // Empresa activa: se mantiene la última si sigue siendo válida (para no
    // perderla al recargar). Si no, el cliente entra a la suya; el admin
    // arranca SIN empresa (elige a conciencia).
    let cid = LS.company;
    if (!comps.find((c) => c.id === cid)) {
      cid = m.user.is_platform_admin ? "" : (comps[0] ? comps[0].id : "");
    }
    LS.company = cid;
    setMe(m); setCompanies(comps); setCompanyId(cid);
  }

  async function refreshCompanies() {
    if (!me) return;
    setCompanies(await fetchCompanies(me));
  }

  useEffect(() => {
    if (LS.token) loadSession().catch(() => { LS.token = ""; }).finally(() => setChecking(false));
    else setChecking(false);
  }, []);

  function logout() { LS.token = ""; LS.company = ""; setMe(null); setCompanies([]); setCompanyId(""); }
  function selectCompany(id) { LS.company = id; setCompanyId(id); }

  if (checking) return <div className="min-h-screen flex items-center justify-center text-slate-500">Cargando…</div>;
  if (!me) return <Login onLogged={() => { LS.company = ""; loadSession(); }} />;
  return <Shell me={me} companies={companies} companyId={companyId}
    onSelectCompany={selectCompany} onRefreshCompanies={refreshCompanies} onLogout={logout} />;
}

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
