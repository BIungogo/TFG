#include "esp_camera.h"
#include "FS.h"
#include "SD_MMC.h"
#include <Preferences.h> // Acceso a la memoria Flash (NVS)

// ==========================================
// PINES EXACTOS FREENOVE ESP32-S3 WROOM CAM
// ==========================================
#define PWDN_GPIO_NUM -1
#define RESET_GPIO_NUM -1
#define XCLK_GPIO_NUM 15
#define SIOD_GPIO_NUM 4
#define SIOC_GPIO_NUM 5
#define Y9_GPIO_NUM 16
#define Y8_GPIO_NUM 17
#define Y7_GPIO_NUM 18
#define Y6_GPIO_NUM 12
#define Y5_GPIO_NUM 10
#define Y4_GPIO_NUM 8
#define Y3_GPIO_NUM 9
#define Y2_GPIO_NUM 11
#define VSYNC_GPIO_NUM 6
#define HREF_GPIO_NUM 7
#define PCLK_GPIO_NUM 13

#define BUTTON_PIN 1 // Pin asignado al pulsador externo

Preferences preferences;
unsigned int pictureCount = 0;

void setup() {
  Serial.begin(115200);
  pinMode(BUTTON_PIN, INPUT_PULLUP);

  // --- INICIALIZACIÓN NVS (Contador persistente) ---
  preferences.begin("dataset", false); 
  pictureCount = preferences.getUInt("counter", 0);
  Serial.printf("Memoria NVS inicializada. Próxima foto: %d\n", pictureCount);

  // --- INICIALIZACIÓN SDMMC (Configuración Freenove) ---
  SD_MMC.setPins(39, 38, 40); 
  if(!SD_MMC.begin("/sdcard", true)){ 
    Serial.println("Error crítico: No se pudo montar la tarjeta SD_MMC.");
    return;
  }
  if(!SD_MMC.exists("/dataset")) {
    SD_MMC.mkdir("/dataset");
  }

  // --- CONFIGURACIÓN DE LA CÁMARA ---
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sccb_sda = SIOD_GPIO_NUM;
  config.pin_sccb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;
  
  if (psramFound()) {
    config.frame_size = FRAMESIZE_UXGA; // Resolución óptima
    config.jpeg_quality = 10;
    config.fb_count = 2;
  } else {
    config.frame_size = FRAMESIZE_SVGA;
    config.jpeg_quality = 12;
    config.fb_count = 1;
  }

  if (esp_camera_init(&config) != ESP_OK) {
    Serial.println("Error al inicializar la cámara.");
    return;
  }

  sensor_t *s = esp_camera_sensor_get();
  s->set_vflip(s, 1); // Voltear la imagen si es necesario

  Serial.println("Sistema embebido listo. Presiona el botón para clasificar el residuo.");
}

void loop() {
  if (digitalRead(BUTTON_PIN) == LOW) {
    delay(50); // Mitigación de rebotes
    if (digitalRead(BUTTON_PIN) == LOW) {
      capturarImagen();
      while(digitalRead(BUTTON_PIN) == LOW); 
      delay(200);
    }
  }
}

void capturarImagen() {
  // 1. ESTABILIZACIÓN DEL SENSOR (AWB/AEC): Descartamos 4 frames iniciales
  for(int i = 0; i < 4; i++){
    camera_fb_t * dummy_fb = esp_camera_fb_get();
    if (dummy_fb) {
        esp_camera_fb_return(dummy_fb); 
    }
  }

  // 2. CAPTURA DEL FRAME DEFINITIVO (Color estabilizado)
  camera_fb_t * fb = esp_camera_fb_get();
  if (!fb) {
    Serial.println("Fallo del sensor en la captura definitiva.");
    return;
  }

  // 3. GUARDADO Y PERSISTENCIA
  String path = "/dataset/residuos_" + String(pictureCount) + ".jpg";
  File file = SD_MMC.open(path.c_str(), FILE_WRITE);
  
  if (!file) {
    Serial.println("Error de escritura en SD_MMC.");
  } else {
    file.write(fb->buf, fb->len);
    Serial.printf("Guardado exitoso: %s\n", path.c_str());
    
    // Incremento y salvado en memoria Flash
    pictureCount++;
    preferences.putUInt("counter", pictureCount);
  }
  
  file.close();
  esp_camera_fb_return(fb); 
}