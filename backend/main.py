import os
import secrets
from pathlib import Path

from fastapi import FastAPI, Depends, Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
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
    generate_company_api_key
)

from services.ai_service import generate_response


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
# Sirve la carpeta admin/ (index.html, style.css, app.js) como
# archivos estáticos en /admin. La seguridad real no está acá
# (los archivos estáticos en sí no son sensibles): está en los
# endpoints /companies, /companies/{id}/knowledge, etc., que
# exigen usuario y contraseña (verify_admin) antes de devolver
# o modificar cualquier dato. Aunque alguien abra /admin, no va
# a poder ver ni cambiar nada sin esas credenciales.
# =========================================================

app.mount(
    "/admin",
    StaticFiles(directory="admin", html=True),
    name="admin"
)


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

    response = generate_response(
        prompt,
        company.knowledge
    )


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

INFORMACIÓN DE LA EMPRESA:

{company.knowledge}


HISTORIAL DE LA CONVERSACIÓN:

{conversation_context}


PREGUNTA DEL CLIENTE:

{request.message}
"""


    # =====================================================
    # 8. GENERAR RESPUESTA
    # =====================================================

    response = generate_response(

        prompt,

        company.knowledge

    )


    # =====================================================
    # 9. GUARDAR RESPUESTA
    # =====================================================

    add_message(

        db=db,

        conversation_id=conversation_id,

        role="assistant",

        content=response

    )


    # =====================================================
    # 10. RESPONDER
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
            "#2563eb"

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
            company.knowledge or ""

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