"""
Pruebas unitarias para el módulo de base de datos de empleados de ChocolaTech.
"""

import unittest
from hr_buddy_chocolatech.database.db import db_manager


class TestDatabaseManager(unittest.TestCase):

    def test_obtener_todos_empleados(self):
        empleados = db_manager.obtener_todos()
        self.assertGreaterEqual(len(empleados), 11)
        nombres = [e["nombre"] for e in empleados]
        self.assertIn("Juan Silva", nombres)
        self.assertIn("Eric Monné", nombres)
        self.assertIn("María Gonzalez", nombres)

    def test_buscar_empleado_exacto(self):
        emp = db_manager.buscar_empleado("Juan Silva")
        self.assertIsNotNone(emp)
        self.assertEqual(emp["departamento"], "Ingeniería")
        self.assertEqual(emp["saldo_vacaciones"], 20)
        self.assertEqual(emp["modalidad"], "hibrido")

    def test_buscar_empleado_tolerancia_acentos_y_mayusculas(self):
        # Búsqueda sin tilde y en minúscula
        emp = db_manager.buscar_empleado("maria gonzalez")
        self.assertIsNotNone(emp)
        self.assertEqual(emp["nombre"], "María Gonzalez")
        self.assertEqual(emp["saldo_vacaciones"], 5)
        self.assertEqual(float(emp["banco_horas"]), 12.5)

    def test_buscar_instructor_eric_monne(self):
        emp = db_manager.buscar_empleado("Eric Monné")
        self.assertIsNotNone(emp)
        self.assertEqual(emp["puesto"], "Instructor de Cursos")
        self.assertEqual(emp["saldo_vacaciones"], 25)

    def test_buscar_empleado_inexistente(self):
        emp = db_manager.buscar_empleado("Colaborador Fantasma Desconocido")
        self.assertIsNone(emp)


if __name__ == "__main__":
    unittest.main()
