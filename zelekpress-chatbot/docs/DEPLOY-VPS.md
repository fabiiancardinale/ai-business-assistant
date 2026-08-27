# Desplegar el SaaS en la VPS

La v2 (esta plataforma) corre **aparte** de la v1 que ya tenés en
`api.zelekpress.com`. No se toca la v1. Le damos un **subdominio nuevo**,
por ejemplo `app.zelekpress.com`, que sirve el panel y la API juntos.

Resultado final:
- `https://app.zelekpress.com/` → el panel (dashboard.html)
- `https://app.zelekpress.com/api/...` → la API (FastAPI)
- `https://app.zelekpress.com/widget/widget.js` → el widget

---

## 0. DNS (una vez)

En tu proveedor de DNS creá un registro **A**:

```
app.zelekpress.com   A   187.127.57.56
```

Esperá a que propague (unos minutos).

---

## 1. Traer el código a la VPS

Ya lo pusiste en GitHub, así que en la VPS:

```bash
cd /var/www/ai-business-assistant
git pull origin main
cd zelekpress-chatbot
```

---

## 2. Elegí un camino

### Camino A — Docker (recomendado: trae Postgres + Redis solos)

Instalar Docker (si no está):

```bash
curl -fsSL https://get.docker.com | sh
```

Crear el `.env` del backend:

```bash
cp backend/.env.example backend/.env
nano backend/.env
```

Poné al menos:

```env
APP_ENV=production
APP_URL=https://app.zelekpress.com
WIDGET_URL=https://app.zelekpress.com
DATABASE_URL=postgresql+psycopg2://zelekpress:zelekpress@postgres:5432/zelekpress
REDIS_URL=redis://redis:6379/0
JWT_SECRET=PONER_UN_SECRETO_LARGO_Y_ALEATORIO
GROQ_API_KEY=gsk_tu_key_real
SUPERADMIN_EMAIL=admin@zelekpress.com
SUPERADMIN_PASSWORD=CAMBIAR_ESTA
```

Levantar:

```bash
docker compose up -d --build
```

Esto arranca Postgres, Redis y el backend en `127.0.0.1:8000` (corre el
seed solo). Verificá:

```bash
curl -s http://127.0.0.1:8000/health
```

### Camino B — Sin Docker (venv + systemd, como la v1, con SQLite para arrancar)

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
nano .env        # DATABASE_URL=sqlite:///./prod.db  (para empezar sin Postgres)
python -m app.seed
```

Servicio systemd (`/etc/systemd/system/zelekpress-saas.service`):

```ini
[Unit]
Description=Zelekpress SaaS (v2)
After=network.target

[Service]
WorkingDirectory=/var/www/ai-business-assistant/zelekpress-chatbot/backend
EnvironmentFile=/var/www/ai-business-assistant/zelekpress-chatbot/backend/.env
ExecStart=/var/www/ai-business-assistant/zelekpress-chatbot/backend/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
Restart=always
User=root

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now zelekpress-saas
curl -s http://127.0.0.1:8000/health
```

> SQLite alcanza para empezar; cuando escale, se migra a Postgres cambiando
> solo `DATABASE_URL` (y corriendo el seed en la base nueva).

---

## 3. Servir el panel (frontend) por Nginx

Copiamos el panel a un directorio que Nginx sirva como estático:

```bash
sudo mkdir -p /var/www/zelek-panel
sudo cp /var/www/ai-business-assistant/zelekpress-chatbot/frontend/dashboard.html /var/www/zelek-panel/index.html
```

---

## 4. Nginx: un solo subdominio para panel + API + widget

Crear `/etc/nginx/sites-available/zelekpress-saas`:

```nginx
server {
    server_name app.zelekpress.com;

    # Panel (estático)
    root /var/www/zelek-panel;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    # API + widget + uploads + docs -> backend FastAPI
    location ~ ^/(api|widget|uploads|health|docs|openapi.json) {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        # necesario para los WebSockets (chat en vivo)
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 3600s;
        client_max_body_size 8m;
    }
}
```

Activar + SSL:

```bash
sudo ln -s /etc/nginx/sites-available/zelekpress-saas /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d app.zelekpress.com
```

---

## 5. Probar

- Abrí `https://app.zelekpress.com/` → aparece el panel.
- En el login, poné la URL de la API: **`https://app.zelekpress.com`**
  (mismo dominio; Nginx enruta `/api` al backend).
- Registrate (crea usuario + empresa) o entrá.
- Creá un chatbot, copiá su código de instalación (ya apunta a
  `https://app.zelekpress.com/widget/widget.js`) y probalo en un sitio.

---

## Notas

- La v1 en `api.zelekpress.com` sigue intacta; esto es un servicio nuevo en
  otro puerto (8000) y otro subdominio.
- Actualizar en el futuro: `git pull` + (Docker) `docker compose up -d --build`
  o (systemd) `systemctl restart zelekpress-saas`.
- El chat en vivo (WebSockets) corre en un solo proceso; si algún día ponés
  varios workers de uvicorn, hay que activar el bus por Redis (ya está la
  base para eso).
