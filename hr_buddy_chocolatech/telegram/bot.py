"""
Integración de Telegram Bot para HR Buddy (ChocolaTech).
Soporta:
- Modo Long-Polling (para ejecución directa y pruebas locales inmediatas)
- Modo Webhook (para producción o integración con n8n)
- Aislamiento estricto de memoria por ID de usuario (update.effective_user.id)
"""

import os
import asyncio
from typing import Optional
from dotenv import load_dotenv

from hr_buddy_chocolatech.agent.core import hr_buddy_agent
from hr_buddy_chocolatech.agent.memory import memory_manager

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")


def process_telegram_update(update_dict: dict) -> Optional[dict]:
    """
    Procesa un objeto Update proveniente de un Webhook de Telegram
    y retorna la estructura para enviar la respuesta.
    """
    message = update_dict.get("message") or update_dict.get("edited_message")
    if not message:
        return None

    chat_id = message.get("chat", {}).get("id")
    from_user = message.get("from", {})
    user_id = str(from_user.get("id", chat_id))
    user_first_name = from_user.get("first_name", "Colaborador")
    text = message.get("text", "").strip()

    if not text:
        return None

    # Manejo de comandos especiales
    if text == "/start":
        respuesta = (
            f"¡Hola {user_first_name}! 👋 Soy **HR Buddy**, tu asistente virtual de Recursos Humanos en **ChocolaTech** 🍫✨\n\n"
            "Puedo ayudarte a:\n"
            "• Consultar tu **saldo de vacaciones** acumulado 🌴\n"
            "• Revisar tu balance en el **Banco de Horas** ⏱️\n"
            "• Conocer tu **modalidad de trabajo** (Híbrido/Remoto/Presencial) 💻\n"
            "• Resolver dudas sobre beneficios corporativos y políticas de la empresa 📜\n\n"
            "Para comenzar y consultar tus datos, **¿podrías decirme tu nombre completo?**"
        )
    elif text == "/reset":
        memory_manager.clear_session(user_id)
        respuesta = "🔄 Hemos reiniciado nuestra conversación. ¿En qué te puedo colaborar hoy?"
    elif text == "/help":
        respuesta = (
            "📌 **Comandos disponibles en HR Buddy:**\n"
            "• `/start` - Iniciar o reiniciar la bienvenida\n"
            "• `/reset` - Borrar el historial de la sesión actual\n"
            "• `/help` - Ver esta ayuda\n\n"
            "O simplemente escribe tu consulta, por ejemplo:\n"
            "• *'Soy Juan Silva'*\n"
            "• *'¿Cuántos días de vacaciones me quedan?'*\n"
            "• *'¿Cuál es mi balance en el banco de horas?'*\n"
            "• *'¿Qué beneficios ofrece ChocolaTech?'*"
        )
    else:
        # Enviar al agente con session_id = user_id de Telegram
        res = hr_buddy_agent.process_message(session_id=user_id, user_message=text)
        respuesta = res["answer"]

    return {
        "chat_id": chat_id,
        "text": respuesta,
        "parse_mode": "Markdown"
    }


def run_telegram_polling():
    """Ejecuta el bot de Telegram en modo Long Polling para desarrollo local."""
    if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN.startswith("your_"):
        print(" [Telegram Bot] No se ha configurado un TELEGRAM_BOT_TOKEN válido en el archivo .env.")
        print("ℹ️ Puedes probar el agente usando la interfaz web o el comando interactivo: python cli_chat.py")
        return

    try:
        from telegram import Update
        from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

        async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
            user_id = str(update.effective_user.id)
            nombre = update.effective_user.first_name
            saludo = (
                f"¡Hola {nombre}! 👋 Soy **HR Buddy**, asistente de RR. HH. de **ChocolaTech** 🍫✨\n\n"
                "¿Podrías decirme tu nombre completo para acceder a tus datos corporativos?"
            )
            await update.message.reply_text(saludo, parse_mode="Markdown")

        async def reset_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
            user_id = str(update.effective_user.id)
            memory_manager.clear_session(user_id)
            await update.message.reply_text("🔄 Sesión reiniciada con éxito.", parse_mode="Markdown")

        async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
            user_id = str(update.effective_user.id)
            texto = update.message.text
            resultado = hr_buddy_agent.process_message(session_id=user_id, user_message=texto)
            await update.message.reply_text(resultado["answer"], parse_mode="Markdown")

        print("🤖 Iniciando HR Buddy Telegram Bot en modo Long-Polling...")
        app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
        app.add_handler(CommandHandler("start", start_cmd))
        app.add_handler(CommandHandler("reset", reset_cmd))
        app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
        app.run_polling()

    except ImportError:
        print(" Paquete 'python-telegram-bot' no disponible. Instálalo con: pip install python-telegram-bot")
    except Exception as e:
        print(f" Error iniciando Telegram Bot: {e}")


if __name__ == "__main__":
    run_telegram_polling()
