"""
Pruebas del motor RAG y búsqueda documental de políticas de ChocolaTech.
"""

import unittest
from hr_buddy_chocolatech.rag.vector_store import rag_engine


class TestPolicyRAG(unittest.TestCase):

    def test_carga_de_documentos(self):
        self.assertGreater(len(rag_engine.documents), 0)
        archivos = {d.source_file for d in rag_engine.documents}
        self.assertIn("01_politica_vacaciones.md", archivos)
        self.assertIn("02_politica_banco_horas.md", archivos)
        self.assertIn("03_politica_modalidades_trabajo.md", archivos)
        self.assertIn("04_politica_beneficios_chocolatech.md", archivos)
        self.assertIn("05_codigo_conducta_etica.md", archivos)

    def test_busqueda_vacaciones(self):
        res = rag_engine.search("días de anticipación para solicitar vacaciones", top_k=2)
        self.assertGreater(len(res), 0)
        top = res[0]
        self.assertIn("vacaciones", top["title"].lower())
        self.assertIn("15", top["content"])  # Regla de 15 días continuos de anticipación

    def test_busqueda_banco_horas(self):
        res = rag_engine.search("límite máximo de horas acumulables en el banco de horas", top_k=2)
        self.assertGreater(len(res), 0)
        top = res[0]
        self.assertIn("40", top["content"])  # Límite de 40.0 horas positivas

    def test_busqueda_beneficios(self):
        res = rag_engine.search("beneficios médicos SGMM y ChocoBox mensual", top_k=2)
        self.assertGreater(len(res), 0)
        textos = " ".join(r["content"] for r in res)
        self.assertTrue("ChocoBox" in textos or "Seguro de Gastos Médicos" in textos)


if __name__ == "__main__":
    unittest.main()
