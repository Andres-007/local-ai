from model.database import ChatDatabase
from pymongo import MongoClient
import sys
import os
from datetime import datetime # Asegúrate de que datetime esté importado

# --- Añade tus propios proyectos aquí ---
# Asegúrate de que las URLs de las imágenes sean accesibles públicamente
# y que las projectUrl apunten a sitios reales (o déjalas como '#')
PROJECTS_DATA = [
    {
        # --- ¡NUEVO PROYECTO AÑADIDO! ---
        "title": "Sitio Web GameVerse",
        "description": "Una página de inicio moderna para un portal de noticias y reseñas de videojuegos, creada con Tailwind CSS.",
        "imageUrl": "https://placehold.co/600x400/4f46e5/ffffff?text=GameVerse+Preview", # Placeholder usando el color púrpura del sitio
        "projectUrl": "#", # Usamos '#' como placeholder. El iframe lo mostrará como una página vacía.
        "codeSnippet": """<!DOCTYPE html>
<html lang="es" class="scroll-smooth">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GameVerse - Tu Universo de Videojuegos</title>
    
    <!-- Tailwind CSS CDN -->
    <script src="https://cdn.tailwindcss.com"></script>
    
    <!-- Google Fonts: Poppins -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700;800&display=swap" rel="stylesheet">

    <!-- Configuración personalizada para Tailwind -->
    <script>
        tailwind.config = {
            theme: {
                extend: {
                    fontFamily: {
                        'sans': ['Poppins', 'sans-serif'],
                    },
                }
            }
        }
    </script>

    <style>
        /* Estilos CSS embebidos */
        /* Pequeño estilo para la barra de scroll, mejora la estética dark */
        ::-webkit-scrollbar {
            width: 8px;
        }
        ::-webkit-scrollbar-track {
            background: #111827; /* bg-gray-900 */
        }
        ::-webkit-scrollbar-thumb {
            background: #4f46e5; /* bg-indigo-600 */
            border-radius: 4px;
        }
        ::-webkit-scrollbar-thumb:hover {
            background: #6366f1; /* bg-indigo-500 */
        }
    </style>
</head>
<body class="bg-gray-900 text-white font-sans">

    <!-- =============================================== -->
    <!-- HEADER / NAVEGACIÓN -->
    <!-- =============================================== -->
    <header class="bg-gray-900/80 backdrop-blur-lg sticky top-0 z-50 shadow-lg shadow-black/20">
        <nav class="container mx-auto px-6 py-4 flex justify-between items-center">
            <!-- Logo -->
            <a href="#" class="text-3xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-purple-500 to-indigo-500">
                GameVerse
            </a>
            
            <!-- Links de Navegación (Desktop) -->
            <div class="hidden md:flex space-x-8 items-center">
                <a href="#news" class="text-gray-300 hover:text-purple-400 transition-colors duration-300">Noticias</a>
                <a href="#reviews" class="text-gray-300 hover:text-purple-400 transition-colors duration-300">Reseñas</a>
                <a href="#upcoming" class="text-gray-300 hover:text-purple-400 transition-colors duration-300">Próximamente</a>
                <a href="#contact" class="bg-purple-600 hover:bg-purple-700 text-white font-bold py-2 px-4 rounded-full transition-transform duration-300 hover:scale-105">
                    Contacto
                </a>
            </div>

            <!-- Botón de Menú (Móvil) -->
            <div class="md:hidden">
                <button id="mobile-menu-button" class="text-white focus:outline-none">
                    <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16m-7 6h7"></path>
                    </svg>
                </button>
            </div>
        </nav>

        <!-- Menú Móvil (Oculto por defecto) -->
        <div id="mobile-menu" class="hidden md:hidden bg-gray-800">
            <a href="#news" class="block py-2 px-4 text-sm text-gray-300 hover:bg-purple-600">Noticias</a>
            <a href="#reviews" class="block py-2 px-4 text-sm text-gray-300 hover:bg-purple-600">Reseñas</a>
            <a href="#upcoming" class="block py-2 px-4 text-sm text-gray-300 hover:bg-purple-600">Próximamente</a>
            <a href="#contact" class="block py-2 px-4 text-sm text-gray-300 hover:bg-purple-600">Contacto</a>
        </div>
    </header>

    <main>
        <!-- =============================================== -->
        <!-- HERO SECTION -->
        <!-- =============================================== -->
        <section id="hero" class="relative min-h-screen flex items-center justify-center text-center overflow-hidden">
            <!-- Imagen de fondo y superposición oscura -->
            <div class="absolute inset-0 z-0">
                <img src="https://placehold.co/1920x1080/111827/4F46E5?text=Epic+Game+Scene" alt="Fondo de videojuego épico" class="w-full h-full object-cover">
                <div class="absolute inset-0 bg-black/60"></div>
            </div>

            <!-- Contenido del Hero -->
            <div class="relative z-10 px-6">
                <h1 class="text-5xl md:text-7xl font-extrabold tracking-tight leading-tight mb-4">
                    <span class="text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-indigo-600">Explora el Universo</span>
                    <br> de los Videojuegos
                </h1>
                <p class="text-lg md:text-xl text-gray-300 max-w-3xl mx-auto mb-8">
                    Tu portal definitivo para las últimas noticias, reseñas honestas y los lanzamientos más esperados del mundo gaming.
                </p>
                <a href="#reviews" class="bg-purple-600 hover:bg-purple-700 text-white font-bold text-lg py-4 px-8 rounded-full transition-all duration-300 hover:scale-110 transform shadow-lg shadow-purple-500/30">
                    Ver Reseñas
                </a>
            </div>
        </section>

        <!-- =============================================== -->
        <!-- SECCIÓN DE JUEGOS DESTACADOS -->
        <!-- =============================================== -->
        <section id="reviews" class="py-20 bg-gray-900">
            <div class="container mx-auto px-6">
                <h2 class="text-4xl font-bold text-center mb-12">
                    Juegos <span class="text-purple-500">Destacados</span>
                </h2>
                <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-8">
                    <!-- Tarjeta de Juego 1 -->
                    <div class="bg-gray-800 rounded-lg overflow-hidden shadow-lg hover:shadow-purple-500/40 transition-shadow duration-300 transform hover:-translate-y-2">
                        <img src="https://placehold.co/600x400/1F2937/FFFFFF?text=CyberAura+2088" alt="CyberAura 2088" class="w-full h-48 object-cover">
                        <div class="p-6">
                            <h3 class="text-xl font-bold mb-2">CyberAura 2088</h3>
                            <p class="text-gray-400 mb-4 text-sm">Un RPG de mundo abierto ambientado en una metrópolis futurista obsesionada con el poder y la modificación corporal.</p>
                            <a href="#" class="text-purple-400 hover:text-purple-300 font-semibold">Leer más &rarr;</a>
                        </div>
                    </div>
                    <!-- Tarjeta de Juego 2 -->
                    <div class="bg-gray-800 rounded-lg overflow-hidden shadow-lg hover:shadow-purple-500/40 transition-shadow duration-300 transform hover:-translate-y-2">
                        <img src="https://placehold.co/600x400/1F2937/FFFFFF?text=Valoria+Chronicles" alt="Valoria Chronicles" class="w-full h-48 object-cover">
                        <div class="p-6">
                            <h3 class="text-xl font-bold mb-2">Valoria Chronicles</h3>
                            <p class="text-gray-400 mb-4 text-sm">Embárcate en una aventura épica de fantasía para salvar el reino de Valoria de una oscuridad ancestral.</p>
                            <a href="#" class="text-purple-400 hover:text-purple-300 font-semibold">Leer más &rarr;</a>
                        </div>
                    </div>
                    <!-- Tarjeta de Juego 3 -->
                    <div class="bg-gray-800 rounded-lg overflow-hidden shadow-lg hover:shadow-purple-500/40 transition-shadow duration-300 transform hover:-translate-y-2">
                        <img src="https://placehold.co/600x400/1F2937/FFFFFF?text=Star+Drifter" alt="Star Drifter" class="w-full h-48 object-cover">
                        <div class="p-6">
                            <h3 class="text-xl font-bold mb-2">Star Drifter</h3>
                            <p class="text-gray-400 mb-4 text-sm">Explora una galaxia infinita, comercia con especies alienígenas y lucha por la supervivencia en este simulador espacial.</p>
                            <a href="#" class="text-purple-400 hover:text-purple-300 font-semibold">Leer más &rarr;</a>
                        </div>
                    </div>
                </div>
            </div>
        </section>
    </main>
    
    <!-- =============================================== -->
    <!-- FOOTER -->
    <!-- =============================================== -->
    <footer id="contact" class="bg-gray-950 border-t border-gray-800 py-8">
        <div class="container mx-auto px-6 text-center text-gray-400">
            <p>&copy; 2024 GameVerse. Todos los derechos reservados.</p>
            <div class="flex justify-center space-x-6 mt-4">
                <a href="#" class="hover:text-purple-400 transition-colors">Twitter</a>
                <a href="#" class="hover:text-purple-400 transition-colors">Discord</a>
                <a href="#" class="hover:text-purple-400 transition-colors">YouTube</a>
            </div>
        </div>
    </footer>

    <!-- =============================================== -->
    <!-- JAVASCRIPT EMBEBIDO -->
    <!-- =============================================== -->
    <script>
        // Script para el menú móvil
        const mobileMenuButton = document.getElementById('mobile-menu-button');
        const mobileMenu = document.getElementById('mobile-menu');

        mobileMenuButton.addEventListener('click', () => {
            mobileMenu.classList.toggle('hidden');
        });

        // Opcional: Cerrar menú al hacer clic en un enlace
        const mobileMenuLinks = mobileMenu.getElementsByTagName('a');
        for (let link of mobileMenuLinks) {
            link.addEventListener('click', () => {
                mobileMenu.classList.add('hidden');
            });
        }
    </script>

</body>
</html>
"""
    }
]

def seed_projects():
    """
    Script para poblar la base de datos con los proyectos de ejemplo.
    """
    
    # Esto es necesario para que el script pueda encontrar 'model.database'
    # Asume que ejecutas esto desde la raíz del proyecto (donde está app.py)
    sys.path.append(os.path.abspath(os.path.dirname(__file__)))
    
    try:
        # Importar Config después de ajustar el path si es necesario
        from config import Config
    except ImportError:
        print("❌ Error: No se pudo encontrar el archivo 'config.py'.")
        print("Asegúrate de que 'config.py' exista en la raíz y contenga MONGODB_URI y MONGODB_DB_NAME.")
        return

    # Sobrescribir temporalmente la config si no está
    if not hasattr(Config, 'MONGODB_URI') or not hasattr(Config, 'MONGODB_DB_NAME'):
        print("❌ Error: MONGODB_URI o MONGODB_DB_NAME no están definidos en config.py.")
        return

    db = ChatDatabase()
    if not db.client:
        print("❌ No se pudo conectar a la DB. Abortando 'seed'.")
        return

    print(f"Conectado a la DB. Usando colección: '{db.projects.name}'")
    
    print(f"Añadiendo/actualizando {len(PROJECTS_DATA)} proyectos...")
    
    for project in PROJECTS_DATA:
        try:
            # Usar 'update_one' con 'upsert=True' para evitar duplicados
            # Comprueba si un proyecto con el mismo título ya existe y lo actualiza
            # Si no existe, lo inserta (upsert)
            db.projects.update_one(
                {"title": project['title']}, # Filtro para encontrar el proyecto
                {
                    "$set": { # Datos para insertar o actualizar
                        'description': project['description'],
                        'imageUrl': project['imageUrl'],
                        'projectUrl': project['projectUrl'],
                        'codeSnippet': project['codeSnippet'],
                        'created_at': datetime.utcnow() # Actualizar la fecha
                    }
                },
                upsert=True # Opción mágica: inserta si no existe
            )
            print(f"✅ Proyecto procesado: '{project['title']}'")
        except Exception as e:
            print(f"❌ Error añadiendo/actualizando proyecto '{project['title']}': {e}")
    
    print("\nProceso de 'seed' completado.")
    print(f"Total de proyectos en la colección: {db.projects.count_documents({})}")

if __name__ == "__main__":
    seed_projects()

