# Sistema de Ventas y Gestión (Punto de Venta)

Sistema completo de Punto de Venta (POS) desarrollado en Python utilizando Tkinter y `ttkbootstrap` para la interfaz gráfica. Diseñado para gestionar ventas, inventario, clientes y facturación electrónica de manera eficiente.

## 🚀 Características Principales

*   **Punto de Venta (POS)**: Interfaz intuitiva para realizar ventas, compatible con escáner de código de barras y modo táctil.
*   **Gestión de Inventario**: Control de stock, productos, categorías y precios.
*   **Reportes**: Visualización de historial de ventas y reportes detallados.
*   **Clientes y Proveedores**: Administración de base de datos de contactos.
*   **Caja**: Control de ingresos, salidas y arqueo de caja.
*   **Facturación Electrónica**: Módulo para emisión de comprobantes electrónicos (CPE) conforme a SUNAT.
*   **Integración WhatsApp**: Envío de comprobantes y notificaciones vía WhatsApp.
*   **Seguridad**: Sistema de login y gestión de permisos por usuario.

## 🛠️ Tecnologías Utilizadas

*   **Python 3.x**: Lenguaje principal.
*   **Tkinter & ttkbootstrap**: Interfaz gráfica moderna y responsiva.
*   **SQLite**: Base de datos local.
*   **ReportLab**: Generación de PDFs (boletas, facturas).
*   **Requests**: Comunicación con APIs (SUNAT, WhatsApp).

## 📋 Requisitos Previos

Asegúrate de tener instalado Python 3.8 o superior. Las dependencias del proyecto se encuentran en `requirements.txt`.

Las librerías principales incluyen:
*   ttkbootstrap
*   requests
*   Pillow
*   pywin32
*   qrcode
*   lxml
*   signxml
*   cryptography
*   reportlab
*   pandas
*   openpyxl

## ⚙️ Instalación

1.  **Clonar el repositorio**:
    ```bash
    git clone https://github.com/EddieTacas/Proyecto-Tkinter-Punto-de-Venta.git
    cd Proyecto-Tkinter-Punto-de-Venta
    ```

2.  **Crear un entorno virtual (recomendado)**:
    ```bash
    python -m venv .venv
    # En Windows:
    .venv\Scripts\activate
    # En Linux/Mac:
    source .venv/bin/activate
    ```

3.  **Instalar dependencias**:
    ```bash
    pip install -r requirements.txt
    ```

## ▶️ Ejecución

Para iniciar la aplicación, ejecuta el archivo principal:

```bash
python main.py
```

## 📂 Estructura del Proyecto

*   `main.py`: Punto de entrada de la aplicación.
*   `database.py`: Manejo de la base de datos SQLite.
*   `sales_view.py`: Interfaz de ventas.
*   `inventory_view.py`: Gestión de inventario.
*   `reports_view.py`: Visualización de reportes.
*   `movements_view.py`: Ingresos y salidas de caja.
*   `login_view.py`: Sistema de autenticación.
*   `whatsapp_manager.py`: Lógica para integración con WhatsApp.
*   `xml_generator.py`: Generación de XML para facturación electrónica.

---
