# 🤖 Ollama en Google Colab - ArquiSys AI

Este notebook permite ejecutar Ollama con qwen2.5:3b en Google Colab y exponer el endpoint via ngrok para usar desde tu sistema local.

## 🚀 Uso Rápido

1. **Abrir el notebook en Google Colab**
   - Ir a: https://colab.research.google.com/
   - Subir el archivo `ollama_colab.ipynb` o clonarlo desde GitHub

2. **Configurar ngrok (opcional pero recomendado)**
   - Crear cuenta gratis en: https://dashboard.ngrok.com/
   - Copiar el token de auth
   - Pegarlo en la celda "3. Configurar token de ngrok"

3. **Ejecutar todas las celdas en orden**
   - Cell 1: Instala Ollama
   - Cell 2: Instala ngrok
   - Cell 3: Configura token (opcional)
   - Cell 4: Descarga el modelo qwen2.5:3b (~2GB)
   - Cell 5-7: Inicia servicios y obtiene URL pública

4. **Configurar tu sistema local**

   Actualizá tu archivo `.env` con la URL de ngrok:

   ```env
   USE_OLLAMA_FOR_ANALYST=true
   OLLAMA_MODEL=qwen2.5:3b
   OLLAMA_BASE_URL=https://abcd1234.ngrok.io
   ```

5. **¡Usar ArquiSys AI normalmente!**

## 📋 Requisitos

- Cuenta de Google (para Colab)
- Token de ngrok (gratis) para exponer el servicio
-Tu sistema local con la configuración actualizada

## ⚠️ Limitaciones

- **Sesión limitada**: La sesión de Colab dura max ~12 horas
- **URL dinámica**: Cada vez que reinicias el notebook, la URL cambia
- **GPU gratuita**: T4 (~15GB VRAM) - suficiente para qwen2.5:3b

## 🎯 Modelo Usado

- **qwen2.5:3b** (~2GB)
- Velocidad: ~10-15 segundos por respuesta
- Calidad: Buena para parsing de texto y contexto

## 📝 Notas

- El modelo se descarga una sola vez y queda cacheado durante la sesión
- Si la sesión se desconecta, volver a ejecutar desde la celda 4
- Para mejor experiencia, mantener la pestaña de Colab abierta

## 🔄 Si perdés la sesión

1. Volver a ejecutar las celdas 5-7
2. Obtener la nueva URL de ngrok
3. Actualizar `.env` con la nueva URL
4. Continuar usando el sistema

---

**Disclaimer**: Este método es para desarrollo/pruebas. Para producción, considerar un VPS económico (~$5-10/mes).