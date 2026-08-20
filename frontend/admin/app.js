// Ruta relativa: el panel se sirve desde el mismo dominio que la API
// (https://api.zelekpress.com/admin), así que no hace falta (ni conviene)
// fijar un dominio a mano. Antes decía "http://127.0.0.1:8000", que solo
// funciona en tu propia máquina — en producción cada visitante intentaba
// conectarse a su propio localhost, por eso fallaba.
const API_URL = "";


/* =========================
   ELEMENTOS
========================= */

const navItems =
    document.querySelectorAll(".nav-item");

const sections =
    document.querySelectorAll(".section");

const pageTitle =
    document.getElementById("pageTitle");

const pageDescription =
    document.getElementById("pageDescription");


const companiesList =
    document.getElementById("companiesList");

const dashboardCompanies =
    document.getElementById(
        "dashboardCompanies"
    );

const totalCompanies =
    document.getElementById(
        "totalCompanies"
    );


const companyModal =
    document.getElementById(
        "companyModal"
    );

const newCompanyButton =
    document.getElementById(
        "newCompanyButton"
    );

const dashboardCompaniesButton =
    document.getElementById(
        "dashboardCompaniesButton"
    );

const closeModal =
    document.getElementById(
        "closeModal"
    );

const companyForm =
    document.getElementById(
        "companyForm"
    );


/* =========================
   DETALLE EMPRESA
========================= */

const companyDetailSection =
    document.getElementById(
        "company-detail"
    );

const detailCompanyName =
    document.getElementById(
        "detailCompanyName"
    );

const companyKnowledge =
    document.getElementById(
        "companyKnowledge"
    );

const saveKnowledge =
    document.getElementById(
        "saveKnowledge"
    );

const saveStatus =
    document.getElementById(
        "saveStatus"
    );

const backToCompanies =
    document.getElementById(
        "backToCompanies"
    );


/* =========================
   ACCESO DEL CLIENTE
========================= */

const portalEmail =
    document.getElementById(
        "portalEmail"
    );

const portalPassword =
    document.getElementById(
        "portalPassword"
    );

const savePortalPassword =
    document.getElementById(
        "savePortalPassword"
    );

const portalPasswordStatus =
    document.getElementById(
        "portalPasswordStatus"
    );


if (savePortalPassword) {

    savePortalPassword.addEventListener(
        "click",
        async () => {

            if (!selectedCompanyId) {

                alert(
                    "No hay ninguna empresa seleccionada."
                );

                return;

            }


            const password =
                portalPassword.value.trim();

            if (password.length < 6) {

                alert(
                    "La contraseña debe tener al menos 6 caracteres."
                );

                return;

            }


            savePortalPassword.disabled =
                true;

            portalPasswordStatus.textContent =
                "Guardando...";

            portalPasswordStatus.style.color =
                "#6b7280";


            try {

                const response =
                    await fetch(
                        `${API_URL}/companies/${selectedCompanyId}/portal-password`,
                        {
                            method: "PUT",

                            headers: {
                                "Content-Type":
                                    "application/json"
                            },

                            body:
                                JSON.stringify({
                                    password: password
                                })
                        }
                    );


                const data =
                    await response.json();


                if (!response.ok) {

                    throw new Error(
                        data.detail ||
                        "No se pudo guardar"
                    );

                }


                portalPassword.value =
                    "";

                portalPasswordStatus.textContent =
                    "✓ Contraseña guardada. Ya podés pasarle el acceso.";

                portalPasswordStatus.style.color =
                    "#16a34a";


                setTimeout(
                    () => {

                        portalPasswordStatus.textContent =
                            "";

                    },
                    4000
                );


            } catch (error) {

                console.error(
                    "Error guardando contraseña del portal:",
                    error
                );

                portalPasswordStatus.textContent =
                    "✕ " + error.message;

                portalPasswordStatus.style.color =
                    "#dc2626";

            } finally {

                savePortalPassword.disabled =
                    false;

            }

        }
    );

}


/* =========================
   CÓDIGO DE INSTALACIÓN
========================= */

const installSnippet =
    document.getElementById(
        "installSnippet"
    );

const copySnippet =
    document.getElementById(
        "copySnippet"
    );

const copySnippetStatus =
    document.getElementById(
        "copySnippetStatus"
    );

// Dominio donde vive el widget.js que se le instala a los
// clientes. Es el mismo para todas las empresas — lo único
// que cambia por empresa es la API key.
const WIDGET_SCRIPT_URL =
    "https://widget.zelekpress.com/widget.js";


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


function renderInstallSnippet(company) {

    if (!installSnippet) {
        return;
    }

    installSnippet.textContent =
        buildInstallSnippet(company);

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

                console.error(
                    "Error copiando código:",
                    error
                );

                copySnippetStatus.textContent =
                    "✕ No se pudo copiar, seleccioná el texto a mano";

                copySnippetStatus.style.color =
                    "#dc2626";

            }

            setTimeout(
                () => {

                    copySnippetStatus.textContent =
                        "";

                },
                3000
            );

        }
    );

}


/* =========================
   APARIENCIA DEL WIDGET
========================= */

const companyColor =
    document.getElementById(
        "companyColor"
    );

const companyIcon =
    document.getElementById(
        "companyIcon"
    );

const saveAppearance =
    document.getElementById(
        "saveAppearance"
    );

const appearanceStatus =
    document.getElementById(
        "appearanceStatus"
    );

const appearancePreviewButton =
    document.getElementById(
        "appearancePreviewButton"
    );

const companyIconFile =
    document.getElementById(
        "companyIconFile"
    );

const uploadIconButton =
    document.getElementById(
        "uploadIconButton"
    );

const uploadIconStatus =
    document.getElementById(
        "uploadIconStatus"
    );

const companyIconBackground =
    document.getElementById(
        "companyIconBackground"
    );


let selectedCompanyId = null;

// Si el ícono actual de la empresa es una imagen subida (en vez de
// un emoji), guardamos acá su URL para poder mostrarla en la vista
// previa y no perderla al guardar el color.
let currentIconImageUrl = null;


/* =========================
   NAVEGACIÓN
========================= */

navItems.forEach(button => {

    button.addEventListener(
        "click",
        () => {

            const sectionName =
                button.dataset.section;


            navItems.forEach(item => {

                item.classList.remove(
                    "active"
                );

            });


            button.classList.add(
                "active"
            );


            sections.forEach(section => {

                section.classList.remove(
                    "active"
                );

            });


            const targetSection =
                document.getElementById(
                    sectionName
                );


            if (targetSection) {

                targetSection.classList.add(
                    "active"
                );

            }


            const titles = {

                dashboard: [
                    "Dashboard",
                    "Resumen de tu asistente IA"
                ],

                companies: [
                    "Empresas",
                    "Administra los negocios conectados a tu IA."
                ],

                conversations: [
                    "Conversaciones",
                    "Revisa las conversaciones de tus clientes."
                ],

                settings: [
                    "Configuración",
                    "Configuración general del asistente."
                ]

            };


            if (titles[sectionName]) {

                pageTitle.textContent =
                    titles[sectionName][0];

                pageDescription.textContent =
                    titles[sectionName][1];

            }


            if (
                sectionName === "companies"
            ) {

                loadCompanies();

            }

        }
    );

});


/* =========================
   CARGAR EMPRESAS
========================= */

async function loadCompanies() {

    try {

        companiesList.innerHTML =
            `
            <div class="loading">
                Cargando empresas...
            </div>
            `;


        const response =
            await fetch(
                `${API_URL}/companies`
            );


        if (!response.ok) {

            throw new Error(
                "No se pudieron cargar las empresas"
            );

        }


        const companies =
            await response.json();


        totalCompanies.textContent =
            companies.length;


        renderCompanies(
            companies
        );


        renderDashboardCompanies(
            companies
        );


    } catch (error) {

        console.error(
            "Error cargando empresas:",
            error
        );


        companiesList.innerHTML =
            `
            <div class="loading">
                Error al conectar con la API.
            </div>
            `;

    }

}


/* =========================
   MOSTRAR EMPRESAS
========================= */

function renderCompanies(
    companies
) {

    if (companies.length === 0) {

        companiesList.innerHTML =
            `
            <div class="empty-state">

                <div class="empty-icon">
                    🏢
                </div>

                <h3>
                    No hay empresas
                </h3>

                <p>
                    Crea tu primera empresa para comenzar.
                </p>

            </div>
            `;

        return;

    }


    companiesList.innerHTML =
        companies.map(company => {

            const initial =
                company.name
                    .charAt(0)
                    .toUpperCase();


            return `
                <div
                    class="company-row"
                    data-company-id="${company.id}"
                    style="cursor: pointer;"
                >

                    <div class="company-info">

                        <div class="company-avatar">
                            ${initial}
                        </div>

                        <div>

                            <div class="company-name">
                                ${escapeHtml(
                                    company.name
                                )}
                            </div>

                            <div class="company-email">
                                ${escapeHtml(
                                    company.email ||
                                    "Sin correo"
                                )}
                            </div>

                        </div>

                    </div>

                    <span class="badge success-badge">
                        Activa
                    </span>

                </div>
            `;

        }).join("");


    document
        .querySelectorAll(
            ".company-row[data-company-id]"
        )
        .forEach(row => {

            row.addEventListener(
                "click",
                () => {

                    const companyId =
                        Number(
                            row.dataset.companyId
                        );


                    openCompany(
                        companyId
                    );

                }
            );

        });

}


/* =========================
   DASHBOARD
========================= */

function renderDashboardCompanies(
    companies
) {

    if (companies.length === 0) {

        dashboardCompanies.innerHTML =
            `
            <div class="loading">
                No hay empresas registradas.
            </div>
            `;

        return;

    }


    dashboardCompanies.innerHTML =
        companies
            .slice(0, 5)
            .map(company => {

                const initial =
                    company.name
                        .charAt(0)
                        .toUpperCase();


                return `
                    <div
                        class="company-row"
                        data-dashboard-company-id="${company.id}"
                        style="cursor: pointer;"
                    >

                        <div class="company-info">

                            <div class="company-avatar">
                                ${initial}
                            </div>

                            <div>

                                <div class="company-name">
                                    ${escapeHtml(
                                        company.name
                                    )}
                                </div>

                                <div class="company-email">
                                    ${escapeHtml(
                                        company.email ||
                                        ""
                                    )}
                                </div>

                            </div>

                        </div>

                        <span class="badge success-badge">
                            Activa
                        </span>

                    </div>
                `;

            })
            .join("");


    document
        .querySelectorAll(
            "[data-dashboard-company-id]"
        )
        .forEach(row => {

            row.addEventListener(
                "click",
                () => {

                    const companyId =
                        Number(
                            row.dataset
                                .dashboardCompanyId
                        );


                    openCompany(
                        companyId
                    );

                }
            );

        });

}


/* =========================
   ABRIR EMPRESA
========================= */

async function openCompany(
    companyId
) {

    selectedCompanyId =
        companyId;


    try {

        const response =
            await fetch(
                `${API_URL}/companies/${companyId}/knowledge`
            );


        const data =
            await response.json();


        if (!response.ok) {

            throw new Error(
                data.error ||
                data.detail ||
                "No se pudo obtener la información"
            );

        }


        detailCompanyName.textContent =
            data.name;


        renderInstallSnippet(
            data
        );


        if (portalEmail) {

            portalEmail.textContent =
                data.email || "— (esta empresa no tiene email cargado)";

        }

        if (portalPassword) {

            portalPassword.value =
                "";

        }

        if (portalPasswordStatus) {

            portalPasswordStatus.textContent =
                "";

        }


        companyKnowledge.value =
            data.knowledge || "";


        saveStatus.textContent =
            "";


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

            currentIconImageUrl =
                data.icon;

            companyIcon.value =
                "";

        } else {

            currentIconImageUrl =
                null;

            companyIcon.value =
                data.icon || "💬";

        }


        appearanceStatus.textContent =
            "";

        uploadIconStatus.textContent =
            "";

        updateAppearancePreview();


        sections.forEach(section => {

            section.classList.remove(
                "active"
            );

        });


        companyDetailSection.classList.add(
            "active"
        );


        pageTitle.textContent =
            data.name;


        pageDescription.textContent =
            "Configuración del asistente IA";


        navItems.forEach(item => {

            item.classList.remove(
                "active"
            );

        });


    } catch (error) {

        console.error(
            "Error abriendo empresa:",
            error
        );


        alert(
            "Error al cargar la empresa: " +
            error.message
        );

    }

}


/* =========================
   VOLVER A EMPRESAS
========================= */

if (backToCompanies) {

    backToCompanies.addEventListener(
        "click",
        () => {

            companyDetailSection.classList.remove(
                "active"
            );


            const companiesSection =
                document.getElementById(
                    "companies"
                );


            if (companiesSection) {

                companiesSection.classList.add(
                    "active"
                );

            }


            navItems.forEach(item => {

                item.classList.remove(
                    "active"
                );

            });


            const companiesButton =
                document.querySelector(
                    '[data-section="companies"]'
                );


            if (companiesButton) {

                companiesButton.classList.add(
                    "active"
                );

            }


            pageTitle.textContent =
                "Empresas";


            pageDescription.textContent =
                "Administra los negocios conectados a tu IA.";


            loadCompanies();

        }
    );

}


/* =========================
   MODAL NUEVA EMPRESA
========================= */

newCompanyButton.addEventListener(
    "click",
    () => {

        companyModal.classList.add(
            "show"
        );

    }
);


closeModal.addEventListener(
    "click",
    () => {

        companyModal.classList.remove(
            "show"
        );

    }
);


companyModal.addEventListener(
    "click",
    event => {

        if (
            event.target === companyModal
        ) {

            companyModal.classList.remove(
                "show"
            );

        }

    }
);


/* =========================
   CREAR EMPRESA
========================= */

companyForm.addEventListener(
    "submit",
    async event => {

        event.preventDefault();


        const company = {

            name:
                document.getElementById(
                    "companyName"
                ).value.trim(),

            email:
                document.getElementById(
                    "companyEmail"
                ).value.trim(),

            phone:
                document.getElementById(
                    "companyPhone"
                ).value.trim(),

            website:
                document.getElementById(
                    "companyWebsite"
                ).value.trim()

        };


        try {

            const response =
                await fetch(
                    `${API_URL}/companies`,
                    {
                        method: "POST",

                        headers: {
                            "Content-Type":
                                "application/json"
                        },

                        body:
                            JSON.stringify(
                                company
                            )
                    }
                );


            const data =
                await response.json();


            if (!response.ok) {

                throw new Error(
                    data.detail ||
                    data.error ||
                    "No se pudo crear la empresa"
                );

            }


            companyForm.reset();


            companyModal.classList.remove(
                "show"
            );


            await loadCompanies();


            // En vez de un simple aviso, se abre directo el
            // detalle de la empresa recién creada: ahí ya está
            // listo el código de instalación (con su API key)
            // para copiar y pasarle al cliente.

            await openCompany(
                data.id
            );


        } catch (error) {

            console.error(
                "Error creando empresa:",
                error
            );


            alert(
                "Error: " +
                error.message
            );

        }

    }
);


/* =========================
   GUARDAR CONOCIMIENTO
========================= */

if (saveKnowledge) {

    saveKnowledge.addEventListener(
        "click",
        async () => {

            if (!selectedCompanyId) {

                alert(
                    "No hay ninguna empresa seleccionada."
                );

                return;

            }


            const knowledge =
                companyKnowledge.value;


            saveKnowledge.disabled =
                true;


            saveStatus.textContent =
                "Guardando...";


            saveStatus.style.color =
                "#6b7280";


            try {

                const response =
                    await fetch(
                        `${API_URL}/companies/${selectedCompanyId}/knowledge`,
                        {
                            method: "PUT",

                            headers: {
                                "Content-Type":
                                    "application/json"
                            },

                            /* =================================
                               IMPORTANTE:
                               FastAPI espera:
                               {
                                   "knowledge": "..."
                               }
                            ================================= */

                            body:
                                JSON.stringify({
                                    knowledge:
                                        knowledge
                                })
                        }
                    );


                const data =
                    await response.json();


                if (!response.ok) {

                    let errorMessage =
                        "No se pudo guardar";


                    if (data.detail) {

                        if (
                            Array.isArray(
                                data.detail
                            )
                        ) {

                            errorMessage =
                                data.detail
                                    .map(
                                        error => {

                                            if (
                                                typeof error ===
                                                "string"
                                            ) {

                                                return error;

                                            }

                                            return (
                                                error.msg ||
                                                JSON.stringify(
                                                    error
                                                )
                                            );

                                        }
                                    )
                                    .join(", ");

                        } else {

                            errorMessage =
                                typeof data.detail ===
                                "string"
                                    ? data.detail
                                    : JSON.stringify(
                                        data.detail
                                    );

                        }

                    } else if (data.error) {

                        errorMessage =
                            typeof data.error ===
                            "string"
                                ? data.error
                                : JSON.stringify(
                                    data.error
                                );

                    }


                    throw new Error(
                        errorMessage
                    );

                }


                saveStatus.textContent =
                    "✓ Guardado correctamente";


                saveStatus.style.color =
                    "#16a34a";


                setTimeout(
                    () => {

                        saveStatus.textContent =
                            "";

                    },
                    3000
                );


            } catch (error) {

                console.error(
                    "Error guardando conocimiento:",
                    error
                );


                saveStatus.textContent =
                    "✕ Error al guardar";


                saveStatus.style.color =
                    "#dc2626";


                alert(
                    "Error al guardar: " +
                    error.message
                );


            } finally {

                saveKnowledge.disabled =
                    false;

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


    // El toggle de "sin fondo" solo tiene sentido con una imagen
    // subida (un emoji sin fondo de color queda invisible como
    // botón), así que ese caso siempre lleva color de fondo.

    const showBackground =
        !currentIconImageUrl ||
        companyIconBackground.checked;

    appearancePreviewButton.style.background =
        showBackground
            ? (companyColor.value || "#111827")
            : "transparent";

    appearancePreviewButton.style.boxShadow =
        showBackground
            ? ""
            : "none";


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


if (companyIconBackground) {

    companyIconBackground.addEventListener(
        "change",
        updateAppearancePreview
    );

}


if (companyIcon) {

    companyIcon.addEventListener(
        "input",
        () => {

            // Si el usuario escribe un emoji a mano, eso reemplaza
            // a cualquier imagen subida antes en la vista previa
            // (el reemplazo real en el servidor recién ocurre al
            // guardar).

            currentIconImageUrl =
                null;

            updateAppearancePreview();

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

            if (!selectedCompanyId) {

                alert(
                    "No hay ninguna empresa seleccionada."
                );

                return;

            }


            const file =
                companyIconFile.files[0];


            if (!file) {

                alert(
                    "Elegí primero una imagen (PNG, JPG o WEBP)."
                );

                return;

            }


            uploadIconButton.disabled =
                true;

            uploadIconStatus.textContent =
                "Subiendo...";

            uploadIconStatus.style.color =
                "#6b7280";


            try {

                const formData =
                    new FormData();

                formData.append(
                    "file",
                    file
                );


                const response =
                    await fetch(
                        `${API_URL}/companies/${selectedCompanyId}/icon`,
                        {
                            method: "POST",

                            body: formData

                            // OJO: no se pone Content-Type a mano acá.
                            // El navegador arma el header multipart con
                            // el "boundary" correcto solo si lo dejamos
                            // que lo agregue él mismo.
                        }
                    );


                const data =
                    await response.json();


                if (!response.ok) {

                    throw new Error(
                        data.detail ||
                        data.error ||
                        "No se pudo subir la imagen"
                    );

                }


                currentIconImageUrl =
                    data.icon;

                companyIcon.value =
                    "";

                updateAppearancePreview();


                uploadIconStatus.textContent =
                    "✓ Imagen subida correctamente";

                uploadIconStatus.style.color =
                    "#16a34a";


                setTimeout(
                    () => {

                        uploadIconStatus.textContent =
                            "";

                    },
                    3000
                );


            } catch (error) {

                console.error(
                    "Error subiendo ícono:",
                    error
                );


                uploadIconStatus.textContent =
                    "✕ " + error.message;

                uploadIconStatus.style.color =
                    "#dc2626";

            } finally {

                uploadIconButton.disabled =
                    false;

            }

        }
    );

}


/* =========================
   GUARDAR APARIENCIA
========================= */

if (saveAppearance) {

    saveAppearance.addEventListener(
        "click",
        async () => {

            if (!selectedCompanyId) {

                alert(
                    "No hay ninguna empresa seleccionada."
                );

                return;

            }


            saveAppearance.disabled =
                true;


            appearanceStatus.textContent =
                "Guardando...";


            appearanceStatus.style.color =
                "#6b7280";


            try {

                const response =
                    await fetch(
                        `${API_URL}/companies/${selectedCompanyId}/appearance`,
                        {
                            method: "PUT",

                            headers: {
                                "Content-Type":
                                    "application/json"
                            },

                            // Si el campo de emoji está vacío, no
                            // mandamos "icon" — así, si la empresa
                            // tiene una imagen subida, este guardado
                            // (que solo toca el color) no la borra.
                            // El backend solo actualiza el ícono
                            // cuando le llega un valor no vacío.
                            body:
                                JSON.stringify({

                                    primary_color:
                                        companyColor.value,

                                    icon:
                                        companyIcon.value.trim() ||
                                        null,

                                    icon_has_background:
                                        companyIconBackground.checked

                                })
                        }
                    );


                const data =
                    await response.json();


                if (!response.ok) {

                    throw new Error(
                        data.detail ||
                        data.error ||
                        "No se pudo guardar"
                    );

                }


                appearanceStatus.textContent =
                    "✓ Guardado correctamente";


                appearanceStatus.style.color =
                    "#16a34a";


                setTimeout(
                    () => {

                        appearanceStatus.textContent =
                            "";

                    },
                    3000
                );


            } catch (error) {

                console.error(
                    "Error guardando apariencia:",
                    error
                );


                appearanceStatus.textContent =
                    "✕ Error al guardar";


                appearanceStatus.style.color =
                    "#dc2626";


                alert(
                    "Error al guardar: " +
                    error.message
                );


            } finally {

                saveAppearance.disabled =
                    false;

            }

        }
    );

}


/* =========================
   BOTÓN DASHBOARD
========================= */

dashboardCompaniesButton.addEventListener(
    "click",
    () => {

        const companiesButton =
            document.querySelector(
                '[data-section="companies"]'
            );


        if (companiesButton) {

            companiesButton.click();

        }

    }
);


/* =========================
   SEGURIDAD HTML
========================= */

function escapeHtml(
    value
) {

    if (!value) {

        return "";

    }


    return String(value)

        .replace(
            /&/g,
            "&amp;"
        )

        .replace(
            /</g,
            "&lt;"
        )

        .replace(
            />/g,
            "&gt;"
        )

        .replace(
            /"/g,
            "&quot;"
        )

        .replace(
            /'/g,
            "&#039;"
        );

}


/* =========================
   INICIO
========================= */

loadCompanies();