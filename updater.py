import os
import sys
import json
import requests
import zipfile
import shutil
import time
import subprocess
import tkinter as tk
from tkinter import messagebox, ttk

# --- CONFIGURACIÓN ---
# URL "Raw" de tu archivo version.json en GitHub
# IMPORTANTE: Cambia 'EddieTacas' por tu usuario si es diferente y asegurar que la rama es 'main'
GITHUB_VERSION_URL = "https://raw.githubusercontent.com/EddieTacas/Proyecto-Tkinter-Punto-de-Venta/main/version.json"

# Archivos y carpetas que NO deben ser reemplazados
# database.db: Tu base de datos local
# auth_baileys: La sesión de WhatsApp
# pos_config.json: Configuración local de la caja (opcional, agrégalo si quieres conservarlo)
FILES_TO_PRESERVE = ["database.db", "pos_config.json"]
DIRS_TO_PRESERVE = ["auth_baileys"]

# Nombre del ejecutable principal de tu sistema para reiniciarlo
MAIN_EXECUTABLE_NAME = "SistemaVentas.exe" 

class UpdaterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Actualizador del Sistema")
        self.root.geometry("400x200")
        self.root.resizable(False, False)

        # Centrar ventana
        self.center_window()

        # Estilo visual básico
        style = ttk.Style()
        style.theme_use('clam')

        # Etiquetas
        self.lbl_status = ttk.Label(root, text="Buscando actualizaciones...", font=("Segoe UI", 10))
        self.lbl_status.pack(pady=20)

        # Barra de progreso
        self.progress = ttk.Progressbar(root, orient="horizontal", length=300, mode="determinate")
        self.progress.pack(pady=10)

        # Botón (deshabilitado al inicio)
        self.btn_action = ttk.Button(root, text="Cancelar", command=self.close_app)
        self.btn_action.pack(pady=10)

        # Iniciar proceso automáticamente
        self.root.after(1000, self.check_for_updates)

    def center_window(self):
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry('{}x{}+{}+{}'.format(width, height, x, y))

    def log(self, message):
        self.lbl_status.config(text=message)
        self.root.update()

    def check_for_updates(self):
        try:
            # 1. Leer versión local
            local_version = "0.0.0"
            if os.path.exists("version.json"):
                with open("version.json", "r") as f:
                    local_data = json.load(f)
                    local_version = local_data.get("version", "0.0.0")
            
            self.log(f"Versión actual: {local_version}. Consultando GitHub...")

            # 2. Consultar versión remota
            response = requests.get(GITHUB_VERSION_URL)
            response.raise_for_status()
            remote_data = response.json()
            remote_version = remote_data.get("version")
            download_url = remote_data.get("download_url")

            if not remote_version or not download_url:
                raise ValueError("El archivo version.json remoto no tiene el formato correcto.")

            # 3. Comparar versiones
            if self.is_newer(remote_version, local_version):
                if messagebox.askyesno("Actualización Disponible", f"Nueva versión encontrada: {remote_version}\n¿Deseas descargarla e instalarla ahora?"):
                    self.start_update(download_url)
                else:
                    self.lbl_status.config(text="Actualización cancelada por el usuario.")
                    self.btn_action.config(text="Salir", command=self.close_app)
            else:
                messagebox.showinfo("Sistema Actualizado", "Ya tienes la última versión instalada.")
                self.close_app()

        except Exception as e:
            messagebox.showerror("Error", f"Error al buscar actualizaciones:\n{e}")
            self.close_app()

    def is_newer(self, remote, local):
        # Comparación simple de cadenas o semver básica
        # Para algo más robusto usar pkg_resources.parse_version
        v_remote = [int(x) for x in remote.split('.')]
        v_local = [int(x) for x in local.split('.')]
        return v_remote > v_local

    def start_update(self, url):
        self.log("Descargando actualización...")
        self.progress["value"] = 0
        
        try:
            # Descargar archivo ZIP
            local_filename = "update.zip"
            with requests.get(url, stream=True) as r:
                r.raise_for_status()
                total_length = int(r.headers.get('content-length', 0))
                dl = 0
                with open(local_filename, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192): 
                        if chunk: 
                            dl += len(chunk)
                            f.write(chunk)
                            # Actualizar barra de progreso
                            if total_length > 0:
                                percent = int((dl / total_length) * 100)
                                self.progress["value"] = percent
                                self.root.update()

            self.log("Actualización descargada. Instalando...")
            self.install_update(local_filename)

        except Exception as e:
            messagebox.showerror("Error de Actualización", f"Ocurrió un error durante la descarga:\n{e}")
            if os.path.exists("update.zip"):
                os.remove("update.zip")
            self.btn_action.config(text="Salir")

    def install_update(self, zip_path):
        # Crear carpeta temporal para extracción
        extract_folder = "temp_update"
        if os.path.exists(extract_folder):
            shutil.rmtree(extract_folder)
        os.makedirs(extract_folder)

        try:
            # 1. Extraer ZIP
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_folder)
            
            # Nota: A veces los ZIPs tienen una carpeta raíz dentro.
            # Verificamos si el contenido está dentro de una subcarpeta
            content_dir = extract_folder
            items = os.listdir(extract_folder)
            if len(items) == 1 and os.path.isdir(os.path.join(extract_folder, items[0])):
                content_dir = os.path.join(extract_folder, items[0])

            # 2. Realizar la actualización (respetando exclusiones)
            # Como el script se está ejecutando, esperaríamos que sea un ejecutable aparte
            # o que el usuario lo corra aparte. 
            
            # Mover archivos nuevos al directorio actual
            for item in os.listdir(content_dir):
                source_path = os.path.join(content_dir, item)
                dest_path = os.path.join(os.getcwd(), item)

                # Verificar si debe ser ignorado
                if item in FILES_TO_PRESERVE:
                    print(f"Conservando archivo existente: {item}")
                    continue
                if item in DIRS_TO_PRESERVE:
                    print(f"Conservando directorio existente: {item}")
                    continue

                # Si es un directorio, usar copytree con reemplazo
                if os.path.isdir(source_path):
                    if os.path.exists(dest_path):
                        shutil.rmtree(dest_path)
                    shutil.copytree(source_path, dest_path)
                else:
                    # Si es un archivo, reemplazar
                    if os.path.exists(dest_path):
                        os.remove(dest_path)
                    shutil.copy2(source_path, dest_path)

            self.log("¡Actualización completada con éxito!")
            messagebox.showinfo("Éxito", "El sistema se ha actualizado correctamente.\nLa aplicación se reiniciará.")

            # Limpieza
            if os.path.exists(zip_path):
                os.remove(zip_path)
            shutil.rmtree(extract_folder)

            # Intentar abrir la app principal
            if os.path.exists(MAIN_EXECUTABLE_NAME):
                subprocess.Popen([MAIN_EXECUTABLE_NAME])
            
            self.close_app()

        except Exception as e:
             messagebox.showerror("Error de Instalación", f"No se pudo instalar la actualización:\n{e}\n\nAsegúrate de que la aplicación principal esté CERRADA.")
             self.btn_action.config(text="Salir")

    def close_app(self):
        self.root.destroy()
        sys.exit()

if __name__ == "__main__":
    root = tk.Tk()
    app = UpdaterApp(root)
    root.mainloop()
