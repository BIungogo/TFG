# Papelera Inteligente Automatizada basada en Visión por Computador y Edge AI (TFG)

Repositorio oficial del Trabajo de Fin de Grado (TFG) centrado en el diseño, desarrollo e implementación de un sistema autónomo de clasificación de residuos mediante **Visión por Computador** y **Aprendizaje Profundo (*Deep Learning*)** ejecutado directamente en sistemas embebidos de bajo coste y consumo (**Edge AI**).

---

## 1. Motivación y Problema a Resolver

En espacios públicos con un elevado tránsito de personas (como centros comerciales, aeropuertos, estaciones o parques), la separación selectiva de residuos falla principalmente debido al error humano, la falta de tiempo o el desconocimiento de las normativas locales de reciclaje. En estos entornos urbanos, **la efectividad de la separación manual se sitúa en apenas un 20%**, lo que contamina las fracciones reciclables y dificulta enormemente su posterior tratamiento.

## 2. Propuesta del Proyecto

El objetivo de este proyecto es el diseño y desarrollo de una **papelera inteligente automatizada** capaz de identificar y clasificar de forma autónoma **cinco tipos de residuos**:

1. **Plástico / Aluminio** (Envases ligeros)
2. **Orgánico**
3. **Papel / Cartón**
4. **Vidrio**
5. **Resto** (Fracción no reciclable)

---

## 3. Arquitectura Técnica

### Inteligencia Artificial y Visión por Computador
El sistema emplea técnicas de visión artificial y aprendizaje profundo (*Deep Learning*) mediante el entrenamiento de **redes neuronales convolucionales (CNN) ligeras**, diseñadas para extraer características visuales de los residuos capturados y clasificarlos con alta precisión.

### Particularidad Técnica: Edge AI en Microcontrolador
En lugar de depender de una conexión permanente para enviar las imágenes a un servidor externo en la nube, el modelo neuronal se **optimiza y comprime** (aplicando técnicas como la **cuantización**) para ejecutarse de manera 100% local, rápida y eficiente en un microcontrolador de bajo coste y reducido consumo energético:
- **Microcontrolador:** **ESP32-S3** (Módulo **Freenove ESP32-S3 WROOM** con **8 MB de memoria Flash** y **8 MB de PSRAM**).
- **Sensor de imagen:** Cámara **OmniVision OV2640**.

### Soporte Físico y Prototipo Funcional
El proyecto abarca también el desarrollo mecánico y electrónico de un prototipo funcional autónomo:
- **Diseño CAD:** Modelado tridimensional íntegro en **Onshape**.
- **Manufactura Aditiva:** Fabricación mediante impresión 3D con tecnología **FDM en material PLA**, laminado y parametrizado en **OrcaSlicer**.
- **Integración Electrónica:** Estructura diseñada a medida que aloja el módulo ESP32-S3 y la cámara OV2640, un **pulsador externo** para activar la captura de imágenes, almacenamiento en tarjeta microSD y un **módulo de batería de litio 18650** que dota al sistema de autonomía energética.

---

## 4. Estructura del Repositorio

Actualmente, el repositorio contiene los módulos correspondientes a la fase de adquisición de datos, la herramienta gráfica de etiquetado y el conjunto de imágenes tanto en bruto como clasificadas por categorías:

```text
├── Codigos/
│   ├── Data_adquisition/
│   │   └── Data_adquisition.ino       # Firmware de adquisición de imágenes (versión base)
│   ├── Data_adquisition_2.0/
│   │   └── Data_adquisition_2.0.ino   # Firmware de adquisición con ajustes de configuración en Arduino IDE
│   └── etiquetador.py                 # Herramienta gráfica interactiva (Tkinter) para clasificar el dataset
├── dataset/
│   └── residuos_*.jpg                 # Dataset en bruto de imágenes capturadas con la cámara OV2640
├── dataset_clasificado/
│   ├── carton_papel/                  # Imágenes etiquetadas como Cartón / Papel (193 imágenes)
│   ├── organico/                      # Imágenes etiquetadas como Orgánico (150 imágenes)
│   ├── plastico_metal/                # Imágenes etiquetadas como Plástico / Metal (295 imágenes)
│   ├── vidrio/                        # Imágenes etiquetadas como Vidrio (122 imágenes)
│   ├── resto/                         # Imágenes etiquetadas como Resto (149 imágenes)
│   ├── rechazadas/                    # Imágenes descartadas durante el filtrado (31 imágenes)
│   └── registro_etiquetas.csv         # Registro histórico de clasificación con marca temporal
├── ejecutar_etiquetador.bat           # Script de acceso directo para lanzar el etiquetador en Windows
├── .gitignore
└── README.md
```

### Funcionamiento del Firmware de Adquisición (`Data_adquisition`)
El código implementado para el ESP32-S3 realiza las siguientes tareas:
- **Lectura con antirrebote (*debounce*):** Detecta la pulsación del botón externo conectado al `GPIO 1`.
- **Estabilización óptica del sensor (AWB/AEC):** Antes de tomar la fotografía definitiva, descarta los primeros 4 *frames* del búfer para permitir que el sensor OV2640 estabilice el balance de blancos y la exposición automática.
- **Captura en alta resolución aprovechando la PSRAM:** Si detecta la memoria PSRAM activa, captura en resolución `UXGA` con alta calidad JPEG.
- **Almacenamiento en microSD (`SD_MMC`) y persistencia en Flash (`NVS`):** Guarda cada imagen bajo el formato `/dataset/residuos_<N>.jpg` en la tarjeta microSD y almacena el contador `N` en la memoria no volátil (NVS) del ESP32-S3 mediante la librería `Preferences`, evitando sobrescribir imágenes tras reinicios o apagados.

### Herramienta Interactiva de Etiquetado (`etiquetador.py`)
Aplicación de escritorio desarrollada en Python (`Tkinter` + `Pillow`) para agilizar la clasificación manual de las capturas:
- Permite clasificar cada imagen mediante botones en pantalla o atajos de teclado (`1`–`5` para las 5 clases de residuos y `R` para rechazar capturas defectuosas).
- Filtra automáticamente las imágenes que ya han sido etiquetadas previamente para procesar únicamente las pendientes.
- Organiza las imágenes en subcarpetas dentro de `dataset_clasificado/` (estructura compatible con *DataLoaders* de PyTorch y TensorFlow/Keras) y mantiene un registro detallado en `registro_etiquetas.csv` con soporte para deshacer acciones (`Ctrl+Z`).

---

## 5. Configuración en Arduino IDE

Para compilar y cargar correctamente el firmware en el módulo **Freenove ESP32-S3 WROOM** desde el entorno **Arduino IDE**, es fundamental aplicar la siguiente configuración en el menú `Herramientas` (*Tools*):

| Parámetro en Arduino IDE | Valor Configurado |
| :--- | :--- |
| **Board** | `ESP32S3 Dev Module` |
| **USB CDC On Boot** | `Disabled` |
| **CPU Frequency** | `240MHz (WiFi)` |
| **Core Debug Level** | `None` |
| **USB DFU On Boot** | `Disabled` |
| **Erase All Flash Before Sketch Upload** | `Disabled` |
| **Events Run On** | `Core 1` |
| **Flash Mode** | `QIO 80MHz` |
| **Flash Size** | `4MB (32Mb)` |
| **JTAG Adapter** | `Disabled` |
| **Arduino Runs On** | `Core 1` |
| **USB Firmware MSC On Boot** | `Disabled` |
| **Partition Scheme** | `Default 4MB with spiffs (1.2MB APP/1.5MB SPIFFS)` |
| **PSRAM** | `OPI PSRAM` |
| **Upload Mode** | `UART0 / Hardware CDC` |
| **Upload Speed** | `921600` |
| **USB Mode** | `Hardware CDC and JTAG` |
| **Zigbee Mode** | `Disabled` |

### Asignación de Pines (Freenove ESP32-S3 WROOM CAM)
- **Pulsador de captura:** `GPIO 1` (configurado con resistencia interna `INPUT_PULLUP`).
- **Interfaz microSD (`SD_MMC`):** `CMD = GPIO 38`, `CLK = GPIO 39`, `D0 = GPIO 40`.
- **Cámara OV2640:** Pines predefinidos del bus de cámara Freenove (`XCLK = 15`, `SIOD = 4`, `SIOC = 5`, `VSYNC = 6`, `HREF = 7`, `PCLK = 13`, `Y2..Y9 = 11, 9, 8, 10, 12, 18, 17, 16`).
