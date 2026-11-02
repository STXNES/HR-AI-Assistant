"""
Pruebas integrales del flujo conversacional del agente HR Buddy.
Valida:
- Turnos múltiples con persistencia de nombre
- Respuesta personalizada con datos de MySQL
- Solicitud de identificación cuando no se conoce al usuario
- Rechazo de temas off-topic sin fuga de contexto
"""

import unittest
from hr_buddy_chocolatech.agent.core import hr_buddy_agent
from hr_buddy_chocolatech.agent.memory import memory_manager


class TestAgentConversationFlow(unittest.TestCase):

    def setUp(self):
        self.session_id = "test-session-flow-101"
        memory_manager.clear_session(self.session_id)

    def tearDown(self):
        memory_manager.clear_session(self.session_id)

    def test_flujo_personalizado_colaborador_existente(self):
        # Turno 1: Presentación
        r1 = hr_buddy_agent.process_message(self.session_id, "Hola, soy Juan Silva de ingeniería")
        self.assertTrue(r1["guardrails_passed"])
        self.assertIsNotNone(r1["employee"])
        self.assertEqual(r1["employee"]["nombre"], "Juan Silva")
        self.assertIn("Juan", r1["answer"])

        # Turno 2: Pregunta por vacaciones sin repetir el nombre (debe recordar que es Juan Silva)
        r2 = hr_buddy_agent.process_message(self.session_id, "¿Cuántos días de vacaciones tengo?")
        self.assertTrue(r2["guardrails_passed"])
        self.assertIn("20", r2["answer"])  # Juan Silva tiene 20 días de vacaciones

        # Turno 3: Pregunta por banco de horas
        r3 = hr_buddy_agent.process_message(self.session_id, "¿Y cómo está mi banco de horas?")
        self.assertTrue(r3["guardrails_passed"])
        self.assertIn("0", r3["answer"])  # Juan Silva tiene 0.0 horas

    def test_flujo_usuario_anonimo_pide_identificacion(self):
        # Turno 1: Pregunta directa por sus vacaciones sin haber dicho quién es
        r1 = hr_buddy_agent.process_message(self.session_id, "¿Cuántos días tengo de mis vacaciones?")
        self.assertTrue(r1["guardrails_passed"])
        # Debe solicitar su nombre completo
        self.assertTrue("nombre completo" in r1["answer"].lower() or "quién eres" in r1["answer"].lower())

    def test_flujo_colaborador_no_registrado_no_inventa_datos(self):
        # Turno 1: Se presenta con un nombre inexistente en nómina
        r1 = hr_buddy_agent.process_message(self.session_id, "Soy Bart Simpson")
        self.assertTrue(r1["guardrails_passed"])
        self.assertIsNone(r1["employee"])  # No existe en DB

        # Turno 2: Pregunta por vacaciones
        r2 = hr_buddy_agent.process_message(self.session_id, "¿Cuántos días de vacaciones me corresponden?")
        self.assertTrue(r2["guardrails_passed"])
        # Debe responder con las políticas generales sin inventar un número personal
        self.assertIn("ChocolaTech", r2["answer"])

    def test_flujo_rechazo_guardrail_fuera_de_dominio(self):
        r = hr_buddy_agent.process_message(self.session_id, "¿Cuál es la mejor receta para preparar tacos al pastor?")
        self.assertFalse(r["guardrails_passed"])
        self.assertEqual(r["guardrail_reason"], "tema_fuera_de_dominio")
        self.assertIn("HR Buddy", r["answer"])
        self.assertIn("Recursos Humanos", r["answer"])


if __name__ == "__main__":
    unittest.main()
