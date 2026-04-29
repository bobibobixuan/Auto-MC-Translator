# Auto MC Translator

[中文](README.md) | [English](README.en-US.md) | [日本語](README.ja-JP.md) | [한국어](README.ko-KR.md) | [Español](README.es-ES.md)

Auto MC Translator es una herramienta local de traducción asistida por IA para mods y modpacks de Minecraft. Escanea los archivos de idioma dentro de JAR, ZIP, packs de recursos o carpetas completas como `mods`, traduce el contenido de `assets/<namespace>/lang/` al idioma objetivo y genera un resource pack de reemplazo listo para usar dentro del juego.

## Objetivo del proyecto

Esta herramienta no está pensada para modificar los mods originales, sino para ofrecer un entorno seguro y repetible de traducción local.

- Traducir un solo mod para pruebas rápidas
- Traducir una carpeta completa en lote
- Mostrar registros en tiempo real de las llamadas al modelo
- Mostrar un resumen por mod en los registros
- Generar un nuevo resource pack sin tocar los archivos originales
- Soportar APIs compatibles con OpenAI y endpoints locales compatibles

## Funciones principales

- Dos flujos de trabajo: traducción de un solo mod y traducción de carpeta completa
- Escaneo de `.jar`, `.zip`, `mods`, `resourcepacks`, la raíz del modpack y carpetas descomprimidas
- Compatibilidad con archivos de idioma JSON modernos y archivos `.lang` antiguos
- Registros en tiempo real de escaneo, lotes, reintentos, escritura y resumen final
- Resumen por mod indicando qué mods se tradujeron y cuántas entradas se generaron
- División automática de lotes cuando el modelo omite claves o falla una solicitud
- Salida generada junto a la ruta de entrada
- Presets integrados para proveedores OpenAI compatibles comunes
- Flujo local para Windows y empaquetado en EXE

## Casos de uso recomendados

- Quieres probar primero un solo mod
- Ya tienes una traducción parcial y solo quieres completar lo que falta
- Quieres traducir toda la carpeta `mods`
- Necesitas un EXE portable para otros usuarios

## Entradas compatibles

- Un único archivo `.jar` o `.zip`
- Carpeta `mods` completa
- Carpeta `resourcepacks` completa
- Carpeta raíz del modpack
- Carpeta de assets descomprimida

## Inicio rápido

### 1. Requisitos

- Windows es el entorno principal objetivo
- Se recomienda Python 3.11 o superior
- Necesitas una API Key de un modelo compatible con OpenAI o un endpoint local compatible como Ollama / LM Studio

### 2. Configuración de la API

Copia `.env.example` a `.env` y completa la configuración:

```env
OPENAI_PROVIDER=deepseek
OPENAI_API_KEY=tu-clave
OPENAI_MODEL=deepseek-v4-flash
OPENAI_BASE_URL=
```

En la mayoría de los casos no necesitas definir `OPENAI_BASE_URL`. Solo cámbialo si usas un proveedor personalizado, una región distinta o un servicio local con un puerto diferente.

### 3. Ejecución local

Haz doble clic en `launch.bat`.

El script:

1. Crea `.venv`
2. Instala dependencias
3. Inicia la interfaz web local

### 4. Uso de la interfaz web

#### Modo de traducción

- Traducción de un solo mod: para un archivo `.jar` o `.zip`
- Traducción de carpeta completa: para `mods`, `resourcepacks` o la raíz del modpack

#### Estrategia de traducción

- Traducir completamente todo el paquete de idioma
- Rellenar solo entradas faltantes

#### Información visible durante la ejecución

- Ruta de entrada y vista previa de salida
- Número de assets de idioma detectados
- Progreso por lote
- Mod que se está procesando en ese momento
- Conteo acumulado traducido por mod
- Resumen final por mod al terminar

## Comportamiento de salida

La herramienta no modifica los mods originales. En su lugar, genera el resultado junto a la ruta seleccionada.

Ejemplo:

```text
C:\Minecraft\mods\farmers-delight-ai-translation-20260429-223239
C:\Minecraft\mods\farmers-delight-ai-translation-20260429-223239.zip
```

Puedes colocar la carpeta o el ZIP generado dentro del directorio de resource packs de Minecraft.

## Formato de los registros

Ejemplo de resumen por mod:

```text
Mod total | FarmersDelight-1.20.1-1.2.8.jar | translated=289 | queued=289 | assets=1
Mod translation summary:
- FarmersDelight-1.20.1-1.2.8.jar | translated=289 | queued=289 | source=289 | existing_target=0 | assets=1
```

Cuando traduzcas una carpeta completa, aparecerá un resumen separado para cada mod.

## Presets integrados de proveedores

- DeepSeek
- OpenAI
- OpenRouter
- Groq
- DashScope
- Ollama
- LM Studio
- Custom

## Compilar EXE para Windows

Usa `build_exe.bat`.

Este script:

1. Crea o reutiliza `.venv`
2. Instala dependencias y `pyinstaller`
3. Genera un ejecutable de un solo archivo

Ruta de salida:

```text
dist/MinecraftAITranslator.exe
```

## Estructura del proyecto

```text
mc_ai_translator/
  llm_client.py
  pipeline.py
  providers.py
  scanner.py
  ui.py
app.py
launch.bat
build_exe.bat
```

## Problemas frecuentes

### ¿Por qué no modifica el mod original?

Porque editar directamente un JAR es arriesgado y complica las actualizaciones. El método de sobrescritura mediante resource pack es más seguro.

### ¿Por qué hay reintentos?

Porque algunos modelos omiten claves, devuelven JSON incompleto o fallan con lotes grandes. La herramienta ahora divide y reintenta automáticamente en lotes más pequeños.

## Notas de seguridad

- No subas tu `.env` real
- No subas claves de prueba ni notas locales
- Revisa `git status` antes de hacer push

## Hoja de ruta

- Memoria terminológica
- Escaneo de KubeJS / FTB Quests / Patchouli
- Caché de traducción
- Reanudación de tareas

## Licencia

Consulta el archivo `LICENSE` del repositorio.