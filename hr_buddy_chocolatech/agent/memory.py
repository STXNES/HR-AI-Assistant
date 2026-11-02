"""
Gestor de Memoria por Sesión para HR Buddy.
Permite aislar historiales conversacionales por ID de usuario (Telegram chat_id
o sesión web) y persistir el estado de identificación del colaborador entre turnos.
"""

import time
from typing import Dict, Any, List, Optional, Tuple


class SessionData:
    def __init__(self, session_id: str):
        self.session_id: str = session_id
        self.identified_name: Optional[str] = None
        self.employee_data: Optional[Dict[str, Any]] = None
        self.messages: List[Dict[str, str]] = []
        self.last_activity: float = time.time()

    def add_message(self, role: str, content: str):
        self.messages.append({
            "role": role,
            "content": content,
            "timestamp": time.time()
        })
        self.last_activity = time.time()
        # Ventana deslizante para no saturar tokens (últimos 12 mensajes)
        if len(self.messages) > 12:
            self.messages = self.messages[-12:]

    def set_employee(self, name: str, data: Optional[Dict[str, Any]]):
        self.identified_name = name
        self.employee_data = data
        self.last_activity = time.time()

    def clear(self):
        self.identified_name = None
        self.employee_data = None
        self.messages.clear()
        self.last_activity = time.time()


class SessionMemoryManager:
    """Almacén en memoria de estados de sesión indexados por session_id."""

    def __init__(self):
        self._sessions: Dict[str, SessionData] = {}

    def get_or_create(self, session_id: str) -> SessionData:
        if session_id not in self._sessions:
            self._sessions[session_id] = SessionData(session_id)
        return self._sessions[session_id]

    def add_turn(self, session_id: str, user_text: str, assistant_text: str):
        session = self.get_or_create(session_id)
        session.add_message("user", user_text)
        session.add_message("assistant", assistant_text)

    def set_employee_context(self, session_id: str, name: str, employee_record: Optional[Dict[str, Any]]):
        session = self.get_or_create(session_id)
        session.set_employee(name, employee_record)

    def get_employee_context(self, session_id: str) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        session = self.get_or_create(session_id)
        return session.identified_name, session.employee_data

    def format_history_for_prompt(self, session_id: str) -> str:
        session = self.get_or_create(session_id)
        if not session.messages:
            return "No hay interacciones previas."

        formatted = []
        for msg in session.messages[-8:]:  # Últimos 8 turnos
            speaker = "Colaborador" if msg["role"] == "user" else "HR Buddy"
            formatted.append(f"{speaker}: {msg['content']}")
        return "\n".join(formatted)

    def clear_session(self, session_id: str):
        if session_id in self._sessions:
            self._sessions[session_id].clear()


# Instancia singleton para gestión centralizada
memory_manager = SessionMemoryManager()
