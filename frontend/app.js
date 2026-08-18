const API_URL = "http://127.0.0.1:8000";

const COMPANY_ID = 1;

let conversationId = null;


const messagesContainer =
    document.getElementById("messages");

const messageInput =
    document.getElementById("messageInput");

const sendButton =
    document.getElementById("sendButton");


function addMessage(
    text,
    type
) {

    const message =
        document.createElement("div");

    message.className =
        `message ${type}`;

    message.textContent =
        text;

    messagesContainer.appendChild(
        message
    );

    messagesContainer.scrollTop =
        messagesContainer.scrollHeight;
}


async function sendMessage() {

    const message =
        messageInput.value.trim();


    if (!message) {
        return;
    }


    addMessage(
        message,
        "user"
    );


    messageInput.value = "";

    sendButton.disabled = true;


    try {

        const response =
            await fetch(
                `${API_URL}/chat`,
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body: JSON.stringify({

                        company_id:
                            COMPANY_ID,

                        conversation_id:
                            conversationId,

                        message:
                            message

                    })
                }
            );


        const data =
            await response.json();


        if (!response.ok) {

            throw new Error(
                data.detail ||
                data.error ||
                "Error del servidor"
            );

        }


        conversationId =
            data.conversation_id;


        addMessage(
            data.response,
            "assistant"
        );


    } catch (error) {

        console.error(error);

        addMessage(
            "Lo siento, ocurrió un error al conectar con el asistente.",
            "assistant"
        );

    }


    sendButton.disabled = false;

    messageInput.focus();
}


sendButton.addEventListener(
    "click",
    sendMessage
);


messageInput.addEventListener(
    "keydown",
    function(event) {

        if (event.key === "Enter") {

            sendMessage();

        }

    }
);