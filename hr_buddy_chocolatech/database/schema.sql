-- =====================================================================
-- Base de Datos Corporativa ChocolaTech - Módulo de Recursos Humanos
-- Inmersión Agentes de IA - Alura Latam
-- =====================================================================

CREATE DATABASE IF NOT EXISTS chocolatech CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE chocolatech;

DROP TABLE IF EXISTS empleados;

CREATE TABLE empleados (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    email VARCHAR(150) NOT NULL UNIQUE,
    departamento VARCHAR(100) NOT NULL,
    puesto VARCHAR(100) NOT NULL,
    fecha_ingreso DATE NOT NULL,
    saldo_vacaciones INT NOT NULL DEFAULT 0,
    banco_horas DECIMAL(5,1) NOT NULL DEFAULT 0,
    modalidad VARCHAR(20) NOT NULL DEFAULT 'hibrido'
);

-- Inserción de colaboradores de prueba ChocolaTech
INSERT INTO empleados (nombre, email, departamento, puesto, fecha_ingreso, saldo_vacaciones, banco_horas, modalidad) VALUES
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
('Eric Monné', 'eric.monne@chocolatech.com', 'Producto', 'Instructor de Cursos', '2024-01-15', 25, 8.0, 'hibrido');
