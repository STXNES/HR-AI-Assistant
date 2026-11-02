"""
Núcleo del Agente Conversacional HR Buddy de ChocolaTech.
Orquesta:
- Guardrails de dominio y seguridad
- Extracción de identidad y búsqueda en MySQL ($fromAI)
- Búsqueda documental de políticas vía RAG
- Memoria aislada por sesión (Telegram / Web)
- Generación de respuesta adaptativa (Groq, Gemini, OpenAI o motor local de contingencia)
"""

import os
import re
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv

from hr_buddy_chocolatech.agent.system_prompt import (
    HR_BUDDY_SYSTEM_PROMPT,
    PROMPT_RECHAZO_GUARDRAILS,
    PROMPT_PEDIR_NOMBRE,
)
from hr_buddy_chocolatech.agent.guardrails import HRGuardrails
from hr_buddy_chocolatech.agent.memory import memory_manager
from hr_buddy_chocolatech.agent.tools import (
    tool_buscar_empleado_mysql,
    tool_consultar_politicas_rrhh,
)

load_dotenv()

# Variables de configuración de LLM
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq").lower()
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")


def extraer_nombre_candidato(texto: str) -> Optional[str]:
    """Extrae el nombre del colaborador a partir de frases comunes o mensajes directos."""
    texto_strip = texto.strip()

    # Patrones con intro
    patrones = [
        r"(?:hola\s*,?\s*)?(?:yo\s+)?soy\s+([A-Za-záéíóúÁÉÍÓÚñÑ\s]+)",
        r"(?:mi\s+nombre\s+es|me\s+llamo)\s+([A-Za-záéíóúÁÉÍÓÚñÑ\s]+)",
        r"(?:habla|aqui|acá)\s+([A-Za-záéíóúÁÉÍÓÚñÑ\s]+)",
    ]

    for pat in patrones:
        match = re.search(pat, texto_strip, re.IGNORECASE)
        if match:
            candidato = match.group(1).strip()
            # Limpiar añadidos comunes como "de ingeniería", "del área de...", "y quisiera saber"
            candidato = re.split(r'\b(?:de|del|en|para|y\s+(?:trabajo|quisiera|tengo))\b', candidato, flags=re.IGNORECASE)[0].strip()
            candidato = re.sub(r'[\.\,\!\?]+$', '', candidato).strip()
            if len(candidato.split()) >= 1 and len(candidato) > 2:
                return candidato

    # Si el mensaje consta de 2 a 4 palabras sin verbos de pregunta, puede ser el nombre directo
    palabras = texto_strip.split()
    no_es_pregunta = not any(w in texto_strip.lower() for w in ["que", "cómo", "como", "cuánto", "cuanto", "dónde", "donde", "por qué", "ayuda", "dias", "horas", "tengo", "puedo"])
    if 2 <= len(palabras) <= 4 and no_es_pregunta and not texto_strip.endswith("?"):
        limpio = re.sub(r'[\.\,\!\?]+$', '', texto_strip).strip()
        return limpio

    return None


class HRBuddyAgent:
    """Agente de Recursos Humanos para ChocolaTech."""

    def __init__(self, llm_provider: str = LLM_PROVIDER):
        self.llm_provider = llm_provider

    def _call_remote_llm(self, prompt_text: str) -> Optional[str]:
        """Llama a un proveedor LLM remoto configurado con fallback en cascada."""
        providers = [self.llm_provider, "groq", "gemini", "openai"]
        
        # Eliminar duplicados manteniendo orden
        vistos = set()
        providers_clean = [p for p in providers if not (p in vistos or vistos.add(p))]

        for prov in providers_clean:
            # 1. Groq
            if prov == "groq" and GROQ_API_KEY:
                try:
                    from langchain_groq import ChatGroq
                    llm = ChatGroq(
                        model="llama-3.3-70b-versatile",
                        groq_api_key=GROQ_API_KEY,
                        temperature=0.2
                    )
                    res = llm.invoke(prompt_text)
                    return res.content if hasattr(res, "content") else str(res)
                except Exception as e:
                    print(f"Error llamando a Groq: {e}")

            # 2. Gemini
            if prov == "gemini" and GEMINI_API_KEY:
                try:
                    from langchain_google_genai import ChatGoogleGenerativeAI
                    llm = ChatGoogleGenerativeAI(
                        model="gemini-1.5-flash",
                        google_api_key=GEMINI_API_KEY,
                        temperature=0.2
                    )
                    res = llm.invoke(prompt_text)
                    return res.content if hasattr(res, "content") else str(res)
                except Exception as e:
                    print(f"Error llamando a Gemini: {e}")

            # 3. OpenAI
            if prov == "openai" and OPENAI_API_KEY:
                try:
                    from langchain_openai import ChatOpenAI
                    llm = ChatOpenAI(
                        model="gpt-3.5-turbo",
                        openai_api_key=OPENAI_API_KEY,
                        temperature=0.2
                    )
                    res = llm.invoke(prompt_text)
                    return res.content if hasattr(res, "content") else str(res)
                except Exception as e:
                    print(f"Error llamando a OpenAI: {e}")

        return None

    def _generate_local_fallback_response(
        self,
        user_message: str,
        emp_data: Optional[Dict[str, Any]],
        identified_name: Optional[str],
        rag_results: List[Dict[str, Any]]
    ) -> str:
        """
        Generador sintético local de alta fidelidad.
        Permite respuestas precisas y deterministas siguiendo todas las reglas de negocio
        incluso si los servicios externos de LLM no están disponibles o no tienen saldo.
        """
        msg_lower = user_message.lower()

        # Caso: Saludo o presentación con nombre
        es_saludo_o_presentacion = (
            any(s in msg_lower for s in ["hola", "buen dia", "buenos dias", "buenas"]) or
            any(k in msg_lower for k in ["soy ", "me llamo", "mi nombre"])
        )
        no_es_consulta_especifica = not any(k in msg_lower for k in ["vacacion", "banco de horas", "modalidad", "beneficio", "sgmm"])

        if es_saludo_o_presentacion and no_es_consulta_especifica:
            if emp_data:
                return (
                    f"¡Hola {emp_data['nombre']}! Qué gusto saludarte. Soy **HR Buddy**, tu asistente de Recursos Humanos de ChocolaTech. 🍫✨\n\n"
                    f"Actualmente tienes registrado en el sistema:\n"
                    f"• **Puesto:** {emp_data['puesto']} ({emp_data['departamento']})\n"
                    f"• **Modalidad:** {emp_data['modalidad'].capitalize()}\n"
                    f"• **Saldo de Vacaciones:** {emp_data['saldo_vacaciones']} días hábiles\n"
                    f"• **Banco de Horas:** {emp_data['banco_horas']} horas\n\n"
                    f"¿En qué te puedo apoyar el día de hoy?"
                )
            elif identified_name:
                return (
                    f"¡Hola {identified_name}! Soy **HR Buddy**, asistente de Recursos Humanos de ChocolaTech. 🍫\n\n"
                    f"No encuentro un registro activo con tu nombre en nuestra base de datos de colaboradores, "
                    f"pero con gusto puedo orientarte sobre todas nuestras políticas corporativas generales. "
                    f"¿En qué tema de RR. HH. te gustaría consultar?"
                )
            else:
                return PROMPT_PEDIR_NOMBRE

        # Caso: Consulta de vacaciones
        if "vacacion" in msg_lower or "vacaciones" in msg_lower or "dias libres" in msg_lower:
            if emp_data:
                dias = emp_data['saldo_vacaciones']
                return (
                    f"¡Hola {emp_data['nombre']}! 🌴\n\n"
                    f"Consultando nuestro sistema de Recursos Humanos, cuentas actualmente con un saldo disponible de **{dias} días hábiles** de vacaciones.\n\n"
                    f"**Recordatorio de nuestra política de ChocolaTech:**\n"
                    f"• Las solicitudes deben enviarse con al menos **15 días continuos de anticipación** a través de RR. HH. o este canal.\n"
                    f"• Puedes fraccionarlas en períodos mínimos de 1 día hábil.\n"
                    f"• Se permite transferir hasta un máximo de 5 días hábiles al siguiente ciclo anual.\n\n"
                    f"¿Deseas iniciar la solicitud de algún período en específico?"
                )
            else:
                return (
                    f"En ChocolaTech, el saldo de vacaciones se genera anualmente según la antigüedad laboral "
                    f"(iniciando desde 12 días hábiles para el primer año cumplido). Las solicitudes deben tramitarse "
                    f"con un mínimo de 15 días de anticipación.\n\n"
                    f"*(Nota: No registramos tu nombre en nuestro sistema activo, por lo que no fue posible consultar un saldo personal. Si eres colaborador de ChocolaTech, por favor indícame tu nombre completo).* 🍫"
                )

        # Caso: Consulta de banco de horas
        if "banco de horas" in msg_lower or "horas extra" in msg_lower or "sobretiempo" in msg_lower:
            if emp_data:
                horas = emp_data['banco_horas']
                estado = "a tu favor (+)" if horas > 0 else ("en contra a compensar (-)" if horas < 0 else "equilibrado (0.0)")
                return (
                    f"¡Hola {emp_data['nombre']}! ⏱️\n\n"
                    f"Tu balance actual en el **Banco de Horas** de ChocolaTech es de **{horas} horas** ({estado}).\n\n"
                    f"**Lineamientos de la política:**\n"
                    f"• El límite máximo acumulable positivo es de 40.0 horas.\n"
                    f"• Si tienes saldo a favor, puedes canjearlo por tiempo libre avisando con 48 horas de anticipación a tu líder.\n"
                    f"• Si el saldo fuera negativo, cuentas con un período de 60 días para compensarlo coordinando con tu supervisor."
                )
            else:
                return (
                    f"La política de Banco de Horas de ChocolaTech permite acumular hasta un máximo de 40.0 horas positivas, "
                    f"las cuales pueden ser canjeadas por días u horas libres con aviso previo de 48 horas a la jefatura directa. "
                    f"Los saldos negativos no pueden superar las -10.0 horas y deben compensarse en 60 días.\n\n"
                    f"*(Indícame tu nombre completo si deseas revisar tu balance individual).* 🍫"
                )

        # Caso: Modalidad de trabajo
        if "modalidad" in msg_lower or "remoto" in msg_lower or "hibrido" in msg_lower or "presencial" in msg_lower or "home office" in msg_lower:
            if emp_data:
                mod = emp_data['modalidad']
                return (
                    f"¡Hola {emp_data['nombre']}! 🏢💻\n\n"
                    f"Tu modalidad de trabajo registrada es **{mod.capitalize()}** en el departamento de **{emp_data['departamento']}**.\n\n"
                    f"**Detalles de la modalidad {mod.capitalize()}:**\n"
                    f"• Asistencia requerida según política: { 'Mínimo 2 días presenciales por semana con horario núcleo de 10:00 a 16:00' if mod == 'hibrido' else ('100% teletrabajo con bono de conectividad de $45 USD' if mod == 'remoto' else 'Lunes a viernes presencial con comedor subsidiado al 100%') }.\n"
                    f"• Si deseas solicitar un cambio de modalidad, se requiere un mínimo de 6 meses de permanencia en el puesto."
                )
            else:
                return (
                    f"ChocolaTech contempla tres modalidades de trabajo: Híbrida (mínimo 2 días presenciales por semana), "
                    f"Remota (100% home office con subsidio de conectividad) y Presencial (con comedor corporativo y transporte). "
                    f"Para solicitar un cambio de modalidad se requiere un mínimo de 6 meses en la posición."
                )

        # Caso: Beneficios generales
        if "beneficio" in msg_lower or "sgmm" in msg_lower or "chocobox" in msg_lower or "beca" in msg_lower or "seguro" in msg_lower:
            return (
                f"Entre los principales beneficios de **ChocolaTech** destacan:\n"
                f"1. **Seguro de Gastos Médicos Mayores (SGMM):** Cobertura 100% para colaborador y dependientes directos.\n"
                f"2. **ChocoBox Mensual:** Caja exclusiva de chocolates y lanzamientos de I+D el primer viernes de cada mes.\n"
                f"3. **Beca Anual de Capacitación:** Hasta $1,000 USD anuales para cursos, certificaciones y plataformas educativas.\n"
                f"4. **Días de Desconexión (Mental Health Days):** 2 días al año con goce de sueldo sin necesidad de justificación médica.\n"
                f"5. **Descuento de Empleado:** 40% de descuento en todas nuestras tiendas.\n\n"
                + (f"*(Identificado como: {emp_data['nombre']} - {emp_data['puesto']})*" if emp_data else "")
            )

        # Respuesta general basada en RAG
        if rag_results:
            top_content = rag_results[0]["content"]
            saludo = f"¡Hola {emp_data['nombre']}! " if emp_data else "¡Hola! "
            return (
                f"{saludo}Con base en las políticas de Recursos Humanos de ChocolaTech:\n\n"
                f"{top_content}\n\n"
                f"*(Fuente: {rag_results[0]['source']} - {rag_results[0]['section']})*"
            )

        return (
            "¡Hola! Como HR Buddy de ChocolaTech, puedo asistirte con información sobre "
            "tu saldo de vacaciones, banco de horas, modalidad de trabajo y políticas de beneficios corporativos. "
            "¿Qué consulta te gustaría realizar?"
        )

    def process_message(self, session_id: str, user_message: str) -> Dict[str, Any]:
        """
        Flujo integral de procesamiento de un mensaje de usuario.
        Retorna diccionario con la respuesta generada y metadatos de auditoría.
        """
        # 1. Aplicación de Guardrails de Seguridad y Dominio
        es_valido, motivo = HRGuardrails.validar_consulta(user_message)
        if not es_valido:
            if motivo == "prompt_injection_detectada":
                respuesta = (
                    "Lo siento, he detectado instrucciones que intentan modificar mis políticas operativas. "
                    "Como **HR Buddy**, mi función está estrictamente limitada a resolver consultas de "
                    "Recursos Humanos y políticas corporativas de ChocolaTech."
                )
            else:
                respuesta = PROMPT_RECHAZO_GUARDRAILS

            memory_manager.add_turn(session_id, user_message, respuesta)
            return {
                "answer": respuesta,
                "guardrails_passed": False,
                "guardrail_reason": motivo,
                "employee": None,
                "sources": []
            }

        # 2. Obtener estado previo de la sesión
        identified_name, emp_data = memory_manager.get_employee_context(session_id)

        # 3. Detección y búsqueda del colaborador en la base de datos si aún no está identificado
        candidato_nombre = extraer_nombre_candidato(user_message)
        
        if candidato_nombre:
            db_res = tool_buscar_empleado_mysql(candidato_nombre)
            if db_res["encontrado"]:
                identified_name = db_res["nombre"]
                emp_data = db_res
                memory_manager.set_employee_context(session_id, identified_name, emp_data)
            else:
                identified_name = candidato_nombre
                emp_data = None
                memory_manager.set_employee_context(session_id, identified_name, None)

        # 4. Si el usuario no ha dicho su nombre y pregunta por datos personales, pedir su nombre
        pregunta_personal = any(k in user_message.lower() for k in [
            "mis vacaciones", "mi saldo", "mis horas", "mi banco", "mi modalidad", "cuantos dias tengo", "cuanto me queda"
        ])
        
        if not identified_name and pregunta_personal:
            respuesta = PROMPT_PEDIR_NOMBRE
            memory_manager.add_turn(session_id, user_message, respuesta)
            return {
                "answer": respuesta,
                "guardrails_passed": True,
                "needs_identification": True,
                "employee": None,
                "sources": []
            }

        # 5. Búsqueda RAG de políticas corporativas
        rag_res = tool_consultar_politicas_rrhh(user_message, top_k=2)
        rag_context = rag_res["contexto_texto"]
        rag_sources = [r["source"] for r in rag_res.get("resultados", [])]

        # 6. Construcción del Prompt Enriquecido para el LLM
        historial_texto = memory_manager.format_history_for_prompt(session_id)
        
        if emp_data:
            info_empleado = (
                f"DATOS DEL COLABORADOR IDENTIFICADO (MySQL):\n"
                f"- Nombre: {emp_data['nombre']}\n"
                f"- Email: {emp_data['email']}\n"
                f"- Puesto: {emp_data['puesto']}\n"
                f"- Departamento: {emp_data['departamento']}\n"
                f"- Fecha de Ingreso: {emp_data['fecha_ingreso']}\n"
                f"- Saldo de Vacaciones: {emp_data['saldo_vacaciones']} días hábiles\n"
                f"- Banco de Horas: {emp_data['banco_horas']} horas\n"
                f"- Modalidad: {emp_data['modalidad']}"
            )
        elif identified_name:
            info_empleado = (
                f"COLABORADOR NO ENCONTRADO EN BASE DE DATOS:\n"
                f"- El usuario indicó llamarse: '{identified_name}'.\n"
                f"- Estado: NO figura en la base de empleados de ChocolaTech.\n"
                f"- REGLA: No inventes ningún saldo personal. Responde usando exclusivamente las políticas generales."
            )
        else:
            info_empleado = (
                "COLABORADOR NO IDENTIFICADO AÚN:\n"
                "- Si la pregunta requiere datos personales específicos, pídele su nombre completo."
            )

        full_prompt = f"""{HR_BUDDY_SYSTEM_PROMPT}

========================
INFORMACIÓN DEL COLABORADOR:
{info_empleado}
========================

DOCUMENTACIÓN DE POLÍTICAS CORPORATIVAS (RAG):
{rag_context}
========================

HISTORIAL DE LA CONVERSACIÓN:
{historial_texto}
========================

MENSAJE DEL USUARIO:
{user_message}

RESPUESTA DE HR BUDDY:"""

        # 7. Intentar llamada a LLM remoto; si falla o no hay API key, invocar fallback local de alta calidad
        answer_text = self._call_remote_llm(full_prompt)

        if not answer_text or not answer_text.strip():
            answer_text = self._generate_local_fallback_response(
                user_message,
                emp_data,
                identified_name,
                rag_res.get("resultados", [])
            )

        # 8. Registrar turno en memoria de sesión
        memory_manager.add_turn(session_id, user_message, answer_text)

        return {
            "answer": answer_text,
            "guardrails_passed": True,
            "employee": emp_data,
            "identified_name": identified_name,
            "sources": rag_sources
        }


# Instancia singleton para importación
hr_buddy_agent = HRBuddyAgent()
