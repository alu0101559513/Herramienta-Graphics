# GRAPHICS
[![CI Tests](https://github.com/alu0101559513/Herramienta-Graphics/actions/workflows/build.yml/badge.svg)](https://github.com/alu0101559513/Herramienta-Graphics/actions/workflows/build.yml)

[![Deploy docs](https://github.com/alu0101559513/Herramienta-Graphics/actions/workflows/doc.yml/badge.svg)](https://github.com/alu0101559513/Herramienta-Graphics/actions/workflows/doc.yml)


Plataforma para analizar los resultados de tus experimentos, generar gráficas, consultar reportes y trabajar con resultados de forma sencilla.

# Características principales

## Creación de análisis
- Crea análisis fácilmente subiendo tus ficheros CSV.

## Generación de gráficas
- Boxplots
- Violin plots
- Histogramas
- Critical Distance plots
- Evolution plots

## Generación de reportes
- Reportes SAES

## Generación de notebooks
- Genera un Jupyter Notebook con todas las gráficas y reportes de SAES

# Manual de usuario

En el siguiente enlace podrás encontrar la documentación completa de uso de la aplicación:
[Manual de usuario] (<https://alu0101559513.github.io/Herramienta-Graphics/>)

# Tecnologías utilizadas

## Frontend
- React
- TypeScript
- Redux Toolkit
- Vite

## Backend
- FastAPI
- Python
- Beanie ODM
- MongoDB

## Infraestructura
- Docker
- Docker Compose
- Nginx

# Requisitos previos

Antes de ejecutar la aplicación necesitas tener instalado:

- Docker
- Docker Compose
- Git

# Instalación

## 1. Clonar el repositorio

```bash
git clone git@github.com:alu0101559513/Graphics.git
cd Graphics
```

---

## 2. Configurar variables de entorno

La aplicación requiere configurar dos archivos `.env`.


### Backend

Crear el archivo:

```bash
backend/.env
```

Ejemplo:

```env
MONGO_URL=mongodb://mongo:27017
DB_NAME=app_db

FRONTEND_URL=http://localhost:3000

JWT_SECRET=your_secret_key
JWT_ALGORITHM=HS256
JWT_EXPIRE_HOURS=24
```

### Frontend

Crear el archivo:

```bash
frontend/.env
```

Ejemplo:

```env
VITE_API_URL=http://localhost:8000
```

## 3. Levantar la aplicación con Docker

Desde la raíz del proyecto ejecutar:

```bash
docker compose up --build
```

# Acceso a la aplicación

## Frontend

```txt
http://localhost:3000
```

## Backend API

```txt
http://localhost:8000
```

# Documentación técnica

La documentación técnica de la API se genera automáticamente mediante FastAPI y se encuentra disponible en Swagger/OpenAPI.

```txt
http://localhost:8000/docs
```

## Documentación ReDoc

```txt
http://localhost:8000/redoc
```
