# 🌾 AGROVET YACUANQUER

**Sistema de Gestión Comercial Integrado para Agroinsumos**

---

## Descripción

**AGROVET** es una solución empresarial integral de gestión comercial diseñada específicamente para el sector agropecuario. Desarrollada con tecnologías modernas y robustas, permite automatizar y optimizar los procesos operacionales de compra, venta, inventario y atención al cliente.

Actualmente en operación en **AgroVet Yacuanquer**, ofreciendo una plataforma confiable y eficiente para la gestión diaria del negocio.

---

##  Funcionalidades principales

###  Gestión de Ventas
- Registro y procesamiento de ventas en tiempo real
- Generación automática de facturas y documentos PDF
- Historial completo de transacciones
- Gestión de métodos de pago y créditos

###  Control de Inventario
- Monitoreo de existencias de productos agrícolas y veterinarios
- Alertas de productos con bajo inventario
- Registro de entradas y salidas de productos
- Historial detallado de movimientos

###  Gestión de Clientes y Proveedores
- Base de datos centralizada de clientes
- Perfiles de proveedores
- Historial de compras y ventas por cliente
- Información de contacto organizada

###  Reportes Financieros
- Reporte de caja diario
- Análisis de ventas por período
- Estadísticas de productos más vendidos
- Gestión de créditos y pagos

###  Seguridad y Acceso
- Sistema de autenticación de usuarios
- Control de acceso por roles
- Interfaz especializada para auxiliares de atención al cliente
- Auditoría de operaciones

###  Comunicación
- Envío de correos integrado
- Notificaciones automáticas
- Respuestas a consultas de contacto

---

##  Stack Tecnológico

| Aspecto | Tecnología |
|--------|-----------|
| **Backend** | Python 3.11.9 + Flask |
| **Base de Datos** | MySQL / MariaDB |
| **Servidor** | Waitress / Gunicorn |
| **Frontend** | HTML5 + CSS3 + JavaScript Vanilla |
| **Reportes** | ReportLab, pdfkit, xhtml2pdf |
| **Email** | Flask-Mail + Mailtrap |
| **Servidor WSGI** | Waitress / Gunicorn |
| **Despliegue** | Windows + Railway (Cloud) |

---

##  Estructura del Proyecto

```
AgroVet/
├── main.py                          # Aplicación principal Flask
├── config.py                        # Configuración centralizada
├── database.py                      # Gestor de conexiones MySQL
├── setup_database.py                # Inicializador de base de datos
├── requirements.txt                 # Dependencias Python
│
├── controlador/                     # Controladores (Blueprints Flask)
│   ├── login_controller.py
│   ├── ventas_controller.py
│   ├── productos_controller.py
│   ├── inventario_controller.py
│   ├── cliente_proveedor_controller.py
│   ├── historial_venta_controller.py
│   ├── reporte_caja_controller.py
│   ├── ventas_pdf_controller.py
│   └── mail_helper.py
│
├── modelo/                          # Modelos de datos
│   ├── cliente_model.py
│   ├── producto_model.py
│   ├── venta_model.py
│   ├── inventario_model.py
│   ├── historial_venta_model.py
│   ├── reporte_caja_model.py
│   └── cliente_proveedor_modelo.py
│
├── vista/                           # Plantillas HTML
│   ├── login.html
│   ├── inicio.html
│   ├── ventas.html
│   ├── productos.html
│   ├── inventario.html
│   ├── historial_venta.html
│   ├── reporte_caja.html
│   ├── usuarios.html
│   ├── Auxiliar_cliente.html
│   └── detalle_venta.html
│
├── static/                          # Recursos estáticos
├── data/
│   ├── logs/                        # Registros de operación
│   └── backup_automatico/           # Copias de seguridad
│
├── AgroVet.sql                      # Script de base de datos
├── railway.json                     # Configuración Railway
└── README.md                        # Este archivo
```



### Módulos Principales

#### 🛒 Ventas
- Crear nuevas ventas
- Registrar productos vendidos
- Aplicar descuentos
- Generar facturas PDF
- Gestionar formas de pago

#### 📦 Productos
- Catálogo centralizado
- Precios y referencias
- Categorización
- Información de proveedores

#### 📊 Inventario
- Stock en tiempo real
- Alertas de inventario bajo
- Movimientos de entrada/salida
- Reporte de existencias

#### 👤 Clientes
- Registro de clientes
- Histórico de compras
- Gestión de créditos
- Información de contacto

#### 📈 Reportes
- Reporte de caja diario
- Historial de ventas
- Análisis de productos
- Estadísticas empresariales

---







## 📋 API Interna

La aplicación ofrece varios endpoints de utilidad:

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/api/status` | GET | Estado general del sistema |
| `/api/diagnostico` | GET | Diagnóstico técnico |
| `/api/test-email` | POST | Prueba envío de correos |
| `/api/contacto` | POST | Formulario de contacto |
| `/api/dashboard/estadisticas` | GET | Estadísticas del dashboard |




## 📦 Compilación a Ejecutable

El proyecto incluye scripts para compilar a `.exe` en Windows:

```bash
.\crear_exe.bat
```

Genera:
- `AGROVET.exe` - Aplicación compilada
- `setup_database.exe` - Instalador de BD

---

## 👥 Equipo y Contacto

**Desarrollador:** Miguel Ángel Gutiérrez López  
**Empresa:** AgroVet Yacuanquer  
**Teléfono:** 3217470975  
**Ubicación:** Yacuanquer, Nariño, Colombia

---

## 📄 Licencia

Este proyecto es propiedad de **AgroVet Yacuanquer** y está reservado para uso interno.

---

## 🔐 Seguridad

- **Cambiar credenciales por defecto antes de producción**
- Mantener MySQL actualizado
- Realizar backups regulares
- Usar HTTPS en despliegues públicos
- Revisar logs periódicamente

---

## 📚 Recursos Adicionales

- [Documentación Flask](https://flask.palletsprojects.com/)
- [MySQL Connector/Python](https://dev.mysql.com/doc/connector-python/en/)
- [Railway Deployment](https://railway.app/docs)

---

## 📊 Próximos Pasos: Análisis de Datos

A cierre de año fiscal 2026, se realizará un **análisis integral del desempeño financiero y operacional de AgroVet Yacuanquer** utilizando los datos recopilados durante este período.

Este proyecto de análisis tiene como objetivos:

- **Extraer insights** de patrones de venta, productos más rentables y comportamiento del cliente
- **Optimizar decisiones comerciales** basadas en datos históricos
- **Identificar oportunidades** de crecimiento y eficiencia operacional
- **Incursionar en ciencia de datos** como área complementaria de desarrollo profesional

Los resultados de este análisis permitirán fortalecer la estrategia comercial de AgroVet y sentar las bases para implementar modelos predictivos en futuras versiones del sistema.

---

**Última actualización:** Agosto 18 2026  
**Versión:** 21 
**Estado:** En producción
