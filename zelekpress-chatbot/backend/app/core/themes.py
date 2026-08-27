"""Tokens de diseño del widget y temas predefinidos.

La apariencia de cada chatbot es un diccionario de "tokens" (colores,
layout, launcher, header, mensajes, tipografía). El mismo esquema lo usan:
el editor de personalización, el preview en tiempo real y el widget real
(Fase 4). Cambiar la apariencia = cambiar estos tokens.
"""
import copy


# Apariencia por defecto (base sobre la que se mergea cualquier personalización).
DEFAULT_APPEARANCE = {
    "colors": {
        "primary": "#F0C030",       # color principal (launcher, header, botón enviar)
        "secondary": "#1a1310",     # acento oscuro
        "background": "#ffffff",    # fondo del panel de chat
        "text": "#111827",          # texto general
        "user_bubble": "#111827",   # burbuja del usuario
        "user_text": "#ffffff",
        "bot_bubble": "#f1f2f6",    # burbuja del bot
        "bot_text": "#111827",
        "links": "#2563eb",
    },
    "layout": {
        "mode": "floating",         # floating | embedded
        "side": "right",            # right | left
        "width": 370,
        "height": 560,
        "radius": 18,               # radio de bordes del panel
        "shadow": True,
    },
    "launcher": {
        "icon": "💬",               # emoji o texto; si hay image, gana la imagen
        "image": None,
        "size": 60,
        "color": "#F0C030",         # fondo del botón launcher
        "text": "",                 # texto opcional al lado del ícono
        "position_bottom": 24,
        "position_side": 24,
    },
    "header": {
        "show_logo": True,
        "title": "Asistente",
        "subtitle": "En línea",
        "bg_color": "#1a1310",
        "text_color": "#ffffff",
    },
    "messages": {
        "font": "Inter, system-ui, Arial, sans-serif",
        "size": 14,
        "spacing": 10,
        "bot_avatar": None,
        "user_avatar": None,
    },
}


def _merge(base: dict, override: dict | None) -> dict:
    """Merge profundo: los tokens dados pisan los del base, sin perder el resto."""
    result = copy.deepcopy(base)
    if not override:
        return result
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _merge(result[key], value)
        else:
            result[key] = value
    return result


def full_appearance(tokens: dict | None) -> dict:
    """Devuelve la apariencia completa (default + personalización guardada)."""
    return _merge(DEFAULT_APPEARANCE, tokens)


# Temas predefinidos (solo los overrides respecto del default).
PRESET_THEMES = {
    "modern": {
        "label": "Modern",
        "tokens": {
            "colors": {"primary": "#6366f1", "secondary": "#0b1020", "user_bubble": "#6366f1",
                       "bot_bubble": "#eef2ff", "background": "#ffffff"},
            "layout": {"radius": 18, "shadow": True},
            "launcher": {"color": "#6366f1", "icon": "💬"},
            "header": {"bg_color": "#0b1020", "text_color": "#ffffff"},
        },
    },
    "minimal": {
        "label": "Minimal",
        "tokens": {
            "colors": {"primary": "#111827", "user_bubble": "#111827", "bot_bubble": "#f3f4f6",
                       "background": "#ffffff"},
            "layout": {"radius": 10, "shadow": False},
            "launcher": {"color": "#111827"},
            "header": {"bg_color": "#ffffff", "text_color": "#111827", "show_logo": False},
        },
    },
    "corporate": {
        "label": "Corporate",
        "tokens": {
            "colors": {"primary": "#0ea5e9", "secondary": "#0c4a6e", "user_bubble": "#0ea5e9",
                       "bot_bubble": "#e0f2fe", "background": "#ffffff"},
            "layout": {"radius": 12},
            "launcher": {"color": "#0ea5e9"},
            "header": {"bg_color": "#0c4a6e", "text_color": "#ffffff"},
        },
    },
    "dark": {
        "label": "Dark",
        "tokens": {
            "colors": {"primary": "#F0C030", "background": "#171a22", "text": "#e7e9ee",
                       "bot_bubble": "#232733", "bot_text": "#e7e9ee",
                       "user_bubble": "#F0C030", "user_text": "#1a1310"},
            "layout": {"radius": 16},
            "launcher": {"color": "#F0C030"},
            "header": {"bg_color": "#0f1117", "text_color": "#ffffff"},
        },
    },
    "glass": {
        "label": "Glass",
        "tokens": {
            "colors": {"primary": "#8b5cf6", "background": "#ffffffee", "bot_bubble": "#f5f3ff",
                       "user_bubble": "#8b5cf6"},
            "layout": {"radius": 22, "shadow": True},
            "launcher": {"color": "#8b5cf6"},
            "header": {"bg_color": "#8b5cf6", "text_color": "#ffffff"},
        },
    },
    "rounded": {
        "label": "Rounded",
        "tokens": {
            "colors": {"primary": "#10b981", "user_bubble": "#10b981", "bot_bubble": "#ecfdf5"},
            "layout": {"radius": 28, "shadow": True},
            "launcher": {"color": "#10b981", "size": 64},
            "header": {"bg_color": "#065f46", "text_color": "#ffffff"},
        },
    },
    "elegant": {
        "label": "Elegant",
        "tokens": {
            "colors": {"primary": "#b91c1c", "secondary": "#1c1917", "user_bubble": "#b91c1c",
                       "bot_bubble": "#faf5f0", "background": "#fffdfb"},
            "layout": {"radius": 8, "shadow": True},
            "launcher": {"color": "#b91c1c"},
            "header": {"bg_color": "#1c1917", "text_color": "#f5f0e6"},
        },
    },
}
