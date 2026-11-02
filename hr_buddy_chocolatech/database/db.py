"""
Módulo de Gestión de Base de Datos para HR Buddy (ChocolaTech).
Soporta MySQL nativo y cuenta con fallback automático a SQLite para desarrollo
local inmediato sin dependencias externas obligatorias.
"""

import os
import re
import sqlite3
import unicodedata
from typing import Dict, Any, Optional, List
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

DB_TYPE = os.getenv("DB_TYPE", "sqlite").lower()  # 'mysql' o 'sqlite'
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "chocolatech123")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "chocolatech")

SQLITE_PATH = Path(__file__).resolve().parent / "chocolatech_local.db"
SCHEMA_SQL_PATH = Path(__file__).resolve().parent / "schema.sql"


def normalize_text(text: str) -> str:
    """Elimina acentos y normaliza a minúsculas para búsquedas flexibles."""
    if not text:
        return ""
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return text.lower().strip()


class DatabaseManager:
    """Administrador de conexiones de base de datos con failover transparente."""

    def __init__(self, prefer_mysql: bool = (DB_TYPE == "mysql")):
        self.prefer_mysql = prefer_mysql
        self.is_mysql_active = False
        self._mysql_conn = None
        self._init_connection()

    def _init_connection(self):
        """Intenta conectar a MySQL; si falla, inicializa SQLite automáticamente."""
        if self.prefer_mysql:
            try:
                import pymysql
                import pymysql.cursors

                self._mysql_conn = pymysql.connect(
                    host=MYSQL_HOST,
                    port=MYSQL_PORT,
                    user=MYSQL_USER,
                    password=MYSQL_PASSWORD,
                    database=MYSQL_DATABASE,
                    cursorclass=pymysql.cursors.DictCursor,
                    autocommit=True
                )
                self.is_mysql_active = True
                print(" Conexión exitosa a MySQL (ChocolaTech DB)")
                return
            except Exception as e:
                print(f" No fue posible conectar a MySQL ({e}). Activando fallback local SQLite...")

        self.is_mysql_active = False
        self._init_sqlite()

    def _init_sqlite(self):
        """Inicializa la base SQLite con el esquema y datos de prueba provistos."""
        conn = sqlite3.connect(str(SQLITE_PATH))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Crear tabla si no existe
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS empleados (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                departamento TEXT NOT NULL,
                puesto TEXT NOT NULL,
                fecha_ingreso TEXT NOT NULL,
                saldo_vacaciones INTEGER NOT NULL DEFAULT 0,
                banco_horas REAL NOT NULL DEFAULT 0,
                modalidad TEXT NOT NULL DEFAULT 'hibrido'
            );
        """)

        # Verificar si hay registros
        cursor.execute("SELECT COUNT(*) FROM empleados")
        count = cursor.fetchone()[0]
        if count == 0:
            datos_iniciales = [
                ('Juan Silva', 'juan.silva@empresa.com', 'Ingeniería', 'Ingeniero de Software', '2022-03-10', 20, 0.0, 'hibrido'),
                ('María Gonzalez', 'maria.gonzalez@empresa.com', 'Recursos Humanos', 'Analista de RR. HH.', '2021-05-15', 5, 12.5, 'hibrido'),
                ('Carlos Olivera', 'carlos.olivera@empresa.com', 'Finanzas', 'Analista Financiero', '2023-01-20', 0, 0.0, 'presencial'),
                ('Ana Lima', 'ana.lima@empresa.com', 'Marketing', 'Especialista en Marketing', '2020-11-05', 15, -4.0, 'remoto'),
                ('Pedro Santos', 'pedro.santos@empresa.com', 'Ventas', 'Ejecutivo de Ventas', '2022-08-01', 10, 8.0, 'hibrido'),
                ('Fernanda Costa', 'fernanda.costa@empresa.com', 'Operaciones', 'Gerente de Operaciones', '2019-02-12', 30, 0.0, 'presencial'),
                ('Rafael Mendez', 'rafael.mendez@empresa.com', 'TI', 'Analista de Soporte', '2023-06-10', 0, 15.5, 'hibrido'),
                ('Juliana García', 'juliana.garcía@empresa.com', 'Ingeniería', 'Desarrolladora Front-end', '2021-09-25', 12, 0.0, 'remoto'),
                ('Bruno Alvarez', 'bruno.alvarez@empresa.com', 'Diseño', 'Diseñador UX/UI', '2022-04-18', 8, 3.5, 'hibrido'),
                ('Camila Herrera', 'camila.herrera@empresa.com', 'Atención al Cliente', 'Analista de Atención al Cliente', '2024-01-05', 0, 0.0, 'hibrido'),
                ('Eric Monné', 'eric.monne@chocolatech.com', 'Producto', 'Instructor de Cursos', '2024-01-15', 25, 8.0, 'hibrido')
            ]
            cursor.executemany("""
                INSERT INTO empleados (nombre, email, departamento, puesto, fecha_ingreso, saldo_vacaciones, banco_horas, modalidad)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, datos_iniciales)
            conn.commit()
            print(f" SQLite inicializada con {len(datos_iniciales)} colaboradores de ChocolaTech.")
        conn.close()

    def get_sqlite_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(SQLITE_PATH))
        conn.row_factory = sqlite3.Row
        return conn

    def buscar_empleado(self, nombre_completo: str) -> Optional[Dict[str, Any]]:
        """
        Busca un colaborador por su nombre (exacto o aproximado con tolerancia a acentos).
        Equivalente a la herramienta $fromAI en el flujo de orquestación.
        """
        if not nombre_completo or not nombre_completo.strip():
            return None

        busqueda_limpia = normalize_text(nombre_completo)

        # 1. Intento vía MySQL si está activo
        if self.is_mysql_active and self._mysql_conn:
            try:
                self._mysql_conn.ping(reconnect=True)
                with self._mysql_conn.cursor() as cursor:
                    # Búsqueda exacta primero
                    cursor.execute(
                        "SELECT * FROM empleados WHERE LOWER(nombre) = LOWER(%s) LIMIT 1",
                        (nombre_completo.strip(),)
                    )
                    emp = cursor.fetchone()
                    if emp:
                        return dict(emp)

                    # Búsqueda LIKE tolerante
                    cursor.execute(
                        "SELECT * FROM empleados WHERE LOWER(nombre) LIKE LOWER(%s) LIMIT 1",
                        (f"%{nombre_completo.strip()}%",)
                    )
                    emp = cursor.fetchone()
                    if emp:
                        return dict(emp)
            except Exception as e:
                print(f"Error consultando MySQL: {e}. Reintentando vía SQLite...")

        # 2. Consulta en SQLite (con normalización de tildes en memoria)
        conn = self.get_sqlite_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM empleados")
        filas = cursor.fetchall()
        conn.close()

        # Coincidencia exacta normalizada
        for f in filas:
            if normalize_text(f["nombre"]) == busqueda_limpia:
                return dict(f)

        # Coincidencia parcial (subcadena)
        for f in filas:
            nombre_db = normalize_text(f["nombre"])
            if busqueda_limpia in nombre_db or nombre_db in busqueda_limpia:
                return dict(f)

        return None

    def obtener_todos(self) -> List[Dict[str, Any]]:
        """Retorna el listado completo de colaboradores para propósitos de gestión."""
        if self.is_mysql_active and self._mysql_conn:
            try:
                self._mysql_conn.ping(reconnect=True)
                with self._mysql_conn.cursor() as cursor:
                    cursor.execute("SELECT * FROM empleados ORDER BY id ASC")
                    return [dict(row) for row in cursor.fetchall()]
            except Exception as e:
                print(f"Error en MySQL obtener_todos: {e}")

        conn = self.get_sqlite_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM empleados ORDER BY id ASC")
        filas = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return filas


# Instancia singleton para importación directa
db_manager = DatabaseManager()
