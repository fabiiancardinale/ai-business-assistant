// El portal se sirve desde el mismo dominio que la API
// (https://api.zelekpress.com/portal), así que las rutas son
// relativas — el navegador ya sabe a qué servidor pedirlas.
const API_URL = "";

// Dominio donde vive el widget.js que se instala en el sitio del
// cliente. Es el mismo para todas las empresas.
const WIDGET_SCRIPT_URL = "https://widget.zelekpress.com/widget.js";


/* =========================
   ELEMENTOS
========================= */

const portalCompanyName =
    document.getElementById("portalCompanyName");

const installSnippet =
    document.getElementById("installSnippet");

const copySnippet =
    document.getElementById("copySnippet");

const copySnippetStatus =
    document.getElementById("copySnippetStatus");

const knowledge =
    document.getElementById("knowledge");

const saveKnowledge =
    document.getElementById("saveKnowledge");

const saveStatus =
    document.getElementById("saveStatus");

const companyColor =
    document.getElementById("companyColor");

const companyIcon =
    document.getElementById("companyIcon");

const companyIconBackground =
    document.getElementById("companyIconBackground");

const appearancePreviewButton =
    document.getElementById("appearancePreviewButton");

const saveAppearance =
    document.getElementById("saveAppearance");

const appearanceStatus =
    document.getElementById("appearanceStatus");

const companyIconFile =
    document.getElementById("companyIconFile");

const uploadIconButton =
    document.getElementById("uploadIconButton");

const uploadIconStatus =
    document.getElementById("uploadIconStatus");


let currentIconImageUrl = null;
let currentCompany = null;


/* =========================
   CÓDIGO DE INSTALACIÓN
========================= */

function buildInstallSnippet(company) {

    const apiKey =
        company.api_key || "TU_API_KEY";

    const color =
        company.primary_color || "#111827";

    return (
        `<script\n` +
        `    src="${WIDGET_SCRIPT_URL}"\n` +
        `    data-api-key="${apiKey}"\n` +
        `    data-bot-name="Asistente ${company.name}"\n` +
        `    data-color="${color}"\n` +
        `></script>`
    );

}


if (copySnippet) {

    copySnippet.addEventListener(
        "click",
        async () => {

            try {

                await navigator.clipboard.writeText(
                    installSnippet.textContent
                );

                copySnippetStatus.textContent =
                    "✓ Copiado";

                copySnippetStatus.style.color =
                    "#16a34a";

            } catch (error) {

                copySnippetStatus.textContent =
                    "✕ No se pudo copiar, seleccioná el texto a mano";

                copySnippetStatus.style.color =
                    "#dc2626";

            }

            setTimeout(
                () => {
                    copySnippetStatus.textContent = "";
                },
                3000
            );

        }
    );

}


/* =========================
   CARGAR MIS DATOS
========================= */

async function loadMe() {

    const response =
        await fetch(`${API_URL}/me`);

    if (!response.ok) {

        throw new Error(
            "No se pudieron cargar tus datos. Revisá tu email y contraseña."
        );

    }

    const data =
        await response.json();

    currentCompany = data;


    portalCompanyName.textContent =
        data.name;

    document.title =
        `${data.name} — Mi Asistente IA`;


    installSnippet.textContent =
        buildInstallSnippet(data);


    knowledge.value =
        data.knowledge || "";


    companyColor.value =
        data.primary_color || "#111827";

    companyIconBackground.checked =
        data.icon_has_background !== false;


    const iconIsImage =
        !!data.icon &&
        (
            data.icon.startsWith("/") ||
            data.icon.startsWith("http")
        );

    if (iconIsImage) {

        currentIconImageUrl = data.icon;
        companyIcon.value = "";

    } else {

        currentIconImageUrl = null;
        companyIcon.value = data.icon || "💬";

    }


    updateAppearancePreview();

}


/* =========================
   GUARDAR CONOCIMIENTO
========================= */

if (saveKnowledge) {

    saveKnowledge.addEventListener(
        "click",
        async () => {

            saveKnowledge.disabled = true;

            saveStatus.textContent = "Guardando...";
            saveStatus.style.color = "#6b7280";

            try {

                const response =
                    await fetch(
                        `${API_URL}/me/knowledge`,
                        {
                            method: "PUT",
                            headers: {
                                "Content-Type": "application/json"
                            },
                            body: JSON.stringify({
                                knowledge: knowledge.value
                            })
                        }
                    );

                if (!response.ok) {

                    const data =
                        await response.json().catch(() => ({}));

                    throw new Error(
                        data.detail || "No se pudo guardar"
                    );

                }

                saveStatus.textContent = "✓ Guardado correctamente";
                saveStatus.style.color = "#16a34a";

                setTimeout(
                    () => { saveStatus.textContent = ""; },
                    3000
                );

            } catch (error) {

                saveStatus.textContent = "✕ " + error.message;
                saveStatus.style.color = "#dc2626";

            } finally {

                saveKnowledge.disabled = false;

            }

        }
    );

}


/* =========================
   VISTA PREVIA EN VIVO
========================= */

function updateAppearancePreview() {

    if (!appearancePreviewButton) {
        return;
    }

    const showBackground =
        !currentIconImageUrl ||
        companyIconBackground.checked;

    appearancePreviewButton.style.background =
        showBackground
            ? (companyColor.value || "#111827")
            : "transparent";

    appearancePreviewButton.style.boxShadow =
        showBackground ? "" : "none";


    if (currentIconImageUrl) {

        appearancePreviewButton.innerHTML =
            `<img src="${currentIconImageUrl}" alt="ícono">`;

    } else {

        appearancePreviewButton.textContent =
            companyIcon.value.trim() || "💬";

    }

}


if (companyColor) {

    companyColor.addEventListener(
        "input",
        updateAppearancePreview
    );

}


if (companyIcon) {

    companyIcon.addEventListener(
        "input",
        () => {

            currentIconImageUrl = null;
            updateAppearancePreview();

        }
    );

}


if (companyIconBackground) {

    companyIconBackground.addEventListener(
        "change",
        updateAppearancePreview
    );

}


/* =========================
   GUARDAR APARIENCIA
========================= */

if (saveAppearance) {

    saveAppearance.addEventListener(
        "click",
        async () => {

            saveAppearance.disabled = true;

            appearanceStatus.textContent = "Guardando...";
            appearanceStatus.style.color = "#6b7280";

            try {

                const response =
                    await fetch(
                        `${API_URL}/me/appearance`,
                        {
                            method: "PUT",
                            headers: {
                                "Content-Type": "application/json"
                            },
                            // Si el campo de emoji está vacío, no se
                            // manda "icon", para no pisar una imagen
                            // subida antes.
                            body: JSON.stringify({
                                primary_color: companyColor.value,
                                icon: companyIcon.value.trim() || null,
                                icon_has_background: companyIconBackground.checked
                            })
                        }
                    );

                if (!response.ok) {

                    const data =
                        await response.json().catch(() => ({}));

                    throw new Error(
                        data.detail || "No se pudo guardar"
                    );

                }


                const data = await response.json();

                installSnippet.textContent =
                    buildInstallSnippet({
                        ...currentCompany,
                        primary_color: data.primary_color
                    });


                appearanceStatus.textContent = "✓ Guardado correctamente";
                appearanceStatus.style.color = "#16a34a";

                setTimeout(
                    () => { appearanceStatus.textContent = ""; },
                    3000
                );

            } catch (error) {

                appearanceStatus.textContent = "✕ " + error.message;
                appearanceStatus.style.color = "#dc2626";

            } finally {

                saveAppearance.disabled = false;

            }

        }
    );

}


/* =========================
   SUBIR ÍCONO (IMAGEN)
========================= */

if (uploadIconButton) {

    uploadIconButton.addEventListener(
        "click",
        async () => {

            const file =
                companyIconFile.files[0];

            if (!file) {

                alert(
                    "Elegí primero una imagen (PNG, JPG o WEBP)."
                );

                return;

            }

            uploadIconButton.disabled = true;

            uploadIconStatus.textContent = "Subiendo...";
            uploadIconStatus.style.color = "#6b7280";

            try {

                const formData = new FormData();
                formData.append("file", file);

                const response =
                    await fetch(
                        `${API_URL}/me/icon`,
                        {
                            method: "POST",
                            body: formData
                        }
                    );

                const data =
                    await response.json();

                if (!response.ok) {

                    throw new Error(
                        data.detail || "No se pudo subir la imagen"
                    );

                }

                currentIconImageUrl = data.icon;
                companyIcon.value = "";
                updateAppearancePreview();

                uploadIconStatus.textContent = "✓ Imagen subida correctamente";
                uploadIconStatus.style.color = "#16a34a";

                setTimeout(
                    () => { uploadIconStatus.textContent = ""; },
                    3000
                );

            } catch (error) {

                uploadIconStatus.textContent = "✕ " + error.message;
                uploadIconStatus.style.color = "#dc2626";

            } finally {

                uploadIconButton.disabled = false;

            }

        }
    );

}


/* =========================
   INICIO
========================= */

loadMe().catch(error => {

    portalCompanyName.textContent =
        "No se pudo cargar tu panel";

    console.error(error);

});