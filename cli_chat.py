"""
Consola Interactiva de Pruebas (CLI) para HR Buddy (ChocolaTech).
Permite dialogar directamente con el agente en la terminal, validando:
- Identificación de colaboradores (MySQL)
- Políticas RAG
- Guardrails temáticos
- Persistencia de contexto en turnos múltiples
"""

import sys

# Asegurar codificación UTF-8 en consolas Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from hr_buddy_chocolatech.agent.core import hr_buddy_agent
from hr_buddy_chocolatech.agent.memory import memory_manager


def main():
    session_id = "cli-test-user-1"
    print("=" * 70)
    print("🍫 HR BUDDY · ASISTENTE DE RECURSOS HUMANOS DE CHOCOLATECH (CLI)")
    print("=" * 70)
    print("Instrucciones:")
    print(" • Escribe tus preguntas en lenguaje natural.")
    print(" • Puedes presentarte (ej: 'Hola, soy Juan Silva') para consultar tus saldos.")
    print(" • Escribe '/reset' para limpiar la memoria de sesión.")
    print(" • Escribe 'salir' o 'exit' para terminar.\n")

    while True:
        try:
            user_input = input("👤 Tú: ").strip()
            if not user_input:
                continue

            if user_input.lower() in ["salir", "exit", "quit"]:
                print("\n👋 ¡Hasta luego! Que tengas un excelente día en ChocolaTech. 🍫\n")
                break

            if user_input.lower() == "/reset":
                memory_manager.clear_session(session_id)
                print("\n🔄 Memoria de sesión reiniciada con éxito.\n")
                continue

            print("\n⏳ HR Buddy procesando...")
            result = hr_buddy_agent.process_message(session_id=session_id, user_message=user_input)

            print("\n🍫 HR Buddy:")
            print(result["answer"])

            # Info de auditoría
            meta_items = []
            if result.get("employee"):
                emp = result["employee"]
                meta_items.append(f"Empleado: {emp['nombre']} [{emp['departamento']}]")
            if result.get("sources"):
                meta_items.append(f"RAG: {', '.join(result['sources'])}")
            if not result.get("guardrails_passed", True):
                meta_items.append(f"Guardrail: BLOQUEADO ({result.get('guardrail_reason')})")

            if meta_items:
                print(f"\n   [Auditoría: {' | '.join(meta_items)}]")

            print("-" * 70 + "\n")

        except (KeyboardInterrupt, EOFError):
            print("\n\nSesión finalizada.")
            break


if __name__ == "__main__":
    main()
