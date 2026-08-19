import os
import secrets
from pathlib import Path

from fastapi import FastAPI, Depends, Header, HTTPException, status, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database.database import engine, Base, get_db

from services.chat_service import (
    create_conversation,
    add_message,
    get_conversation_messages
)

from services.company_service import (
    create_company,
    get_company,
    get_companies,
    get_company_by_api_key,
    update_company_knowledge,
    update_company_appearance,
    generate_company_api_key
)

from services.ai_service import generate_response, stream_response


# =========================================================
# CONFIGURACIÓN
# =========================================================

app = FastAPI(
    title="AI Business Assistant",
    version="1.0.0"
)


# =========================================================
# CORS
# =========================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    # Sin esto, el navegador recibe el header X-Conversation-Id en la
    # respuesta pero el JavaScript del widget no puede leerlo (por
    # default el fetch API solo expone un puñado de headers "seguros").
    expose_headers=["X-Conversation-Id"],
)


# =========================================================
# AUTENTICACIÓN DEL PANEL ADMINISTRATIVO (HTTP Basic Auth)
#
# IMPORTANTE: cambiá estas credenciales antes de usar el panel
# en producción. Lo ideal es moverlas a variables de entorno
# (ADMIN_USERNAME / ADMIN_PASSWORD) en vez de dejarlas
# hardcodeadas acá.
# =========================================================

ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "cambia-esta-clave")

security = HTTPBasic()


def verify_admin(credentials: HTTPBasicCredentials = Depends(security)):
    """
    Dependencia que protege los endpoints y el panel administrativo.
    Compara usuario/clave con secrets.compare_digest para evitar
    ataques de timing (comparar strings con == es inseguro acá).
    """

    correct_username = secrets.compare_digest(
        credentials.username, ADMIN_USERNAME
    )

    correct_password = secrets.compare_digest(
        credentials.password, ADMIN_PASSWORD
    )

    if not (correct_username and correct_password):

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
            headers={"WWW-Authenticate": "Basic"},
        )

    return credentials.username


# =========================================================
# BASE DE DATOS
# =========================================================

Base.metadata.create_all(
    bind=engine
)


# =========================================================
# ARCHIVO DE KNOWLEDGE ANTIGUO
# =========================================================

KNOWLEDGE_FILE = Path(
    "knowledge/business.txt"
)


# =========================================================
# MODELOS
# =========================================================

class ChatRequest(BaseModel):

    company_id: int

    message: str

    conversation_id: int | None = None


class PublicChatRequest(BaseModel):

    message: str

    conversation_id: int | None = None


class CompanyCreateRequest(BaseModel):

    name: str

    email: str | None = None

    phone: str | None = None

    website: str | None = None


class KnowledgeRequest(BaseModel):

    knowledge: str


class AppearanceRequest(BaseModel):

    primary_color: str | None = None

    icon: str | None = None

    icon_has_background: bool | None = None


# =========================================================
# CARGAR KNOWLEDGE ANTIGUO
# =========================================================

def load_knowledge():

    if not KNOWLEDGE_FILE.exists():

        return "No existe información disponible."

    return KNOWLEDGE_FILE.read_text(
        encoding="utf-8"
    )


# =========================================================
# ROOT
# =========================================================

@app.get("/")
def root():

    return {
        "status": "online",
        "service": "AI Business Assistant",
        "version": "1.0.0"
    }


# =========================================================
# PANEL ADMINISTRATIVO
#
# Sirve frontend/admin/ (index.html, style.css, app.js) como
# archivos estáticos en /admin. La seguridad real no está acá
# (los archivos estáticos en sí no son sensibles): está en los
# endpoints /companies, /companies/{id}/knowledge, etc., que
# exigen usuario y contraseña (verify_admin) antes de devolver
# o modificar cualquier dato. Aunque alguien abra /admin, no va
# a poder ver ni cambiar nada sin esas credenciales.
#
# La ruta se calcula a partir de este mismo archivo (no del
# directorio de trabajo del proceso), así funciona sin importar
# desde dónde arranque uvicorn/systemd:
# main.py está en backend/, así que subimos un nivel al raíz
# del proyecto y bajamos a frontend/admin.
# =========================================================

ADMIN_DIR = Path(__file__).resolve().parent.parent / "frontend" / "admin"

app.mount(
    "/admin",
    StaticFiles(directory=str(ADMIN_DIR), html=True),
    name="admin"
)


# =========================================================
# ARCHIVOS SUBIDOS (íconos del widget en PNG/JPG/WEBP)
#
# Carpeta pública donde se guardan los íconos que se suben
# desde el panel admin. Se sirve en /uploads, así el widget
# puede mostrar la imagen sin autenticación (igual que el
# resto de los recursos públicos del widget).
# =========================================================

UPLOADS_DIR = Path(__file__).resolve().parent.parent / "uploads"
ICONS_DIR = UPLOADS_DIR / "icons"

ICONS_DIR.mkdir(parents=True, exist_ok=True)

app.mount(
    "/uploads",
    StaticFiles(directory=str(UPLOADS_DIR)),
    name="uploads"
)


# Tipos de imagen permitidos para el ícono y su extensión de archivo
ALLOWED_ICON_TYPES = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
}

# Tamaño máximo permitido para el ícono (500 KB). Es un botón
# chiquito, no hace falta una imagen pesada.
MAX_ICON_SIZE = 500 * 1024


# =========================================================
# CHAT INTERNO
#
# Utilizado por el panel administrativo.
# =========================================================

@app.post("/chat")
def chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
    admin_user: str = Depends(verify_admin)
):

    # =====================================================
    # 1. BUSCAR EMPRESA
    # =====================================================

    company = get_company(
        db=db,
        company_id=request.company_id
    )

    if not company:

        raise HTTPException(
            status_code=404,
            detail="Empresa no encontrada"
        )


    # =====================================================
    # 2. COMPROBAR KNOWLEDGE
    # =====================================================

    if not company.knowledge:

        raise HTTPException(
            status_code=400,
            detail="La empresa no tiene información configurada"
        )


    # =====================================================
    # 3. CONVERSACIÓN
    # =====================================================

    if request.conversation_id:

        conversation_id = request.conversation_id

    else:

        conversation = create_conversation(
            db=db,
            company_id=company.id
        )

        conversation_id = conversation.id


    # =====================================================
    # 4. HISTORIAL
    # =====================================================

    history = get_conversation_messages(
        db=db,
        conversation_id=conversation_id
    )


    conversation_context = ""


    for message in history:

        if message.role == "user":

            conversation_context += (
                f"Cliente: {message.content}\n"
            )

        elif message.role == "assistant":

            conversation_context += (
                f"Asistente: {message.content}\n"
            )


    # =====================================================
    # 5. GUARDAR MENSAJE
    # =====================================================

    add_message(
        db=db,
        conversation_id=conversation_id,
        role="user",
        content=request.message
    )


    # =====================================================
    # 6. PROMPT
    # =====================================================

    prompt = f"""
Eres el asistente virtual de {company.name}.

Tu trabajo es ayudar a los clientes utilizando la
información proporcionada por la empresa.

REGLAS IMPORTANTES:

- Responde siempre en español.
- Sé amable, claro y profesional.
- Utiliza principalmente la información de la empresa.
- No inventes información.
- No inventes precios.
- No inventes horarios.
- No inventes servicios.
- No inventes teléfonos.
- No inventes direcciones.
- No inventes promociones.
- No inventes productos.
- Si no tienes información suficiente, dilo claramente.
- Si la pregunta requiere información que no tienes,
  indica que un miembro del equipo puede ayudar.
- Responde en texto plano, sin formato markdown: no uses
  asteriscos para negritas, no uses # para títulos, no
  numeres con "1.", "2.", etc.
- Si necesitas mostrar varias opciones o pasos, separalos
  con saltos de línea usando un guion simple "-" al
  inicio de cada línea, como una lista de texto normal.
- Sé breve: resumí tu respuesta en pocas oraciones (máximo
  3-4 líneas por punto). Preferí una respuesta corta y
  completa antes que una larga que se pueda cortar a la
  mitad. Si el tema es muy amplio, da lo esencial y ofrecé
  seguir ampliando si el cliente lo pide.
- Respondé específicamente lo que te preguntan, nada más.
  Por ejemplo, si preguntan solo por los servicios, listá
  solo los servicios — no agregues precios, tiempos de
  entrega, soporte ni datos de contacto salvo que te los
  pidan explícitamente o que sean necesarios para responder
  la pregunta puntual.

INFORMACIÓN DE LA EMPRESA:

{company.knowledge}


HISTORIAL DE LA CONVERSACIÓN:

{conversation_context}


NUEVA PREGUNTA DEL CLIENTE:

{request.message}
"""


    # =====================================================
    # 7. IA
    # =====================================================

    response = generate_response(prompt)


    # =====================================================
    # 8. GUARDAR RESPUESTA
    # =====================================================

    add_message(
        db=db,
        conversation_id=conversation_id,
        role="assistant",
        content=response
    )


    # =====================================================
    # 9. RESPUESTA
    # =====================================================

    return {

        "conversation_id":
            conversation_id,

        "company":
            company.name,

        "response":
            response

    }


# =========================================================
# CHAT PÚBLICO
#
# Endpoint utilizado por el widget.
#
# Header:
#
# X-API-Key: zb_live_xxxxxxxxx
#
# Body:
#
# {
#     "message": "Hola"
# }
#
# =========================================================

@app.post("/api/chat")
def public_chat(

    request: PublicChatRequest,

    db: Session = Depends(get_db),

    x_api_key: str | None = Header(
        default=None
    )

):

    # =====================================================
    # 1. COMPROBAR API KEY
    # =====================================================

    if not x_api_key:

        raise HTTPException(
            status_code=401,
            detail="API Key requerida"
        )


    # =====================================================
    # 2. BUSCAR EMPRESA
    # =====================================================

    company = get_company_by_api_key(

        db=db,

        api_key=x_api_key

    )


    if not company:

        raise HTTPException(
            status_code=401,
            detail="API Key inválida"
        )


    # =====================================================
    # 3. COMPROBAR KNOWLEDGE
    # =====================================================

    if not company.knowledge:

        raise HTTPException(
            status_code=400,
            detail="La empresa no tiene información configurada"
        )


    # =====================================================
    # 4. CONVERSACIÓN
    # =====================================================

    if request.conversation_id:

        conversation_id = (
            request.conversation_id
        )

    else:

        conversation = create_conversation(

            db=db,

            company_id=company.id

        )

        conversation_id = conversation.id


    # =====================================================
    # 5. HISTORIAL
    # =====================================================

    history = get_conversation_messages(

        db=db,

        conversation_id=conversation_id

    )


    conversation_context = ""


    for message in history:

        if message.role == "user":

            conversation_context += (
                f"Cliente: {message.content}\n"
            )

        elif message.role == "assistant":

            conversation_context += (
                f"Asistente: {message.content}\n"
            )


    # =====================================================
    # 6. GUARDAR MENSAJE
    # =====================================================

    add_message(

        db=db,

        conversation_id=conversation_id,

        role="user",

        content=request.message

    )


    # =====================================================
    # 7. PROMPT
    # =====================================================

    prompt = f"""
Eres el asistente virtual de {company.name}.

Tu función es atender a los clientes de esta empresa.

REGLAS IMPORTANTES:

- Responde siempre en español.
- Sé amable, claro y profesional.
- Utiliza exclusivamente la información disponible
  sobre la empresa.
- No inventes información.
- No inventes precios.
- No inventes servicios.
- No inventes horarios.
- No inventes teléfonos.
- No inventes direcciones.
- No inventes promociones.
- No inventes productos.
- No inventes información que no aparezca en el
  conocimiento proporcionado.
- Si no puedes responder con seguridad, dilo claramente.
- Si es necesario, indica que un miembro del equipo
  puede ayudar.
- Responde en texto plano, sin formato markdown: no uses
  asteriscos para negritas, no uses # para títulos, no
  numeres con "1.", "2.", etc.
- Si necesitas mostrar varias opciones o pasos, separalos
  con saltos de línea usando un guion simple "-" al
  inicio de cada línea, como una lista de texto normal.
- Sé breve: resumí tu respuesta en pocas oraciones (máximo
  3-4 líneas por punto). Preferí una respuesta corta y
  completa antes que una larga que se pueda cortar a la
  mitad. Si el tema es muy amplio, da lo esencial y ofrecé
  seguir ampliando si el cliente lo pide.
- Respondé específicamente lo que te preguntan, nada más.
  Por ejemplo, si preguntan solo por los servicios, listá
  solo los servicios — no agregues precios, tiempos de
  entrega, soporte ni datos de contacto salvo que te los
  pidan explícitamente o que sean necesarios para responder
  la pregunta puntual.

INFORMACIÓN DE LA EMPRESA:

{company.knowledge}


HISTORIAL DE LA CONVERSACIÓN:

{conversation_context}


PREGUNTA DEL CLIENTE:

{request.message}
"""


    # =====================================================
    # 8. GENERAR Y ENVIAR RESPUESTA EN STREAM
    #
    # En vez de esperar la respuesta completa de Ollama (que
    # puede tardar bastante), vamos entregando el texto al
    # widget a medida que se genera, así el usuario ve la
    # respuesta apareciendo en tiempo real.
    #
    # El conversation_id va en un header (X-Conversation-Id)
    # porque el cuerpo de la respuesta ya no es JSON: es texto
    # plano que se va transmitiendo de a pedazos.
    # =====================================================

    def event_generator():

        full_response = ""

        for piece in stream_response(prompt):

            full_response += piece

            yield piece


        # =================================================
        # GUARDAR RESPUESTA COMPLETA
        #
        # IMPORTANTE: no podemos reutilizar `db` acá. Esa sesión
        # se cierra apenas la función public_chat() retorna (es
        # decir, apenas se crea el StreamingResponse), y esta
        # función generadora sigue corriendo DESPUÉS de eso,
        # mientras Ollama todavía está generando texto. Por eso
        # abrimos una sesión nueva, propia de este generador.
        # =================================================

        with Session(engine) as fresh_db:

            add_message(

                db=fresh_db,

                conversation_id=conversation_id,

                role="assistant",

                content=full_response

            )


    return StreamingResponse(

        event_generator(),

        media_type="text/plain; charset=utf-8",

        headers={
            "X-Conversation-Id": str(conversation_id)
        }

    )


# =========================================================
# CONFIGURACIÓN PÚBLICA DEL WIDGET
#
# Permite al widget conocer el nombre de la empresa
# sin exponer el knowledge.
# =========================================================

@app.get("/api/widget/config")
def widget_config(

    db: Session = Depends(get_db),

    x_api_key: str | None = Header(
        default=None
    )

):

    # =====================================================
    # 1. COMPROBAR API KEY
    # =====================================================

    if not x_api_key:

        raise HTTPException(
            status_code=401,
            detail="API Key requerida"
        )


    # =====================================================
    # 2. BUSCAR EMPRESA
    # =====================================================

    company = get_company_by_api_key(

        db=db,

        api_key=x_api_key

    )


    if not company:

        raise HTTPException(
            status_code=401,
            detail="API Key inválida"
        )


    # =====================================================
    # 3. RESPUESTA
    # =====================================================

    return {

        "company_id":
            company.id,

        "company_name":
            company.name,

        "welcome_message":
            f"Hola 👋 Soy el asistente virtual de {company.name}. ¿En qué podemos ayudarte?",

        "primary_color":
            company.primary_color or "#111827",

        "icon":
            company.icon or "💬",

        "icon_has_background":
            company.icon_has_background
            if company.icon_has_background is not None
            else True

    }


# =========================================================
# CREAR EMPRESA
# =========================================================

@app.post("/companies")
def create_company_endpoint(

    request: CompanyCreateRequest,

    db: Session = Depends(get_db),

    admin_user: str = Depends(verify_admin)

):

    company = create_company(

        db=db,

        name=request.name,

        email=request.email,

        phone=request.phone,

        website=request.website

    )


    return {

        "id":
            company.id,

        "name":
            company.name,

        "email":
            company.email,

        "phone":
            company.phone,

        "website":
            company.website,

        "api_key":
            company.api_key

    }


# =========================================================
# LISTAR EMPRESAS
# =========================================================

@app.get("/companies")
def companies(

    db: Session = Depends(get_db),

    admin_user: str = Depends(verify_admin)

):

    companies = get_companies(
        db
    )


    return [

        {

            "id":
                company.id,

            "name":
                company.name,

            "email":
                company.email,

            "phone":
                company.phone,

            "website":
                company.website,

            "api_key":
                company.api_key

        }

        for company in companies

    ]


# =========================================================
# OBTENER KNOWLEDGE
# =========================================================

@app.get(
    "/companies/{company_id}/knowledge"
)
def company_knowledge(

    company_id: int,

    db: Session = Depends(get_db),

    admin_user: str = Depends(verify_admin)

):

    company = get_company(

        db=db,

        company_id=company_id

    )


    if not company:

        raise HTTPException(

            status_code=404,

            detail="Empresa no encontrada"

        )


    return {

        "id":
            company.id,

        "name":
            company.name,

        "knowledge":
            company.knowledge or "",

        "api_key":
            company.api_key,

        "primary_color":
            company.primary_color or "#111827",

        "icon":
            company.icon or "💬",

        "icon_has_background":
            company.icon_has_background
            if company.icon_has_background is not None
            else True

    }


# =========================================================
# ACTUALIZAR KNOWLEDGE
# =========================================================

@app.put(
    "/companies/{company_id}/knowledge"
)
def update_knowledge(

    company_id: int,

    data: KnowledgeRequest,

    db: Session = Depends(get_db),

    admin_user: str = Depends(verify_admin)

):

    company = update_company_knowledge(

        db=db,

        company_id=company_id,

        knowledge=data.knowledge

    )


    if not company:

        raise HTTPException(

            status_code=404,

            detail="Empresa no encontrada"

        )


    return {

        "id":
            company.id,

        "name":
            company.name,

        "knowledge":
            company.knowledge

    }


# =========================================================
# ACTUALIZAR APARIENCIA DEL WIDGET
#
# Permite cambiar el color principal y el ícono del botón
# flotante del widget desde el panel de administración, sin
# tener que tocar el <script> instalado en el sitio del
# cliente.
# =========================================================

@app.put(
    "/companies/{company_id}/appearance"
)
def update_appearance(

    company_id: int,

    data: AppearanceRequest,

    db: Session = Depends(get_db),

    admin_user: str = Depends(verify_admin)

):

    company = update_company_appearance(

        db=db,

        company_id=company_id,

        primary_color=data.primary_color,

        icon=data.icon,

        icon_has_background=data.icon_has_background

    )


    if not company:

        raise HTTPException(

            status_code=404,

            detail="Empresa no encontrada"

        )


    return {

        "id":
            company.id,

        "name":
            company.name,

        "primary_color":
            company.primary_color,

        "icon":
            company.icon,

        "icon_has_background":
            company.icon_has_background
            if company.icon_has_background is not None
            else True

    }


# =========================================================
# SUBIR ÍCONO DEL WIDGET (imagen)
#
# Alternativa a poner un emoji: subir una imagen (PNG, JPG o
# WEBP) que se usa como ícono del botón flotante. Se guarda en
# uploads/icons/ y el campo "icon" de la empresa pasa a guardar
# la URL de esa imagen (ej: "/uploads/icons/company_3.png") en
# vez de un emoji. El widget distingue uno de otro mirando si
# el valor empieza con "/" o "http".
# =========================================================

@app.post(
    "/companies/{company_id}/icon"
)
async def upload_company_icon(

    company_id: int,

    file: UploadFile = File(...),

    db: Session = Depends(get_db),

    admin_user: str = Depends(verify_admin)

):

    company = get_company(
        db=db,
        company_id=company_id
    )

    if not company:

        raise HTTPException(
            status_code=404,
            detail="Empresa no encontrada"
        )


    # =====================================================
    # VALIDAR TIPO DE ARCHIVO
    # =====================================================

    extension = ALLOWED_ICON_TYPES.get(
        file.content_type
    )

    if not extension:

        raise HTTPException(
            status_code=400,
            detail="Formato no permitido. Usa PNG, JPG o WEBP."
        )


    # =====================================================
    # VALIDAR TAMAÑO
    # =====================================================

    contents = await file.read()

    if len(contents) > MAX_ICON_SIZE:

        raise HTTPException(
            status_code=400,
            detail="La imagen es muy pesada (máximo 500 KB)."
        )


    # =====================================================
    # GUARDAR ARCHIVO
    #
    # Se nombra con el id de la empresa, así una nueva subida
    # reemplaza la anterior en vez de ir acumulando archivos.
    # =====================================================

    filename = f"company_{company_id}{extension}"

    filepath = ICONS_DIR / filename

    with open(filepath, "wb") as destination:
        destination.write(contents)


    icon_url = f"/uploads/icons/{filename}"

    company = update_company_appearance(
        db=db,
        company_id=company_id,
        icon=icon_url
    )


    return {

        "id":
            company.id,

        "icon":
            company.icon

    }


# =========================================================
# GENERAR API KEY
# PARA EMPRESA EXISTENTE
# =========================================================

@app.post(
    "/companies/{company_id}/generate-api-key"
)
def generate_company_api_key_endpoint(

    company_id: int,

    db: Session = Depends(get_db),

    admin_user: str = Depends(verify_admin)

):

    company = generate_company_api_key(

        db=db,

        company_id=company_id

    )


    if not company:

        raise HTTPException(

            status_code=404,

            detail="Empresa no encontrada"

        )


    return {

        "id":
            company.id,

        "name":
            company.name,

        "api_key":
            company.api_key

    }