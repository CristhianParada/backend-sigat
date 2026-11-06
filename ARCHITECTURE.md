# Arquitectura — SIGAT Backend

## 1. Visión general

SIGAT Backend es una aplicación desarrollada en Python 3.12 con FastAPI, organizada bajo una arquitectura de monolito modular.

Su función es proporcionar servicios y operaciones centralizadas para los clientes web y móvil del sistema, mediante una API HTTP con contratos de comunicación definidos.

La arquitectura busca mantener una separación clara de responsabilidades, facilitar el mantenimiento del código y permitir la evolución independiente de las distintas áreas funcionales.

## 2. Organización por capas

El backend se organiza en cinco capas principales:

```text
API
 │
 ▼
Módulos funcionales
 │
 ▼
Infraestructura
 │
 ▼
Componentes compartidos
 │
 ▼
Configuración
```

Cada capa tiene una responsabilidad específica:

| Capa | Responsabilidad |
|---|---|
| API | Gestiona las solicitudes HTTP, las respuestas, las validaciones y la comunicación con los clientes. |
| Módulos funcionales | Agrupa los casos de uso y las reglas de negocio de cada área del sistema. |
| Infraestructura | Proporciona los mecanismos de acceso a bases de datos, seguridad, almacenamiento y servicios externos. |
| Componentes compartidos | Contiene elementos reutilizables, tipos comunes y componentes transversales. |
| Configuración | Centraliza los parámetros necesarios para ejecutar la aplicación en diferentes entornos. |

Esta separación permite reducir el acoplamiento entre componentes y mantener una organización coherente del código.

## 3. Módulos funcionales

La aplicación se divide en módulos que agrupan funcionalidades relacionadas con la operación del sistema.

| Módulo | Responsabilidad |
|---|---|
| Identidad | Gestión de autenticación, usuarios, perfiles y control de acceso. |
| Catálogo | Consulta de información de referencia y datos geográficos. |
| Notificaciones | Gestión de avisos y comunicaciones dirigidas a los usuarios. |
| Configuración | Administración de información operativa y elementos de configuración del sistema. |
| Registro | Gestión de visitas, lecturas y registros de campo. |
| Sincronización | Intercambio y sincronización de información entre los clientes y el servidor. |
| Concepto | Procesamiento de información y generación de resultados relacionados con la evaluación fitosanitaria. |
| Planificación | Organización de actividades y tareas operativas. |
| Imágenes | Gestión de archivos y evidencias asociadas a los registros. |
| Auditoría | Consulta y seguimiento de las operaciones registradas en el sistema. |
| Administración | Gestión institucional de auditoría (audit log), bitácoras y monitoreo de salud. |
| Importación | Carga masiva de archivos CSV/Excel de campañas anteriores. |
| Laboratorio | Muestreo, remisión de especímenes y diagnóstico taxonómico. |
| Calidad | Verificaciones BPA (Buenas Prácticas Agrícolas) y criterios de calidad. |


La modularidad permite organizar las funcionalidades por dominio y facilitar su mantenimiento y evolución.

## 4. Comunicación entre componentes

Los módulos mantienen responsabilidades delimitadas y utilizan mecanismos de integración definidos por la arquitectura.

La capa API actúa como punto de entrada de las solicitudes y coordina la ejecución de los casos de uso correspondientes.

Los componentes de infraestructura proporcionan los servicios técnicos necesarios sin incorporar directamente esas responsabilidades a las reglas de negocio.

Esta organización busca favorecer:

- Separación de responsabilidades.
- Bajo acoplamiento entre módulos.
- Reutilización de componentes.
- Facilidad de pruebas y mantenimiento.
- Evolución progresiva de las funcionalidades.

## 5. Persistencia de datos

El backend utiliza PostgreSQL como sistema de gestión de bases de datos y PostGIS para el manejo de información geográfica.

El acceso a los datos se realiza mediante SQLAlchemy, utilizando operaciones SQL y mecanismos de gestión de conexiones asíncronas.

La estructura y evolución de la base de datos se administran mediante herramientas de migración.

La separación entre los datos funcionales y los componentes técnicos permite organizar las operaciones de persistencia y mantener una estructura controlada.

## 6. Seguridad

La arquitectura incorpora mecanismos para proteger el acceso a los servicios y controlar las operaciones realizadas por los usuarios.

Entre los aspectos contemplados se encuentran:

- Autenticación y gestión de sesiones.
- Validación de credenciales.
- Control de acceso según los permisos correspondientes.
- Protección de información sensible mediante variables de entorno.
- Validación de las solicitudes recibidas.
- Registro y seguimiento de operaciones relevantes.

Las credenciales, claves y parámetros sensibles deben configurarse fuera del código fuente y no deben publicarse en el repositorio.

## 7. Contrato de comunicación

La API dispone de una especificación OpenAPI que describe los servicios disponibles, sus operaciones, parámetros y estructuras de respuesta.

Este contrato sirve como referencia para la integración de los clientes web y móvil con el backend.

Su utilización permite mantener una comunicación estructurada entre los componentes del sistema y facilitar la documentación de los servicios.

## 8. Ejecución y despliegue

El backend está preparado para ejecutarse en entornos de desarrollo y despliegue mediante una configuración basada en variables de entorno.

La infraestructura de ejecución se apoya en herramientas como Docker para facilitar la configuración y distribución de la aplicación.

Los parámetros de conexión, seguridad y servicios externos deben establecerse de acuerdo con las características de cada entorno.

## 9. Principios de diseño

La arquitectura sigue estos principios:

1. **Modularidad:** organizar las funcionalidades por áreas de responsabilidad.
2. **Separación de responsabilidades:** evitar mezclar reglas de negocio, comunicación HTTP e infraestructura.
3. **Mantenibilidad:** facilitar la comprensión, modificación y evolución del código.
4. **Seguridad:** proteger los datos y controlar el acceso a las operaciones.
5. **Interoperabilidad:** mantener contratos de comunicación definidos para los clientes.
6. **Escalabilidad:** permitir la evolución de los componentes conforme crezcan las necesidades del sistema.

---

Esta documentación presenta una descripción general de la arquitectura del backend SIGAT. Los detalles de implementación, configuración y operación se mantienen en los archivos técnicos correspondientes del proyecto.