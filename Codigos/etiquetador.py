#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Herramienta interactiva de etiquetado de imágenes para clasificación de residuos.
Permite clasificar imágenes mediante clics con el ratón (o atajos de teclado)
y organiza el conjunto de datos en subcarpetas compatibles con PyTorch / TensorFlow.
"""

import os
import sys
import re
import csv
import shutil
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk

# Clases disponibles para la clasificación
# Formato: (identificador_carpeta, etiqueta_visible, color_boton, tecla_atajo)
CLASES = [
    ("organico", "1. Orgánico", "#2e7d32", "1"),
    ("plastico_metal", "2. Plástico / Metal", "#f57f17", "2"),
    ("carton_papel", "3. Cartón / Papel", "#1565c0", "3"),
    ("vidrio", "4. Vidrio", "#00897b", "4"),
    ("resto", "5. Resto", "#546e7a", "5"),
    ("rechazadas", "R. Rechazar imagen", "#c62828", "r"),
]

EXTENSIONES_VALIDAS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def natural_sort_key(s):
    """Clave para ordenar cadenas con números de forma natural (residuos_1, residuos_2... residuos_10)."""
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s)]


class EtiquetadorApp:
    def __init__(self, root, dataset_dir, output_dir):
        self.root = root
        self.dataset_dir = os.path.abspath(dataset_dir)
        self.output_dir = os.path.abspath(output_dir)
        self.csv_path = os.path.join(self.output_dir, "registro_etiquetas.csv")

        self.root.title("Etiquetador Interactivo de Residuos")
        self.root.geometry("1024x768")
        self.root.minsize(800, 600)

        # Crear estructura de carpetas de destino
        os.makedirs(self.output_dir, exist_ok=True)
        for class_id, _, _, _ in CLASES:
            os.makedirs(os.path.join(self.output_dir, class_id), exist_ok=True)

        # Inicializar archivo CSV si no existe
        if not os.path.exists(self.csv_path):
            with open(self.csv_path, mode="w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["nombre_archivo", "clase", "fecha_hora", "ruta_destino"])

        # Pila de historial para la función 'Deshacer'
        self.historial_acciones = []

        # Cargar imágenes pendientes
        self.imagenes_pendientes = self.obtener_imagenes_pendientes()

        # Conteo inicial de imágenes ya etiquetadas en output_dir
        self.conteos = self.obtener_conteos_actuales()
        self.total_inicial = len(self.imagenes_pendientes) + sum(self.conteos.values())

        # Variables de estado
        self.indice_actual = 0
        self.imagen_pil_actual = None
        self.foto_tk_actual = None

        # Construir interfaz
        self.crear_interfaz()
        self.configurar_atajos()

        # Manejador de cierre de ventana
        self.root.protocol("WM_DELETE_WINDOW", self.al_cerrar)

        # Cargar primera imagen
        self.cargar_siguiente_imagen()

    def obtener_imagenes_pendientes(self):
        """Busca todas las imágenes en la carpeta dataset."""
        if not os.path.exists(self.dataset_dir):
            return []
        archivos = [
            f for f in os.listdir(self.dataset_dir)
            if os.path.isfile(os.path.join(self.dataset_dir, f)) and
            os.path.splitext(f)[1].lower() in EXTENSIONES_VALIDAS
        ]
        archivos.sort(key=natural_sort_key)
        return archivos

    def obtener_conteos_actuales(self):
        """Cuenta las imágenes que ya están en cada subcarpeta de destino."""
        conteos = {class_id: 0 for class_id, _, _, _ in CLASES}
        for class_id in conteos:
            carpeta = os.path.join(self.output_dir, class_id)
            if os.path.exists(carpeta):
                conteos[class_id] = len([
                    f for f in os.listdir(carpeta)
                    if os.path.isfile(os.path.join(carpeta, f)) and
                    os.path.splitext(f)[1].lower() in EXTENSIONES_VALIDAS
                ])
        return conteos

    def crear_interfaz(self):
        # Frame superior: Información y progreso
        self.frame_top = tk.Frame(self.root, bg="#eceff1", padx=15, pady=10)
        self.frame_top.pack(side=tk.TOP, fill=tk.X)

        self.lbl_info = tk.Label(
            self.frame_top,
            text="Iniciando...",
            font=("Segoe UI", 12, "bold"),
            bg="#eceff1",
            fg="#263238"
        )
        self.lbl_info.pack(side=tk.LEFT)

        self.lbl_detalles = tk.Label(
            self.frame_top,
            text="",
            font=("Segoe UI", 10),
            bg="#eceff1",
            fg="#546e7a"
        )
        self.lbl_detalles.pack(side=tk.RIGHT)

        # Barra de progreso visual
        self.progreso = ttk.Progressbar(self.root, orient=tk.HORIZONTAL, mode='determinate')
        self.progreso.pack(side=tk.TOP, fill=tk.X, padx=15, pady=(0, 5))

        # Barra de estadísticas en tiempo real
        self.frame_stats = tk.Frame(self.root, bg="#f5f7f8", padx=10, pady=4)
        self.frame_stats.pack(side=tk.TOP, fill=tk.X)
        self.lbl_stats = tk.Label(
            self.frame_stats,
            text="",
            font=("Segoe UI", 9),
            bg="#f5f7f8",
            fg="#37474f"
        )
        self.lbl_stats.pack(anchor=tk.CENTER)

        # Frame central: Visor de imagen
        self.frame_img = tk.Frame(self.root, bg="#1e1e1e")
        self.frame_img.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=15, pady=5)

        self.lbl_imagen = tk.Label(self.frame_img, bg="#1e1e1e", text="Cargando imagen...")
        self.lbl_imagen.pack(fill=tk.BOTH, expand=True)
        self.lbl_imagen.bind("<Configure>", self.al_redimensionar_ventana)

        # Frame inferior: Botones de clasificación y utilidades
        self.frame_bottom = tk.Frame(self.root, bg="#eceff1", padx=15, pady=10)
        self.frame_bottom.pack(side=tk.BOTTOM, fill=tk.X)

        # Botones de clases (con ratón)
        self.frame_botones_clases = tk.Frame(self.frame_bottom, bg="#eceff1")
        self.frame_botones_clases.pack(side=tk.TOP, fill=tk.X, pady=(0, 10))

        self.botones_clases = {}
        for class_id, label, color, _ in CLASES:
            btn = tk.Button(
                self.frame_botones_clases,
                text=label,
                bg=color,
                fg="white",
                font=("Segoe UI", 11, "bold"),
                activebackground="#37474f",
                activeforeground="white",
                relief=tk.RAISED,
                bd=2,
                padx=10,
                pady=12,
                cursor="hand2",
                command=lambda cid=class_id: self.etiquetar(cid)
            )
            btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)
            self.botones_clases[class_id] = btn

        # Botones de utilidades (Deshacer, Ver resumen, Finalizar)
        self.frame_utilidades = tk.Frame(self.frame_bottom, bg="#eceff1")
        self.frame_utilidades.pack(side=tk.BOTTOM, fill=tk.X)

        self.btn_deshacer = tk.Button(
            self.frame_utilidades,
            text="↩ Deshacer última",
            font=("Segoe UI", 10),
            bg="#cfd8dc",
            fg="#263238",
            padx=12,
            pady=6,
            cursor="hand2",
            state=tk.DISABLED,
            command=self.deshacer
        )
        self.btn_deshacer.pack(side=tk.LEFT, padx=5)

        self.btn_resumen = tk.Button(
            self.frame_utilidades,
            text="📊 Ver Recuento",
            font=("Segoe UI", 10),
            bg="#cfd8dc",
            fg="#263238",
            padx=12,
            pady=6,
            cursor="hand2",
            command=self.mostrar_resumen_modal
        )
        self.btn_resumen.pack(side=tk.LEFT, padx=5)

        self.btn_salir = tk.Button(
            self.frame_utilidades,
            text="💾 Guardar y Salir",
            font=("Segoe UI", 10, "bold"),
            bg="#90a4ae",
            fg="#263238",
            padx=12,
            pady=6,
            cursor="hand2",
            command=self.al_cerrar
        )
        self.btn_salir.pack(side=tk.RIGHT, padx=5)

    def configurar_atajos(self):
        """Permite también usar el teclado para mayor rapidez además del ratón."""
        for class_id, _, _, key in CLASES:
            self.root.bind(key.lower(), lambda e, cid=class_id: self.etiquetar(cid))
            self.root.bind(key.upper(), lambda e, cid=class_id: self.etiquetar(cid))

        # Atajos adicionales para rechazar
        self.root.bind("0", lambda e: self.etiquetar("rechazadas"))
        self.root.bind("<Delete>", lambda e: self.etiquetar("rechazadas"))

        # Atajo para deshacer
        self.root.bind("<Control-z>", lambda e: self.deshacer())
        self.root.bind("<Control-Z>", lambda e: self.deshacer())

        # Salir con Escape
        self.root.bind("<Escape>", lambda e: self.al_cerrar())

    def actualizar_estadisticas_texto(self):
        """Actualiza la barra de progreso y el texto de conteos."""
        total_etiquetadas = sum(self.conteos.values())
        total_global = total_etiquetadas + len(self.imagenes_pendientes)

        if total_global > 0:
            porcentaje = (total_etiquetadas / total_global) * 100
            self.progreso['value'] = porcentaje
        else:
            self.progreso['value'] = 100

        # Formar texto de conteos por clase
        texto_partes = []
        for class_id, label, _, _ in CLASES:
            nombre_limpio = label.split(". ", 1)[-1]
            cantidad = self.conteos.get(class_id, 0)
            texto_partes.append(f"{nombre_limpio}: {cantidad}")

        self.lbl_stats.config(text=" | ".join(texto_partes))

        # Estado del botón deshacer
        if self.historial_acciones:
            self.btn_deshacer.config(state=tk.NORMAL)
        else:
            self.btn_deshacer.config(state=tk.DISABLED)

    def al_redimensionar_ventana(self, event=None):
        """Redimensiona la imagen actual adaptándose al tamaño de la ventana."""
        if self.imagen_pil_actual is None:
            return

        ancho_disponible = max(self.frame_img.winfo_width() - 20, 200)
        alto_disponible = max(self.frame_img.winfo_height() - 20, 200)

        img_w, img_h = self.imagen_pil_actual.size
        ratio = min(ancho_disponible / img_w, alto_disponible / img_h)
        nuevo_w = max(1, int(img_w * ratio))
        nuevo_h = max(1, int(img_h * ratio))

        imagen_redimensionada = self.imagen_pil_actual.resize((nuevo_w, nuevo_h), Image.Resampling.LANCZOS)
        self.foto_tk_actual = ImageTk.PhotoImage(imagen_redimensionada)
        self.lbl_imagen.config(image=self.foto_tk_actual, text="")

    def cargar_siguiente_imagen(self):
        """Carga en pantalla la siguiente imagen disponible en la lista de pendientes."""
        self.actualizar_estadisticas_texto()

        if not self.imagenes_pendientes:
            self.mostrar_fin_etiquetado()
            return

        nombre_archivo = self.imagenes_pendientes[0]
        ruta_completa = os.path.join(self.dataset_dir, nombre_archivo)

        try:
            self.imagen_pil_actual = Image.open(ruta_completa)
            total_etiquetadas = sum(self.conteos.values())
            total_global = total_etiquetadas + len(self.imagenes_pendientes)

            self.lbl_info.config(
                text=f"Imagen: {nombre_archivo} ({total_etiquetadas + 1} de {total_global})"
            )
            self.lbl_detalles.config(
                text=f"Pendientes en cola: {len(self.imagenes_pendientes)}"
            )

            # Forzar actualización gráfica
            self.root.update_idletasks()
            self.al_redimensionar_ventana()

        except Exception as e:
            messagebox.showerror(
                "Error al abrir imagen",
                f"No se pudo cargar la imagen {nombre_archivo}:\n{e}\nSe omitirá."
            )
            self.imagenes_pendientes.pop(0)
            self.cargar_siguiente_imagen()

    def etiquetar(self, class_id):
        """Mueve la imagen actual a la carpeta correspondiente y actualiza registros."""
        if not self.imagenes_pendientes:
            return

        nombre_archivo = self.imagenes_pendientes.pop(0)
        ruta_origen = os.path.join(self.dataset_dir, nombre_archivo)
        carpeta_destino = os.path.join(self.output_dir, class_id)
        ruta_destino = os.path.join(carpeta_destino, nombre_archivo)

        try:
            # Mover archivo
            shutil.move(ruta_origen, ruta_destino)

            # Registrar en CSV
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(self.csv_path, mode="a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([nombre_archivo, class_id, timestamp, ruta_destino])

            # Actualizar conteos
            self.conteos[class_id] = self.conteos.get(class_id, 0) + 1

            # Guardar en pila de deshacer
            self.historial_acciones.append({
                "nombre_archivo": nombre_archivo,
                "class_id": class_id,
                "ruta_origen": ruta_origen,
                "ruta_destino": ruta_destino
            })

            # Pasar a la siguiente
            self.cargar_siguiente_imagen()

        except Exception as e:
            messagebox.showerror("Error al mover archivo", f"Ocurrió un error al guardar la imagen:\n{e}")
            self.imagenes_pendientes.insert(0, nombre_archivo)

    def deshacer(self):
        """Revierte la última acción realizada y devuelve la imagen a dataset/."""
        if not self.historial_acciones:
            return

        ultima = self.historial_acciones.pop()
        nombre_archivo = ultima["nombre_archivo"]
        class_id = ultima["class_id"]
        ruta_origen = ultima["ruta_origen"]
        ruta_destino = ultima["ruta_destino"]

        try:
            # Mover de vuelta a dataset
            if os.path.exists(ruta_destino):
                shutil.move(ruta_destino, ruta_origen)

            # Decrementar conteo
            if self.conteos.get(class_id, 0) > 0:
                self.conteos[class_id] -= 1

            # Volver a insertar al inicio de la lista de pendientes
            self.imagenes_pendientes.insert(0, nombre_archivo)

            # Eliminar la última línea del CSV
            self.eliminar_ultima_linea_csv(nombre_archivo)

            # Recargar imagen en pantalla
            self.cargar_siguiente_imagen()

        except Exception as e:
            messagebox.showerror("Error al deshacer", f"No se pudo revertir la última acción:\n{e}")

    def eliminar_ultima_linea_csv(self, nombre_archivo_esperado):
        """Elimina el registro de la imagen deshecha del archivo CSV."""
        if not os.path.exists(self.csv_path):
            return

        with open(self.csv_path, mode="r", newline="", encoding="utf-8") as f:
            lineas = list(csv.reader(f))

        if len(lineas) <= 1:
            return

        # Buscar de abajo a arriba la última ocurrencia de este archivo
        indice_a_borrar = None
        for i in range(len(lineas) - 1, 0, -1):
            if lineas[i] and lineas[i][0] == nombre_archivo_esperado:
                indice_a_borrar = i
                break

        if indice_a_borrar is not None:
            lineas.pop(indice_a_borrar)
            with open(self.csv_path, mode="w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerows(lineas)

    def generar_texto_resumen(self):
        """Genera un texto formateado con los resultados totales."""
        total_procesadas = sum(self.conteos.values())
        lineas = []
        lineas.append("=" * 45)
        lineas.append("          RECUENTO DE IMÁGENES")
        lineas.append("=" * 45)

        for class_id, label, _, _ in CLASES:
            nombre = label.split(". ", 1)[-1]
            cantidad = self.conteos.get(class_id, 0)
            pct = (cantidad / total_procesadas * 100) if total_procesadas > 0 else 0
            lineas.append(f"  • {nombre:<20}: {cantidad:>4}  ({pct:5.1f}%)")

        lineas.append("-" * 45)
        lineas.append(f"  Total etiquetadas   : {total_procesadas:>4}")
        lineas.append(f"  Pendientes restantes: {len(self.imagenes_pendientes):>4}")
        lineas.append("=" * 45)
        return "\n".join(lineas)

    def mostrar_resumen_modal(self):
        """Muestra una ventana modal con el resumen actual."""
        resumen = self.generar_texto_resumen()
        messagebox.showinfo("Recuento actual", resumen)

    def mostrar_fin_etiquetado(self):
        """Notificación cuando se han procesado todas las imágenes."""
        resumen = self.generar_texto_resumen()
        self.lbl_imagen.config(image="", text="¡Todas las imágenes han sido etiquetadas con éxito!")
        self.lbl_info.config(text="Proceso completado")
        self.lbl_detalles.config(text="0 pendientes")

        # Imprimir en consola
        print("\n" + resumen + "\n")

        # Mostrar cuadro de diálogo
        messagebox.showinfo("¡Etiquetado finalizado!", f"¡Has completado todas las imágenes!\n\n{resumen}")
        self.root.destroy()

    def al_cerrar(self):
        """Manejador para cuando el usuario cierra la ventana o pulsa Guardar y Salir."""
        resumen = self.generar_texto_resumen()
        print("\n" + resumen + "\n")

        if self.imagenes_pendientes:
            resp = messagebox.askyesno(
                "Salir del etiquetador",
                f"Hay {len(self.imagenes_pendientes)} imágenes pendientes.\n\n"
                "El progreso actual se ha guardado de forma segura en 'dataset_clasificado/'.\n"
                "¿Deseas cerrar la aplicación ahora?"
            )
            if resp:
                self.root.destroy()
        else:
            self.root.destroy()


def main():
    # Localizar directorios relativos a la raíz del repositorio
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(script_dir, ".."))

    # Permitir pasar rutas personalizadas por argumentos si se desea
    dataset_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.join(project_root, "dataset")
    output_dir = sys.argv[2] if len(sys.argv) > 2 else os.path.join(project_root, "dataset_clasificado")

    if not os.path.exists(dataset_dir):
        print(f"Error: No se encontró la carpeta de origen: {dataset_dir}")
        print("Asegúrate de ejecutar el programa desde la raíz del proyecto o proporcionar la ruta.")
        sys.exit(1)

    print("=" * 60)
    print(" INICIANDO ETIQUETADOR INTERACTIVO DE RESIDUOS")
    print("=" * 60)
    print(f"Carpeta de origen : {dataset_dir}")
    print(f"Carpeta de destino: {output_dir}")
    print("Controles:")
    print(" - Clic con el ratón en cada botón de clase para clasificar.")
    print(" - Atajos opcionales: 1 (Orgánico), 2 (Plástico/Metal), 3 (Cartón/Papel),")
    print("                      4 (Vidrio), 5 (Resto), R o Supr (Rechazar)")
    print(" - Deshacer: Botón 'Deshacer' o Ctrl+Z")
    print("=" * 60)

    root = tk.Tk()
    EtiquetadorApp(root, dataset_dir, output_dir)
    root.mainloop()


if __name__ == "__main__":
    main()
