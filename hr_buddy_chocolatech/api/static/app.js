// Frontend JavaScript para HR Buddy (ChocolaTech)

let currentSessionId = "web-session-" + Math.floor(Math.random() * 10000);

document.addEventListener("DOMContentLoaded", () => {
  const sessionIdDisplay = document.getElementById("sessionIdDisplay");
  const chatFeed = document.getElementById("chatFeed");
  const userInput = document.getElementById("userInput");
  const btnSend = document.getElementById("btnSend");
  const btnResetSession = document.getElementById("btnResetSession");

  sessionIdDisplay.textContent = currentSessionId;

  // Enviar mensaje
  btnSend.addEventListener("click", () => sendMessage());

  userInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  // Botón reiniciar sesión
  btnResetSession.addEventListener("click", async () => {
    try {
      await fetch("/api/reset", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: currentSessionId })
      });
      currentSessionId = "web-session-" + Math.floor(Math.random() * 10000);
      sessionIdDisplay.textContent = currentSessionId;
      chatFeed.innerHTML = `
        <div class="welcome-card">
          <div class="welcome-badge">🔄 Sesión Reiniciada</div>
          <h2>Memoria Limpia</h2>
          <p>Se ha iniciado una nueva sesión independiente. Puedes presentarte o consultar cualquier política.</p>
        </div>
      `;
    } catch (e) {
      console.error("Error al reiniciar sesión:", e);
    }
  });

  // Chips de empleados
  document.querySelectorAll(".emp-chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      const name = chip.getAttribute("data-name");
      userInput.value = `Hola, soy ${name}. ¿Podrías indicarme mis saldos actuales de vacaciones y banco de horas?`;
      userInput.focus();
    });
  });

  // Botones de sugerencias
  document.querySelectorAll(".suggestion-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const prompt = btn.getAttribute("data-prompt");
      userInput.value = prompt;
      sendMessage();
    });
  });

  async function sendMessage() {
    const text = userInput.value.trim();
    if (!text) return;

    // Agregar mensaje del usuario a la vista
    appendMessage("user", text);
    userInput.value = "";
    userInput.disabled = true;
    btnSend.disabled = true;

    // Indicador temporal de carga
    const loadingId = appendLoadingIndicator();

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: currentSessionId,
          message: text
        })
      });

      const data = await res.json();
      removeLoadingIndicator(loadingId);

      // Renderizar respuesta del bot
      appendBotResponse(data);
    } catch (err) {
      removeLoadingIndicator(loadingId);
      appendMessage("bot", `⚠️ Ocurrió un error de conexión con HR Buddy: ${err.message}`);
    } finally {
      userInput.disabled = false;
      btnSend.disabled = false;
      userInput.focus();
    }
  }

  function appendMessage(role, text) {
    const row = document.createElement("div");
    row.className = `message-row ${role}`;

    const avatar = document.createElement("div");
    avatar.className = "msg-avatar";
    avatar.textContent = role === "user" ? "👤" : "🍫";

    const bubble = document.createElement("div");
    bubble.className = "msg-bubble";
    bubble.innerHTML = window.marked ? window.marked.parse(text) : `<p>${text}</p>`;

    row.appendChild(avatar);
    row.appendChild(bubble);

    chatFeed.appendChild(row);
    chatFeed.scrollTop = chatFeed.scrollHeight;
  }

  function appendBotResponse(data) {
    const row = document.createElement("div");
    row.className = "message-row bot";

    const avatar = document.createElement("div");
    avatar.className = "msg-avatar";
    avatar.textContent = "🍫";

    const bubble = document.createElement("div");
    bubble.className = "msg-bubble";

    const contentHtml = window.marked ? window.marked.parse(data.answer) : `<p>${data.answer}</p>`;
    bubble.innerHTML = contentHtml;

    // Metadatos y badges
    const meta = document.createElement("div");
    meta.className = "msg-meta";

    if (data.guardrails_passed === false) {
      meta.innerHTML += `<span class="meta-chip guardrail-blocked">🛡️ Guardrail Bloqueado (${data.guardrail_reason || "off-topic"})</span>`;
    } else {
      meta.innerHTML += `<span class="meta-chip">✅ Guardrail Aprobado</span>`;
    }

    if (data.employee) {
      meta.innerHTML += `<span class="meta-chip emp-found">👤 ${data.employee.nombre} (${data.employee.departamento})</span>`;
    }

    if (data.sources && data.sources.length > 0) {
      meta.innerHTML += `<span class="meta-chip">📚 RAG: ${data.sources.join(", ")}</span>`;
    }

    bubble.appendChild(meta);
    row.appendChild(avatar);
    row.appendChild(bubble);

    chatFeed.appendChild(row);
    chatFeed.scrollTop = chatFeed.scrollHeight;
  }

  function appendLoadingIndicator() {
    const id = "loading-" + Date.now();
    const row = document.createElement("div");
    row.id = id;
    row.className = "message-row bot";
    row.innerHTML = `
      <div class="msg-avatar">🍫</div>
      <div class="msg-bubble" style="color: var(--text-muted); font-style: italic;">
        Consultando sistemas de Recursos Humanos y políticas corporativas...
      </div>
    `;
    chatFeed.appendChild(row);
    chatFeed.scrollTop = chatFeed.scrollHeight;
    return id;
  }

  function removeLoadingIndicator(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
  }
});
