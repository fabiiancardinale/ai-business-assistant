/* =====================================================================
   ZELEKPRESS CHATBOT WIDGET  (Fase 4)
   Se instala en cualquier sitio con:
     <script src="https://app.zelekpress.com/widget/widget.js"
             data-chatbot-id="123"
             data-api="https://api.zelekpress.com"></script>

   - Todo el DOM/CSS vive dentro de un Shadow DOM => NO choca con el sitio
     anfitrión (Bootstrap, Tailwind, WordPress, jQuery, etc.).
   - La apariencia y textos vienen del backend (config pública) — nada
     hardcodeado y ningún secreto en el navegador.
   ===================================================================== */
(function () {
  "use strict";

  // ---- 1. Leer configuración del <script> ----
  var script = document.currentScript;
  if (!script) {
    // fallback: buscar el último script con data-chatbot-id
    var all = document.querySelectorAll("script[data-chatbot-id]");
    script = all[all.length - 1];
  }
  if (!script) return;

  var chatbotId = script.getAttribute("data-chatbot-id");
  if (!chatbotId) { console.warn("[Zelekpress] falta data-chatbot-id"); return; }

  // API base: data-api, o el origen desde donde se sirvió el widget.
  var API = script.getAttribute("data-api");
  if (!API) {
    try { API = new URL(script.src).origin; } catch (e) { API = ""; }
  }
  API = API.replace(/\/$/, "");

  // Evitar doble carga
  if (window.__zpWidgetLoaded === chatbotId) return;
  window.__zpWidgetLoaded = chatbotId;

  // ---- 2. Traer config pública y arrancar ----
  fetch(API + "/api/v1/public/chatbots/" + encodeURIComponent(chatbotId) + "/config")
    .then(function (r) { if (!r.ok) throw new Error("config " + r.status); return r.json(); })
    .then(function (cfg) { init(cfg); })
    .catch(function (e) { console.warn("[Zelekpress] no se pudo cargar el chatbot:", e.message); });

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
    });
  }

  // ---- 3. Inicializar el widget dentro de un Shadow DOM ----
  function init(cfg) {
    var t = cfg.appearance || {};
    var colors = t.colors || {}, layout = t.layout || {}, launcher = t.launcher || {},
        header = t.header || {}, messages = t.messages || {};
    var side = layout.side === "left" ? "left" : "right";
    var offset = (launcher.position_side != null ? launcher.position_side : 24);
    var img = launcher.image || null;

    // Host aislado
    var host = document.createElement("div");
    host.setAttribute("data-zp-widget", chatbotId);
    host.style.cssText = "all:initial;";
    document.body.appendChild(host);
    var root = host.attachShadow ? host.attachShadow({ mode: "open" }) : host;

    var launcherInner = img
      ? '<img src="' + esc(img) + '" alt="" style="width:100%;height:100%;object-fit:cover;border-radius:50%;">'
      : (launcher.icon || "💬");
    var headerLogo = img
      ? '<img src="' + esc(img) + '" alt="" style="width:100%;height:100%;object-fit:cover;">'
      : '<span style="font-size:18px;">' + (launcher.icon || "🤖") + "</span>";

    var css = ""
      + ":host{ all:initial; }"
      + "*{ box-sizing:border-box; font-family:" + (messages.font || "Inter,system-ui,Arial,sans-serif") + "; }"
      + ".zp-launcher{ position:fixed; bottom:" + (launcher.position_bottom || 24) + "px; " + side + ":" + offset + "px;"
      + "  width:" + (launcher.size || 60) + "px; height:" + (launcher.size || 60) + "px; border-radius:50%; border:none; cursor:pointer;"
      + "  background:" + (img ? "transparent" : (launcher.color || "#F0C030")) + "; color:#fff; overflow:hidden; padding:0;"
      + "  display:flex; align-items:center; justify-content:center; font-size:" + Math.round((launcher.size || 60) * 0.42) + "px;"
      + "  box-shadow:0 8px 24px rgba(0,0,0,.3); z-index:2147483000; transition:transform .2s; }"
      + ".zp-launcher:hover{ transform:scale(1.07); }"
      + ".zp-panel{ position:fixed; bottom:" + ((launcher.position_bottom || 24) + (launcher.size || 60) + 14) + "px; " + side + ":" + offset + "px;"
      + "  width:" + (layout.width || 370) + "px; max-width:calc(100vw - 32px); height:" + (layout.height || 560) + "px; max-height:calc(100vh - 120px);"
      + "  background:" + (colors.background || "#fff") + "; color:" + (colors.text || "#111827") + "; border-radius:" + (layout.radius || 18) + "px;"
      + "  box-shadow:" + (layout.shadow === false ? "none" : "0 20px 50px rgba(0,0,0,.28)") + "; overflow:hidden; z-index:2147483000;"
      + "  display:flex; flex-direction:column; opacity:0; visibility:hidden; transform:translateY(16px) scale(.98);"
      + "  transition:opacity .2s, transform .2s, visibility .2s; }"
      + ".zp-panel.open{ opacity:1; visibility:visible; transform:none; }"
      + ".zp-header{ background:" + (header.bg_color || "#1a1310") + "; color:" + (header.text_color || "#fff") + ";"
      + "  padding:14px 16px; display:flex; align-items:center; gap:10px; }"
      + ".zp-logo{ width:34px; height:34px; border-radius:50%; background:" + (colors.primary || "#F0C030") + ";"
      + "  display:flex; align-items:center; justify-content:center; overflow:hidden; flex-shrink:0; }"
      + ".zp-title{ font-weight:700; font-size:15px; }"
      + ".zp-status{ font-size:12px; opacity:.85; display:flex; align-items:center; gap:5px; }"
      + ".zp-dot{ width:7px; height:7px; border-radius:50%; background:#22c55e; display:inline-block; }"
      + ".zp-close{ margin-left:auto; background:transparent; border:none; color:inherit; font-size:22px; cursor:pointer; line-height:1; }"
      + ".zp-msgs{ flex:1; padding:16px; overflow-y:auto; background:#f8fafc; display:flex; flex-direction:column; gap:" + (messages.spacing || 10) + "px; }"
      + ".zp-row{ display:flex; }"
      + ".zp-row.user{ justify-content:flex-end; }"
      + ".zp-bubble{ max-width:80%; padding:10px 13px; font-size:" + (messages.size || 14) + "px; line-height:1.5; border-radius:14px 14px 14px 4px;"
      + "  background:" + (colors.bot_bubble || "#f1f2f6") + "; color:" + (colors.bot_text || "#111827") + "; white-space:pre-wrap; word-wrap:break-word; }"
      + ".zp-row.user .zp-bubble{ background:" + (colors.user_bubble || "#111827") + "; color:" + (colors.user_text || "#fff") + "; border-radius:14px 14px 4px 14px; }"
      + ".zp-input{ display:flex; gap:8px; padding:12px; border-top:1px solid #e5e7eb; background:#fff; }"
      + ".zp-input input{ flex:1; height:40px; border:1px solid #d1d5db; border-radius:10px; padding:0 12px; font-size:14px; outline:none; color:#111827; }"
      + ".zp-send{ width:40px; height:40px; border:none; border-radius:10px; background:" + (colors.primary || "#F0C030") + "; color:#fff; cursor:pointer; font-size:16px; }"
      + ".zp-typing{ display:flex; gap:4px; padding:10px 13px; }"
      + ".zp-typing span{ width:6px; height:6px; border-radius:50%; background:#9ca3af; animation:zpblink 1.2s infinite; }"
      + ".zp-typing span:nth-child(2){ animation-delay:.15s; } .zp-typing span:nth-child(3){ animation-delay:.3s; }"
      + "@keyframes zpblink{ 0%,60%,100%{opacity:.35;} 30%{opacity:1;} }";

    var wrap = document.createElement("div");
    wrap.innerHTML =
      "<style>" + css + "</style>" +
      '<div class="zp-panel" part="panel">' +
      '  <div class="zp-header">' +
      (header.show_logo === false ? "" : '<div class="zp-logo">' + headerLogo + "</div>") +
      "    <div><div class=\"zp-title\">" + esc(header.title || cfg.name_public || "Asistente") + "</div>" +
      '    <div class="zp-status"><span class="zp-dot"></span>' + esc(header.subtitle || "En línea") + "</div></div>" +
      '    <button class="zp-close" aria-label="Cerrar">&times;</button>' +
      "  </div>" +
      '  <div class="zp-msgs"></div>' +
      '  <div class="zp-input">' +
      '    <input type="text" placeholder="Escribí un mensaje..." aria-label="Mensaje">' +
      '    <button class="zp-send" aria-label="Enviar">➤</button>' +
      "  </div>" +
      "</div>" +
      '<button class="zp-launcher" aria-label="Abrir chat">' + launcherInner + "</button>";
    root.appendChild(wrap);

    var panel = root.querySelector(".zp-panel");
    var msgs = root.querySelector(".zp-msgs");
    var input = root.querySelector(".zp-input input");
    var sendBtn = root.querySelector(".zp-send");
    var launcherBtn = root.querySelector(".zp-launcher");
    var closeBtn = root.querySelector(".zp-close");

    var sessionId = null;
    var opened = false;

    function addBubble(text, who) {
      var row = document.createElement("div");
      row.className = "zp-row " + who;
      row.innerHTML = '<div class="zp-bubble">' + esc(text) + "</div>";
      msgs.appendChild(row);
      msgs.scrollTop = msgs.scrollHeight;
      return row;
    }
    function showTyping() {
      var row = document.createElement("div");
      row.className = "zp-row bot zp-typing-row";
      row.innerHTML = '<div class="zp-bubble zp-typing"><span></span><span></span><span></span></div>';
      msgs.appendChild(row);
      msgs.scrollTop = msgs.scrollHeight;
      return row;
    }

    function openPanel() {
      panel.classList.add("open");
      launcherBtn.style.display = "none";
      input.focus();
      if (!opened) {
        opened = true;
        // crear sesión y mostrar saludo
        fetch(API + "/api/v1/public/chatbots/" + chatbotId + "/session", { method: "POST" })
          .then(function (r) { return r.json(); })
          .then(function (s) {
            sessionId = s.session_id;
            if (s.greeting) addBubble(s.greeting, "bot");
          })
          .catch(function () {
            if (cfg.greeting_message) addBubble(cfg.greeting_message, "bot");
          });
      }
    }
    function closePanel() {
      panel.classList.remove("open");
      launcherBtn.style.display = "flex";
    }

    function send() {
      var text = (input.value || "").trim();
      if (!text) return;
      addBubble(text, "user");
      input.value = "";
      var typing = showTyping();
      fetch(API + "/api/v1/public/chatbots/" + chatbotId + "/message", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text, session_id: sessionId })
      })
        .then(function (r) { return r.json(); })
        .then(function (d) {
          typing.remove();
          sessionId = d.session_id || sessionId;
          addBubble(d.reply || "…", "bot");
        })
        .catch(function () {
          typing.remove();
          addBubble("No pude responder en este momento. Probá de nuevo.", "bot");
        });
    }

    launcherBtn.addEventListener("click", openPanel);
    closeBtn.addEventListener("click", closePanel);
    sendBtn.addEventListener("click", send);
    input.addEventListener("keydown", function (e) { if (e.key === "Enter") send(); });
  }
})();
