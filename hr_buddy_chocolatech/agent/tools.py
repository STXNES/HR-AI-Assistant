"""
Herramientas (Tools) de consulta para HR Buddy.
Implementa las herramientas equivalentes a los nodos de n8n:
1. Consulta MySQL ($fromAI: nombre_completo)
2. Búsqueda Vectorial RAG (Políticas de Recursos Humanos)
"""

from typing import Dict, Any, Optional, List
from hr_buddy_chocolatech.database.db import db_manager
from hr_buddy_chocolatech.rag.vector_store import rag_engine


def tool_buscar_empleado_mysql(nombre_completo: str) -> Dict[str, Any]:
    """
    Busca a un empleado en la tabla MySQL 'empleados' de ChocolaTech por su nombre completo.
    Retorna los datos del colaborador si existe, o un mensaje informativo si no se encuentra.
    """
    if not nombre_completo or not nombre_completo.strip():
        return {
            "encontrado": False,
            "mensaje": "No se proporcionó un nombre para la búsqueda."
        }

    resultado = db_manager.buscar_empleado(nombre_completo.strip())

    if resultado:
        return {
            "encontrado": True,
            "id": resultado["id"],
            "nombre": resultado["nombre"],
            "email": resultado["email"],
            "departamento": resultado["departamento"],
            "puesto": resultado["puesto"],
            "fecha_ingreso": str(resultado["fecha_ingreso"]),
            "saldo_vacaciones": resultado["saldo_vacaciones"],
            "banco_horas": float(resultado["banco_horas"]),
            "modalidad": resultado["modalidad"]
        }
    else:
        return {
            "encontrado": False,
            "nombre_buscado": nombre_completo,
            "mensaje": (
                f"El colaborador '{nombre_completo}' no figura en la base de datos de empleados activos. "
                "No deben asumirse ni inventarse datos personales."
            )
        }


def tool_consultar_politicas_rrhh(consulta: str, top_k: int = 3) -> Dict[str, Any]:
    """
    Realiza una búsqueda semántica en la base de conocimientos RAG con las políticas corporativas
    de ChocolaTech (Vacaciones, Banco de Horas, Modalidades de Trabajo, Beneficios y Código Ético).
    """
    if not consulta or not consulta.strip():
        return {"resultados": [], "contexto_texto": "Consulta vacía."}

    resultados = rag_engine.search(consulta, top_k=top_k)
    contexto_texto = rag_engine.format_for_context(resultados)

    return {
        "cantidad_resultados": len(resultados),
        "resultados": resultados,
        "contexto_texto": contexto_texto
    }
