#!/bin/bash
# Script para extraer la URL de ngrok del notebook de Colab
# Usage: ./update_ngrok_url.sh

echo "🔍 Buscando URL de ngrok en el output de Colab..."
echo ""
echo "Por favor, copia y pega la URL completa de ngrok que aparece en Colab:"
echo "(Ejemplo: https://abcd1234.ngrok.io)"
echo ""
read -p "URL: " NGROK_URL

if [ -z "$NGROK_URL" ]; then
    echo "❌ URL no proporcionada"
    exit 1
fi

# Detectar archivo .env
ENV_FILE=".env"
if [ ! -f "$ENV_FILE" ]; then
    ENV_FILE=".env.example"
fi

if [ ! -f "$ENV_FILE" ]; then
    echo "❌ No se encontró archivo .env"
    exit 1
fi

# Actualizar OLLAMA_BASE_URL
if grep -q "OLLAMA_BASE_URL" "$ENV_FILE"; then
    sed -i "s|OLLAMA_BASE_URL=.*|OLLAMA_BASE_URL=$NGROK_URL|" "$ENV_FILE"
else
    echo "OLLAMA_BASE_URL=$NGROK_URL" >> "$ENV_FILE"
fi

echo "✅ Actualizado $ENV_FILE con la URL: $NGROK_URL"
echo ""
echo "Ahora podés ejecutar: py -m streamlit run scripts/ui_app.py"