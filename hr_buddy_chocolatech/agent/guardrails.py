"""
Módulo de Seguridad y Guardrails para HR Buddy.
Asegura que el agente responda exclusivamente sobre temas de Recursos Humanos
y previene ataques de inyección de prompts o desvíos de dominio.
"""

import re
from typing import Tuple

# Patrones típicos de inyección de prompt o manipulación de instrucciones
INJECTION_PATTERNS = [
    r"ignora\s+(todas\s+las|las)?\s*instrucciones",
    r"ignore\s+(all\s+previous\s+|the\s+)?instructions",
    r"olvida\s+(todo\s+lo\s+anterior|tus\s+reglas)",
    r"act\s+as\s+(dan|jailbreak|root)",
    r"modo\s+desarrollador\s+activado",
    r"print\s+(your\s+)?system\s+prompt",
    r"muestra\s+tu\s+prompt\s+del\s+sistema",
    r"revela\s+(tu\s+prompt|las\s+instrucciones\s+ocultas)",
    r"bypass\s+rules",
]

# Temas explícitamente fuera de dominio (Off-topic)
OFFTOPIC_PATTERNS = [
    r"\b(receta|cocinar|ingredientes|pastel|pizza|tacos)\b",
    r"\b(partido|futbol|fútbol|mundial|messi|cr7|champions)\b",
    r"\b(bitcoin|criptomoneda|trading|forex|bolsa\s+de\s+valores)\b",
    r"\b(codigo\s+python|código\s+python|escribe\s+un\s+script|crea\s+un\s+html|javascript|css\s+animation)\b",
    r"\b(cancion|canción|poema|cuento\s+de\s+hadas|chiste\s+de\s+humor)\b",
    r"\b(presidente|elecciones|partido\s+politico|partido\s+político|votar\s+por)\b",
    r"\b(horoscopo|horóscopo|astrologia|astrología|signo\s+zodiacal|virgo|aries|tauro|geminis|géminis|cancer|cáncer|leo|libra|escorpio|sagitario|capricornio|acuario|piscis)\b",
    r"\b(resuelve\s+esta\s+ecuacion|ecuación|integral\s+definida|derivada\s+de)\b",
]

# Temas y palabras clave afines a Recursos Humanos de ChocolaTech
HR_WHITELIST_KEYWORDS = [
    "vacacion", "vacaciones", "descanso", "dias libres", "feriado",
    "banco de horas", "horas extra", "horas extras", "sobretiempo", "compensatorio",
    "modalidad", "remoto", "hibrido", "híbrido", "presencial", "home office", "teletrabajo",
    "beneficio", "beneficios", "seguro", "sgmm", "chocobox", "beca", "capacitacion", "descuento",
    "conducta", "etica", "ética", "acoso", "denuncia", "salario", "sueldo", "nomina", "nómina",
    "empleado", "colaborador", "ingreso", "puesto", "departamento", "equipo", "licencia", "permiso",
    "rrhh", "recursos humanos", "chocolatech", "politica", "política", "reglamento", "contrato",
    "nombre", "soy ", "me llamo", "mi nombre", "hola", "buenos dias", "buenas tardes", "buenas noches",
    "gracias", "adios", "hasta luego", "ayuda", "que puedes hacer", "quien eres", "cuantos dias", "saldo"
]


class HRGuardrails:
    """Validador multicapa de intención y seguridad temática."""

    @staticmethod
    def validar_consulta(texto: str) -> Tuple[bool, str]:
        """
        Evalúa si la entrada del usuario es válida dentro del dominio de HR Buddy.
        Retorna:
            (es_valido: bool, motivo_o_diagnostico: str)
        """
        if not texto or not texto.strip():
            return False, "consulta_vacia"

        texto_limpio = texto.strip().lower()

        # 1. Filtro contra Inyecciones de Prompt
        for pattern in INJECTION_PATTERNS:
            if re.search(pattern, texto_limpio, re.IGNORECASE):
                return False, "prompt_injection_detectada"

        # 2. Filtro explícito de temas fuera de dominio (evaluado con alta prioridad)
        for pattern in OFFTOPIC_PATTERNS:
            if re.search(pattern, texto_limpio, re.IGNORECASE):
                return False, "tema_fuera_de_dominio"

        # 3. Saludos cortos o presentaciones siempre permitidos
        saludos_basicos = ["hola", "buen dia", "buenos dias", "buenas", "buenas tardes", "buenas noches", "hey"]
        if any(texto_limpio == s or texto_limpio.startswith(s + " ") for s in saludos_basicos):
            return True, "saludo_permitido"

        # 4. Presentaciones con nombre (ej. "soy Juan Silva", "me llamo Carlos")
        if re.search(r"\b(soy|me llamo|mi nombre es)\b", texto_limpio):
            return True, "identificacion_permitida"

        # 5. Verificación de afinidad temática de RR. HH.
        tiene_afinidad_rrhh = any(kw in texto_limpio for kw in HR_WHITELIST_KEYWORDS)
        if tiene_afinidad_rrhh:
            return True, "tema_rrhh_valido"

        # Si el mensaje es muy corto (ej: un nombre solo como "Juan Silva" o "Eric Monné"), permitir
        palabras = texto_limpio.split()
        if 1 <= len(palabras) <= 4:
            return True, "posible_nombre_o_pregunta_corta"

        # Por defecto, si no guarda ninguna relación con RR. HH., rechazar amablemente
        return False, "sin_afinidad_rrhh"
