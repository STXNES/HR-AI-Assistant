"""
Servidor API FastAPI para HR Buddy (ChocolaTech).
Expone:
- Endpoint de Chat conversacional para UI Web y aplicaciones externas
- Webhook para Telegram Bot
- Endpoints de consulta de empleados y políticas
- Servidor de archivos estáticos para la interfaz de prueba visual
"""

import os
from typing import Optional, Dict, Any
from pathlib import Path
from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
import httpx

from hr_buddy_chocolatech.agent.core import hr_buddy_agent
from hr_buddy_chocolatech.agent.memory import memory_manager
from hr_buddy_chocolatech.database.db import db_manager
from hr_buddy_chocolatech.rag.vector_store import rag_engine

app = FastAPI(
    title="HR Buddy API - ChocolaTech",
    description="Agente de IA Autónomo y Persistente para Recursos Humanos (Alura Latam)",
    version="1.0.0"
)

STATIC_DIR = Path(__file__).resolve().parent / "static"
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = "web-default-session"


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "agent": "HR Buddy",
        "company": "ChocolaTech",
        "database_connected": True,
        "database_type": "mysql" if db_manager.is_mysql_active else "sqlite_fallback",
        "indexed_policies": len(rag_engine.documents)
    }


@app.post("/api/chat")
def chat_endpoint(payload: ChatRequest):
    """Endpoint principal de conversación con HR Buddy."""
    try:
        session_id = payload.session_id or "web-default-session"
        result = hr_buddy_agent.process_message(
            session_id=session_id,
            user_message=payload.message
        )
        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e), "answer": "Ocurrió un error interno al procesar tu solicitud."}
        )


@app.post("/api/reset")
def reset_session(payload: Dict[str, str]):
    session_id = payload.get("session_id", "web-default-session")
    memory_manager.clear_session(session_id)
    return {"status": "ok", "message": f"Sesión '{session_id}' reiniciada."}


@app.get("/api/employees")
def list_employees():
    """Retorna la lista de empleados para propósitos de verificación y testing."""
    return {"empleados": db_manager.obtener_todos()}


@app.get("/api/policies")
def list_policies():
    """Retorna las políticas disponibles en el almacén RAG."""
    docs = [d.to_dict() for d in rag_engine.documents]
    return {"politicas": docs}


@app.post("/webhook/telegram")
async def telegram_webhook(request: Request):
    """Recepción de Webhook de Telegram para el agente autónomo."""
    try:
        data = await request.json()
        message = data.get("message") or data.get("edited_message")
        if not message:
            return {"status": "ignored"}

        chat_id = message.get("chat", {}).get("id")
        user_id = str(message.get("from", {}).get("id", chat_id))
        text = message.get("text", "").strip()

        if not text:
            return {"status": "no_text"}

        # Procesar con el agente
        res = hr_buddy_agent.process_message(session_id=user_id, user_message=text)
        respuesta_texto = res["answer"]

        # Si hay token configurado, enviar mensaje de vuelta vía API de Telegram
        if TELEGRAM_BOT_TOKEN and not TELEGRAM_BOT_TOKEN.startswith("your_"):
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                    json={
                        "chat_id": chat_id,
                        "text": respuesta_texto,
                        "parse_mode": "Markdown"
                    },
                    timeout=10.0
                )

        return {"status": "ok", "reply": respuesta_texto}

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


# Servir interfaz web
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", response_class=HTMLResponse)
def index_page():
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        with open(index_file, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse("<h1>HR Buddy ChocolaTech API activa</h1><p>Visita /docs para la documentación interactiva.</p>")


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    host = os.getenv("HOST", "0.0.0.0")
    print(f"\n🚀 Servidor HR Buddy activo en http://localhost:{port}\n")
    uvicorn.run(app, host=host, port=port)
