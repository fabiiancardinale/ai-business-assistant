(function () {

    "use strict";

    console.log("AI Business Assistant: iniciando widget...");


    // =====================================================
    // OBTENER SCRIPT ACTUAL
    // =====================================================

    const currentScript = document.currentScript;

    if (!currentScript) {

        console.error(
            "AI Business Assistant: no se pudo detectar el script."
        );

        return;
    }


    // =====================================================
    // CONFIGURACIÓN
    // =====================================================

const apiKey =
    currentScript.getAttribute("data-api-key");

const apiUrl =
    currentScript.getAttribute("data-api-url") ||
    "https://api.zelekpress.com";

const botName =
    currentScript.getAttribute("data-bot-name") ||
    "Asistente IA";

const color =
    currentScript.getAttribute("data-color") ||
    "#111827";


    console.log(
        "AI Business Assistant: configuración cargada",
        {
            apiUrl: apiUrl,
            botName: botName
        }
    );


    // =====================================================
    // VALIDAR API KEY
    // =====================================================

    if (!apiKey) {

        console.error(
            "AI Business Assistant: falta data-api-key."
        );

        return;
    }


    // =====================================================
    // CREAR CONTENEDOR AUTOMÁTICAMENTE
    // =====================================================

    let container =
        document.getElementById(
            "ai-business-assistant"
        );


    if (!container) {

        console.warn(
            "AI Business Assistant: no existe #ai-business-assistant. Creándolo automáticamente."
        );

        container =
            document.createElement("div");

        container.id =
            "ai-business-assistant";

        document.body.appendChild(
            container
        );

    }


    // =====================================================
    // CARGAR CSS
    // =====================================================

    function loadCSS() {

        const existing =
            document.querySelector(
                'link[data-ai-business-assistant="true"]'
            );

        if (existing) {
            return;
        }


        const link =
            document.createElement("link");

        link.rel =
            "stylesheet";

        // Ruta absoluta resuelta a partir del propio script (currentScript.src),
        // así el CSS siempre se pide al dominio del widget, sin importar en qué
        // sitio esté instalado (antes esto era "style.css" relativo, y por eso
        // el navegador terminaba pidiéndolo al dominio de la página cliente).
        link.href =
            new URL("style.css", currentScript.src).href;

        link.setAttribute(
            "data-ai-business-assistant",
            "true"
        );

        document.head.appendChild(
            link
        );

    }


    loadCSS();


    // =====================================================
    // HTML DEL WIDGET
    // =====================================================

    container.innerHTML = `

        <div class="aiba-widget">

            <button
                type="button"
                class="aiba-button"
                id="aiba-open"
                style="background-color: ${color};"
                aria-label="Abrir asistente"
            >
                💬
            </button>


            <div
                class="aiba-chat"
                id="aiba-chat"
            >

                <div
                    class="aiba-header"
                    style="background-color: ${color};"
                >

                    <div class="aiba-header-info">

                        <div class="aiba-bot-name">
                            ${botName}
                        </div>

                        <div class="aiba-status">
                            <span class="aiba-status-dot"></span>
                            En línea
                        </div>

                    </div>


                    <button
                        type="button"
                        class="aiba-close"
                        id="aiba-close"
                        aria-label="Cerrar"
                    >
                        ×
                    </button>

                </div>


                <div
                    class="aiba-messages"
                    id="aiba-messages"
                >

                </div>


                <div class="aiba-input-area">

                    <input
                        type="text"
                        id="aiba-input"
                        class="aiba-input"
                        placeholder="Escribe tu mensaje..."
                        autocomplete="off"
                    />


                    <button
                        type="button"
                        id="aiba-send"
                        class="aiba-send"
                        style="background-color: ${color};"
                        aria-label="Enviar mensaje"
                    >
                        ➤
                    </button>

                </div>

            </div>

        </div>

    `;


    // =====================================================
    // ELEMENTOS
    // =====================================================

    const openButton =
        document.getElementById(
            "aiba-open"
        );

    const closeButton =
        document.getElementById(
            "aiba-close"
        );

    const chat =
        document.getElementById(
            "aiba-chat"
        );

    const messages =
        document.getElementById(
            "aiba-messages"
        );

    const input =
        document.getElementById(
            "aiba-input"
        );

    const sendButton =
        document.getElementById(
            "aiba-send"
        );


    // =====================================================
    // VALIDACIÓN
    // =====================================================

    if (
        !openButton ||
        !closeButton ||
        !chat ||
        !messages ||
        !input ||
        !sendButton
    ) {

        console.error(
            "AI Business Assistant: no se pudo crear correctamente la interfaz."
        );

        return;
    }


    // =====================================================
    // CONVERSACIÓN
    // =====================================================

    let conversationId = null;


    // =====================================================
    // AGREGAR MENSAJE
    //
    // Devuelve el elemento "bubble" creado, para que quien
    // llama pueda seguir escribiendo texto adentro (usado por
    // la respuesta en stream, que va llegando de a pedazos).
    // =====================================================

    function addMessage(
        text,
        type
    ) {

        const message =
            document.createElement("div");

        message.className =
            "aiba-message " + type;


        const bubble =
            document.createElement("div");

        bubble.className =
            "aiba-bubble";


        bubble.textContent =
            text;


        message.appendChild(
            bubble
        );


        messages.appendChild(
            message
        );


        messages.scrollTop =
            messages.scrollHeight;


        return bubble;

    }


    // =====================================================
    // MENSAJE INICIAL
    // =====================================================

    addMessage(
        "Hola 👋 ¿En qué puedo ayudarte?",
        "bot"
    );


    // =====================================================
    // ABRIR CHAT
    // =====================================================

    openButton.addEventListener(
        "click",
        function () {

            chat.classList.add(
                "aiba-visible"
            );

            input.focus();

        }
    );


    // =====================================================
    // CERRAR CHAT
    // =====================================================

    closeButton.addEventListener(
        "click",
        function () {

            chat.classList.remove(
                "aiba-visible"
            );

        }
    );


    // =====================================================
    // TYPING
    // =====================================================

    function showTyping() {

        removeTyping();


        const typing =
            document.createElement("div");

        typing.id =
            "aiba-typing";

        typing.className =
            "aiba-message bot";


        typing.innerHTML = `

            <div class="aiba-bubble aiba-typing">

                <span></span>
                <span></span>
                <span></span>

            </div>

        `;


        messages.appendChild(
            typing
        );


        messages.scrollTop =
            messages.scrollHeight;

    }


    function removeTyping() {

        const typing =
            document.getElementById(
                "aiba-typing"
            );

        if (typing) {

            typing.remove();

        }

    }


    // =====================================================
    // ENVIAR MENSAJE
    // =====================================================

    async function sendMessage() {

        const message =
            input.value.trim();


        if (!message) {

            return;

        }


        // Mostrar mensaje del usuario

        addMessage(
            message,
            "user"
        );


        input.value = "";

        input.disabled = true;

        sendButton.disabled = true;


        showTyping();


        try {

            console.log(
                "AI Business Assistant: enviando mensaje..."
            );


            const response =
                await fetch(
                    apiUrl + "/api/chat",
                    {

                        method: "POST",

                        headers: {

                            "Content-Type":
                                "application/json",

                            "X-API-Key":
                                apiKey

                        },

                        body:
                            JSON.stringify({

                                message:
                                    message,

                                conversation_id:
                                    conversationId

                            })

                    }
                );


            removeTyping();


            // =============================================
            // ERROR API
            //
            // Si falla, la respuesta sigue siendo JSON normal
            // (el backend solo hace streaming cuando todo salió
            // bien), así que acá sí se puede leer con .json().
            // =============================================

            if (!response.ok) {

                let detail =
                    "Ocurrió un error al comunicarse con el asistente.";

                try {

                    const errorData =
                        await response.json();

                    detail =
                        errorData.detail || detail;

                } catch (parseError) {
                    // si ni siquiera es JSON, se deja el mensaje genérico
                }

                addMessage(
                    detail,
                    "bot"
                );

                return;
            }


            // =============================================
            // GUARDAR CONVERSACIÓN
            //
            // Ahora viaja en un header en vez de en el JSON,
            // porque el cuerpo de la respuesta es el texto que
            // va llegando en stream.
            // =============================================

            const headerConversationId =
                response.headers.get("X-Conversation-Id");

            if (headerConversationId) {

                conversationId =
                    Number(headerConversationId);

            }


            // =============================================
            // LEER Y MOSTRAR RESPUESTA EN STREAM
            //
            // Se crea una burbuja vacía y se va rellenando con
            // cada pedazo de texto que llega, en vez de esperar
            // a que la respuesta esté completa.
            // =============================================

            const bubble =
                addMessage("", "bot");

            const reader =
                response.body.getReader();

            const decoder =
                new TextDecoder("utf-8");

            let fullText = "";

            while (true) {

                const { value, done } =
                    await reader.read();

                if (done) {
                    break;
                }

                fullText +=
                    decoder.decode(value, { stream: true });

                bubble.textContent =
                    fullText;

                messages.scrollTop =
                    messages.scrollHeight;

            }

            if (!fullText) {

                bubble.textContent =
                    "No recibí una respuesta.";

            }

        }

        catch (error) {

            console.error(
                "AI Business Assistant: error de conexión",
                error
            );


            removeTyping();


            addMessage(
                "No pude conectarme con el asistente.",
                "bot"
            );

        }

        finally {

            input.disabled =
                false;

            sendButton.disabled =
                false;

            input.focus();

        }

    }


    // =====================================================
    // BOTÓN ENVIAR
    // =====================================================

    sendButton.addEventListener(
        "click",
        sendMessage
    );


    // =====================================================
    // ENTER
    // =====================================================

    input.addEventListener(
        "keydown",
        function (event) {

            if (
                event.key === "Enter"
            ) {

                event.preventDefault();

                sendMessage();

            }

        }
    );


    // =====================================================
    // FINAL
    // =====================================================

    console.log(
        "AI Business Assistant: widget cargado correctamente ✅"
    );

})();