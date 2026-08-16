-- --------------------------------------------------------
-- Host:                         127.0.0.1
-- Versión del servidor:         9.5.0 - MySQL Community Server - GPL
-- SO del servidor:              Win64
-- HeidiSQL Versión:             12.14.0.7165
-- --------------------------------------------------------

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET NAMES utf8 */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;


-- Volcando estructura de base de datos para agrovet
CREATE DATABASE IF NOT EXISTS `agrovet` /*!40100 DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci */ /*!80016 DEFAULT ENCRYPTION='N' */;
USE `agrovet`;

-- Volcando estructura para tabla agrovet.cliente
CREATE TABLE IF NOT EXISTS `cliente` (
  `cedula` varchar(20) COLLATE utf8mb4_general_ci NOT NULL,
  `nombre` varchar(100) COLLATE utf8mb4_general_ci NOT NULL,
  `telefono` varchar(15) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `correo` varchar(100) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `direccion` text COLLATE utf8mb4_general_ci,
  PRIMARY KEY (`cedula`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- Volcando datos para la tabla agrovet.cliente: ~4 rows (aproximadamente)
INSERT INTO `cliente` (`cedula`, `nombre`, `telefono`, `correo`, `direccion`) VALUES
	('1012345678', 'Hacienda Santa María', '555-2001', 'santamaria@hacienda.com', 'Km 12 Vía a la Costa'),
	('1023456789', 'Rancho El Torito', '555-2002', NULL, 'Sector La Pradera'),
	('1034567890', 'Finca La Esperanza', '555-2003', 'esperanza@ganaderia.com', 'Valle de los Chillos');

-- Volcando estructura para tabla agrovet.creditos
CREATE TABLE IF NOT EXISTS `creditos` (
  `id` int NOT NULL AUTO_INCREMENT,
  `venta_id` int NOT NULL,
  `cliente_cedula` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `anticipo` decimal(10,2) NOT NULL DEFAULT '0.00',
  `deuda_inicial` decimal(10,2) NOT NULL DEFAULT '0.00',
  `saldo_pendiente` decimal(10,2) NOT NULL DEFAULT '0.00',
  `dias_credito` int NOT NULL DEFAULT '30',
  `fecha_inicio` date NOT NULL,
  `fecha_vencimiento` date NOT NULL,
  `estado` enum('pendiente','pagado','vencido') COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'pendiente',
  `abonos_realizados` decimal(10,2) NOT NULL DEFAULT '0.00',
  `ultimo_pago` date DEFAULT NULL,
  `observaciones` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci,
  PRIMARY KEY (`id`),
  KEY `fk_creditos_ventas` (`venta_id`),
  KEY `fk_creditos_cliente` (`cliente_cedula`),
  KEY `idx_estado` (`estado`),
  KEY `idx_fecha_vencimiento` (`fecha_vencimiento`),
  CONSTRAINT `fk_creditos_cliente` FOREIGN KEY (`cliente_cedula`) REFERENCES `cliente` (`cedula`) ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT `fk_creditos_ventas` FOREIGN KEY (`venta_id`) REFERENCES `ventas` (`id`) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- Volcando datos para la tabla agrovet.creditos: ~0 rows (aproximadamente)

-- Volcando estructura para tabla agrovet.detalle_venta
CREATE TABLE IF NOT EXISTS `detalle_venta` (
  `id` int NOT NULL AUTO_INCREMENT,
  `id_venta` int NOT NULL,
  `id_producto` int NOT NULL,
  `fecha_venta` date NOT NULL,
  `cantidad_vendida` int NOT NULL,
  `precio_unidad` decimal(10,2) NOT NULL,
  `precio_neto` decimal(10,2) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `id_venta` (`id_venta`),
  KEY `id_producto` (`id_producto`),
  KEY `idx_fecha_producto` (`fecha_venta`,`id_producto`),
  CONSTRAINT `detalle_venta_ibfk_1` FOREIGN KEY (`id_venta`) REFERENCES `ventas` (`id`) ON DELETE CASCADE,
  CONSTRAINT `detalle_venta_ibfk_2` FOREIGN KEY (`id_producto`) REFERENCES `productos` (`id`) ON DELETE RESTRICT
) ENGINE=InnoDB AUTO_INCREMENT=19 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- Volcando datos para la tabla agrovet.detalle_venta: ~0 rows (aproximadamente)

-- Volcando estructura para tabla agrovet.productos
CREATE TABLE IF NOT EXISTS `productos` (
  `id` int NOT NULL AUTO_INCREMENT,
  `nombre` varchar(100) COLLATE utf8mb4_general_ci NOT NULL,
  `descripcion` text COLLATE utf8mb4_general_ci,
  `categoria` varchar(50) COLLATE utf8mb4_general_ci NOT NULL,
  `cantidad` int DEFAULT '0',
  `presentacion` varchar(50) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `proveedor` varchar(15) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `precio_costo` int DEFAULT NULL,
  `precio_venta` int DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `proveedor` (`proveedor`),
  CONSTRAINT `productos_ibfk_1` FOREIGN KEY (`proveedor`) REFERENCES `proveedor` (`telefono`) ON DELETE SET NULL
) ENGINE=InnoDB AUTO_INCREMENT=332 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- Volcando datos para la tabla agrovet.productos: ~41 rows (aproximadamente)
INSERT INTO `productos` (`id`, `nombre`, `descripcion`, `categoria`, `cantidad`, `presentacion`, `proveedor`, `precio_costo`, `precio_venta`) VALUES
	(286, 'Oxitetraciclina 20%', 'Antibiótico de amplio espectro para ganado', 'ANTIBIOTICOS', 25, 'Frasco 500ml', NULL, 45000, 68000),
	(287, 'Penicilina Estreptomicina', 'Combinación antibiótica para infecciones', 'ANTIBIOTICOS', 18, 'Frasco 250ml', NULL, 38000, 55000),
	(288, 'Bioestimulante Foliar', 'Estimulante natural para crecimiento vegetal', 'BIOESTIMULANTES', 35, 'Litro', NULL, 25000, 38000),
	(289, 'Raíz Fuerte', 'Bioestimulante radicular para cultivos', 'BIOESTIMULANTES', 22, 'Kilo', NULL, 18000, 28000),
	(290, 'Trichoderma Harzianum', 'Control biológico de hongos', 'BIOLOGICOS', 15, 'Kilo', NULL, 35000, 52000),
	(291, 'Bacillus Thuringiensis', 'Control biológico de insectos', 'BIOLOGICOS', 28, '500 gramos', NULL, 28000, 42000),
	(292, 'Adherente Vegetal', 'Mejora la adherencia de agroquímicos', 'COADYUVANTES', 37, 'Litro', NULL, 22000, 33000),
	(293, 'Antiespumante', 'Reduce la formación de espuma en mezclas', 'COADYUVANTES', 29, '500 ml', NULL, 15000, 24000),
	(294, 'Concentrado Pollo Engorde', 'Alimento para pollos de engorde', 'CONCENTRADO AVES PRODUCCION', 120, 'Saco 40kg', NULL, 85000, 125000),
	(295, 'Concentrado Gallina Ponedora', 'Alimento para gallinas ponedoras', 'CONCENTRADO AVES PRODUCCION', 85, 'Saco 40kg', NULL, 92000, 135000),
	(296, 'Concentrado Ganado Lechero', 'Alimento para ganado lechero', 'CONCENTRADOS', 65, 'Saco 50kg', NULL, 105000, 155000),
	(297, 'Concentrado Cerdos Ceba', 'Alimento para cerdos en ceba', 'CONCENTRADOS', 45, 'Saco 50kg', NULL, 95000, 140000),
	(298, 'Concentrado Gato Adulto', 'Alimento balanceado para gatos adultos', 'CONCENTRADOS GATOS', 55, 'Bolsa 7.5kg', NULL, 65000, 95000),
	(299, 'Concentrado Gatitos', 'Alimento para gatitos hasta 1 año', 'CONCENTRADOS GATOS', 38, 'Bolsa 4kg', NULL, 42000, 65000),
	(300, 'Concentrado Perro Adulto', 'Alimento balanceado para perros adultos', 'CONCENTRADOS PERROS', 72, 'Bolsa 15kg', NULL, 95000, 145000),
	(301, 'Concentrado Cachorros', 'Alimento para cachorros hasta 1 año', 'CONCENTRADOS PERROS', 41, 'Bolsa 8kg', NULL, 68000, 105000),
	(302, 'Cal Agrícola', 'Enmienda para corrección de pH de suelos', 'ENMIENDA', 90, 'Saco 50kg', NULL, 28000, 42000),
	(303, 'Dolomita', 'Enmienda rica en calcio y magnesio', 'ENMIENDA', 67, 'Saco 50kg', NULL, 32000, 48000),
	(304, 'Urea 46%', 'Fertilizante nitrogenado', 'FERTILIZANTES', 110, 'Saco 50kg', NULL, 75000, 115000),
	(305, 'Triple 15', 'Fertilizante completo NPK 15-15-15', 'FERTILIZANTES', 95, 'Saco 50kg', NULL, 82000, 125000),
	(306, 'Mancozeb 80%', 'Fungicida protector de amplio espectro', 'FUNGICIDAS', 7, 'Kilo', NULL, 45000, 68000),
	(307, 'Azoxystrobin', 'Fungicida sistémico para cultivos', 'FUNGICIDAS', 27, '500 ml', NULL, 68000, 102000),
	(308, 'Glifosato 36%', 'Herbicida no selectivo sistémico', 'HERBICIDAS', 58, 'Litro', NULL, 38000, 58000),
	(309, '2,4-D Amina', 'Herbicida selectivo para hoja ancha', 'HERBICIDAS', 36, 'Litro', NULL, 32000, 48000),
	(310, 'Cipermetrina 10%', 'Insecticida piretroide de contacto', 'INSECTICIDAS', 42, 'Litro', NULL, 42000, 65000),
	(311, 'Imidacloprid', 'Insecticida sistémico neonicotinoide', 'INSECTICIDAS', 33, '500 ml', NULL, 55000, 85000),
	(312, 'Maíz Amarillo', 'Maíz amarillo para alimentación animal', 'MAIZ', 200, 'Saco 50kg', NULL, 65000, 98000),
	(313, 'Maíz Blanco', 'Maíz blanco para consumo humano', 'MAIZ', 150, 'Saco 50kg', NULL, 72000, 110000),
	(314, 'Shampoo Antipulgas', 'Shampoo para mascotas con efecto antipulgas', 'MASCOTAS', 62, 'Botella 500ml', NULL, 18000, 28000),
	(315, 'Collar Antipulgas', 'Collar de protección contra pulgas y garrapatas', 'MASCOTAS', 48, 'Unidad', NULL, 25000, 38000),
	(316, 'Etefón 480', 'Regulador de crecimiento para piña', 'REGULADOR DE CRECIMIENTO', 24, 'Litro', NULL, 58000, 88000),
	(317, 'Clormequat', 'Regulador de crecimiento para cereales', 'REGULADOR DE CRECIMIENTO', 19, 'Kilo', NULL, 42000, 65000),
	(318, 'Membrana Bomba 3"', 'Membrana para bomba de mochila', 'REPUESTOS BOMBAS Y ESTACIONARIAS', 75, 'Unidad', NULL, 15000, 25000),
	(319, 'Válvula Check', 'Válvula de retención para bombas', 'REPUESTOS BOMBAS Y ESTACIONARIAS', 52, 'Unidad', NULL, 8000, 15000),
	(320, 'Sal Mineralizada', 'Suplemento mineral para ganado', 'SALES GANADERAS', 88, 'Bloque 5kg', NULL, 12000, 20000),
	(321, 'Sal con Fósforo', 'Sal mineralizada con fósforo para rumiantes', 'SALES GANADERAS', 10, 'Saco 25kg', NULL, 35000, 55000),
	(322, 'Semilla Maíz Híbrido', 'Semilla de maíz híbrido para siembra', 'SEMILLAS', 10, 'Saco 25kg', NULL, 185000, 280000),
	(323, 'Semilla Pasto Imperial', 'Semilla de pasto para ganadería', 'SEMILLAS', 10, 'Saco 20kg', NULL, 95000, 145000),
	(324, 'Jeringa Desechable 10ml', 'Jeringas desechables para uso veterinario', 'VETERINARIA', 10, 'Paquete 100u', NULL, 35000, 55000),
	(325, 'Guantes de Examen', 'Guantes de látex para examen veterinario', 'VETERINARIA', 10, 'Caja 100u', NULL, 28000, 45000),
	(330, 'Glifocafe', 'Hervicida', 'HERBICIDAS', 5, 'Litro', NULL, 14500, 17000);

-- Volcando estructura para tabla agrovet.proveedor
CREATE TABLE IF NOT EXISTS `proveedor` (
  `telefono` varchar(15) COLLATE utf8mb4_general_ci NOT NULL,
  `nombre_empresa` varchar(100) COLLATE utf8mb4_general_ci NOT NULL,
  `nombre_proveedor` varchar(100) COLLATE utf8mb4_general_ci NOT NULL,
  `correo` varchar(100) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `estado` enum('activo','inactivo') COLLATE utf8mb4_general_ci DEFAULT 'activo',
  `fecha_registro` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `producto` varchar(500) COLLATE utf8mb4_general_ci DEFAULT NULL,
  PRIMARY KEY (`telefono`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- Volcando datos para la tabla agrovet.proveedor: ~1 rows (aproximadamente)

-- Volcando estructura para tabla agrovet.reporte_caja
CREATE TABLE IF NOT EXISTS `reporte_caja` (
  `id` int NOT NULL AUTO_INCREMENT,
  `ingresos` decimal(10,2) DEFAULT '0.00',
  `razon_ingreso` varchar(200) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `fecha_ingreso` datetime DEFAULT NULL,
  `categoria` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT 'otros',
  `egresos` decimal(10,2) DEFAULT '0.00',
  `razon_egreso` varchar(200) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `fecha_egreso` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_categoria` (`categoria`)
) ENGINE=InnoDB AUTO_INCREMENT=28 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- Volcando datos para la tabla agrovet.reporte_caja: ~2 rows (aproximadamente)

-- Volcando estructura para tabla agrovet.ventas
CREATE TABLE IF NOT EXISTS `ventas` (
  `id` int NOT NULL AUTO_INCREMENT,
  `numero_venta` int DEFAULT NULL,
  `fecha_dia` date NOT NULL,
  `fecha_hora` time NOT NULL,
  `nombre_cliente` varchar(100) COLLATE utf8mb4_general_ci NOT NULL,
  `direccion_cliente` text COLLATE utf8mb4_general_ci,
  `telefono_cliente` varchar(15) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `tipo_pago` varchar(50) COLLATE utf8mb4_general_ci NOT NULL,
  `cliente_cedula` varchar(20) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `subtotal` decimal(10,2) NOT NULL DEFAULT '0.00',
  `descuento` decimal(10,2) NOT NULL DEFAULT '0.00',
  `total` decimal(10,2) NOT NULL DEFAULT '0.00',
  `dias_credito` int DEFAULT NULL,
  `submetodo_banco` varchar(50) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `usuario_id` int DEFAULT '1',
  `estado` varchar(20) COLLATE utf8mb4_general_ci DEFAULT 'completada',
  PRIMARY KEY (`id`),
  KEY `cliente_cedula` (`cliente_cedula`),
  KEY `idx_fecha` (`fecha_dia`),
  KEY `idx_numero_venta` (`numero_venta`),
  CONSTRAINT `ventas_ibfk_1` FOREIGN KEY (`cliente_cedula`) REFERENCES `cliente` (`cedula`) ON DELETE SET NULL
) ENGINE=InnoDB AUTO_INCREMENT=19 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- Volcando datos para la tabla agrovet.ventas: ~0 rows (aproximadamente)

/*!40103 SET TIME_ZONE=IFNULL(@OLD_TIME_ZONE, 'system') */;
/*!40101 SET SQL_MODE=IFNULL(@OLD_SQL_MODE, '') */;
/*!40014 SET FOREIGN_KEY_CHECKS=IFNULL(@OLD_FOREIGN_KEY_CHECKS, 1) */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40111 SET SQL_NOTES=IFNULL(@OLD_SQL_NOTES, 1) */;
