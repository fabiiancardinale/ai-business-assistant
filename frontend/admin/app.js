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


let selectedCompanyId = null;


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


        companyKnowledge.value =
            data.knowledge || "";


        saveStatus.textContent =
            "";


        companyColor.value =
            data.primary_color || "#111827";

        companyIcon.value =
            data.icon || "💬";

        appearanceStatus.textContent =
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


            alert(
                "Empresa creada correctamente."
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

    appearancePreviewButton.style.background =
        companyColor.value || "#111827";

    appearancePreviewButton.textContent =
        companyIcon.value.trim() || "💬";

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

                            body:
                                JSON.stringify({

                                    primary_color:
                                        companyColor.value,

                                    icon:
                                        companyIcon.value.trim() ||
                                        "💬"

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