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

-- Para mejores prácticas, cambiar el DEFAULT:
ALTER TABLE cliente 
MODIFY COLUMN fecha_creacion DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP;


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
