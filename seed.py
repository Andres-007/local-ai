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
        "title": "Sitio Web Spotify Rediseñado",
        "description": "Un rediseño moderno y vibrante de la página de inicio de Spotify, enfocado en una estética 'glassmorphism', animaciones suaves y una experiencia de usuario interactiva. Creado con HTML, CSS puro y JavaScript.",
        "imageUrl": "https://placehold.co/600x400/1DB954/ffffff?text=Spotify+Redesign",
        "projectUrl": "#", # Usamos '#' como placeholder. El iframe lo mostrará como una página vacía.
        "codeSnippet": """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Spotify - Rediseño Vibrante</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700&display=swap" rel="stylesheet">
    <style>
        /* --- VARIABLES Y ESTILOS GLOBALES --- */
        :root {
            --spotify-green: #1DB954;
            --dark-bg: #121212;
            --light-text: #FFFFFF;
            --dark-text: #000000;
            --card-bg: rgba(255, 255, 255, 0.05);
            --border-color: rgba(255, 255, 255, 0.1);
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        html {
            scroll-behavior: smooth;
        }

        body {
            font-family: 'Poppins', sans-serif;
            background-color: var(--dark-bg);
            color: var(--light-text);
            overflow-x: hidden;
            position: relative;
        }

        /* --- FONDO ANIMADO --- */
        body::before {
            content: '';
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            z-index: -1;
            background: radial-gradient(circle at 15% 25%, rgba(29, 185, 84, 0.2), transparent 40%),
                        radial-gradient(circle at 85% 75%, rgba(80, 50, 200, 0.2), transparent 40%);
            animation: background-pan 20s linear infinite;
        }

        @keyframes background-pan {
            0% { background-position: 0% 0%; }
            50% { background-position: 100% 100%; }
            100% { background-position: 0% 0%; }
        }

        /* --- ENCABEZADO --- */
        header {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            padding: 1.5rem 5%;
            display: flex;
            justify-content: space-between;
            align-items: center;
            z-index: 1000;
            transition: background-color 0.4s ease, padding 0.4s ease;
        }

        header.scrolled {
            background-color: rgba(0, 0, 0, 0.8);
            backdrop-filter: blur(10px);
            padding: 1rem 5%;
        }

        .logo {
            font-size: 1.8rem;
            font-weight: 700;
            display: flex;
            align-items: center;
            gap: 0.5rem;
            text-decoration: none;
            color: var(--light-text);
        }

        .logo svg {
            width: 32px;
            height: 32px;
            fill: var(--light-text);
        }

        nav ul {
            list-style: none;
            display: flex;
            gap: 2rem;
        }

        nav a {
            color: var(--light-text);
            text-decoration: none;
            font-weight: 600;
            position: relative;
            transition: color 0.3s ease;
        }

        nav a::after {
            content: '';
            position: absolute;
            width: 0;
            height: 2px;
            bottom: -5px;
            left: 50%;
            transform: translateX(-50%);
            background-color: var(--spotify-green);
            transition: width 0.3s ease;
        }

        nav a:hover {
            color: var(--spotify-green);
        }

        nav a:hover::after {
            width: 100%;
        }

        /* --- SECCIÓN HERO --- */
        .hero {
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            text-align: center;
            padding: 0 2rem;
            position: relative;
        }

        .hero h1 {
            font-size: clamp(2.5rem, 8vw, 5.5rem);
            font-weight: 700;
            line-height: 1.1;
            background: linear-gradient(90deg, #1DB954, #FFFFFF);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 1rem;
        }

        .hero p {
            font-size: clamp(1rem, 3vw, 1.25rem);
            max-width: 600px;
            margin-bottom: 2rem;
            color: rgba(255, 255, 255, 0.8);
        }

        .cta-button {
            background-color: var(--spotify-green);
            color: var(--dark-text);
            padding: 1rem 2.5rem;
            border-radius: 50px;
            text-decoration: none;
            font-weight: 700;
            font-size: 1.1rem;
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }

        .cta-button:hover {
            transform: scale(1.05);
            box-shadow: 0 0 25px rgba(29, 185, 84, 0.7);
        }

        /* --- SECCIONES GENERALES Y TARJETAS --- */
        .section {
            padding: 6rem 5%;
            max-width: 1200px;
            margin: 0 auto;
        }

        .section-title {
            text-align: center;
            font-size: 2.5rem;
            margin-bottom: 3rem;
            font-weight: 700;
        }

        .features-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 2rem;
        }

        .feature-card {
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 15px;
            padding: 2rem;
            text-align: center;
            transition: transform 0.3s ease, border-color 0.3s ease;
            position: relative;
            overflow: hidden;
            backdrop-filter: blur(5px);
        }

        /* Efecto Aurora en hover */
        .feature-card::before {
            content: "";
            position: absolute;
            top: var(--y, 0);
            left: var(--x, 0);
            transform: translate(-50%, -50%);
            width: 250px;
            height: 250px;
            background: radial-gradient(circle, var(--spotify-green) 0%, transparent 70%);
            opacity: 0;
            transition: opacity 0.4s ease;
            pointer-events: none;
        }

        .feature-card:hover {
            transform: translateY(-10px);
            border-color: var(--spotify-green);
        }

        .feature-card:hover::before {
            opacity: 0.15;
        }

        .feature-card .icon {
            width: 60px;
            height: 60px;
            margin: 0 auto 1.5rem;
            color: var(--spotify-green);
        }

        .feature-card h3 {
            font-size: 1.5rem;
            margin-bottom: 0.5rem;
        }

        .feature-card p {
            color: rgba(255, 255, 255, 0.7);
            line-height: 1.6;
        }

        /* --- SECCIÓN FAQ (PREGUNTAS FRECUENTES) --- */
        .faq-container {
            max-width: 800px;
            margin: 0 auto;
        }

        .faq-item {
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 10px;
            margin-bottom: 1rem;
            overflow: hidden;
            transition: border-color 0.3s ease;
        }
        
        .faq-item:hover {
            border-color: rgba(255, 255, 255, 0.3);
        }

        .faq-question {
            padding: 1.5rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            cursor: pointer;
            font-weight: 600;
            font-size: 1.1rem;
        }

        .faq-question .toggle-icon {
            font-size: 1.5rem;
            transition: transform 0.3s ease;
            color: var(--spotify-green);
        }

        .faq-answer {
            max-height: 0;
            overflow: hidden;
            transition: max-height 0.5s ease, padding 0.5s ease;
            padding: 0 1.5rem;
            color: rgba(255, 255, 255, 0.8);
            line-height: 1.7;
        }

        .faq-item.active .faq-answer {
            max-height: 200px; /* Ajustar si la respuesta es más larga */
            padding: 0 1.5rem 1.5rem;
        }
        
        .faq-item.active .toggle-icon {
            transform: rotate(45deg);
        }

        /* --- FOOTER --- */
        footer {
            background-color: #000;
            padding: 4rem 5% 2rem;
            border-top: 1px solid var(--border-color);
        }

        .footer-container {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 2rem;
            margin-bottom: 3rem;
        }

        .footer-column h4 {
            font-size: 1.2rem;
            margin-bottom: 1rem;
            color: var(--spotify-green);
        }

        .footer-column ul {
            list-style: none;
        }

        .footer-column ul li {
            margin-bottom: 0.75rem;
        }

        .footer-column a {
            color: rgba(255, 255, 255, 0.7);
            text-decoration: none;
            transition: color 0.3s ease;
        }

        .footer-column a:hover {
            color: var(--light-text);
        }

        .footer-bottom {
            text-align: center;
            padding-top: 2rem;
            border-top: 1px solid var(--border-color);
            font-size: 0.9rem;
            color: rgba(255, 255, 255, 0.5);
        }

        /* --- CLASES DE ANIMACIÓN AL DESPLAZAR --- */
        .animate-on-scroll {
            opacity: 0;
            transform: translateY(30px);
            transition: opacity 0.6s ease-out, transform 0.6s ease-out;
        }

        .animate-on-scroll.is-visible {
            opacity: 1;
            transform: translateY(0);
        }

        /* --- RESPONSIVE DESIGN --- */
        @media (max-width: 768px) {
            header {
                padding: 1rem 5%;
            }
            nav ul {
                display: none; /* Simplificando para el ejemplo */
            }
            .section {
                padding: 4rem 5%;
            }
            .section-title {
                font-size: 2rem;
            }
        }
    </style>
</head>
<body>

    <!-- ==================== ENCABEZADO ==================== -->
    <header id="main-header">
        <a href="#" class="logo">
            <svg viewBox="0 0 167.5 167.5"><path d="M83.7 0C37.5 0 0 37.5 0 83.7c0 46.3 37.5 83.7 83.7 83.7 46.3 0 83.7-37.5 83.7-83.7S130 0 83.7 0zM122 120.8c-1.4 2.5-4.4 3.2-6.8 1.8-19.4-11.8-43.6-14.5-72.4-8-2.8.6-5.5-1.2-6-4-.6-2.8 1.2-5.5 4-6 31.6-7.2 58.6-4.2 80.3 9.2 2.5 1.4 3.2 4.4 1.8 6.8zM132.4 98c-1.8 3-5.5 4-8.5 2.2-22.5-13.7-56.8-17.7-83.4-9.7-3.2 1-6.5-1-7.5-4.3-1-3.2 1-6.5 4.3-7.5 30.4-8.9 68.7-4.5 94.5 11.2 3 1.8 4 5.5 2.2 8.5zM133.4 74C1.8 3.8 6.5 5 10 3.2 26.5-16.2 71.7-18.2 97.4-10 3.8 1.2 7.5-1.5 8.7-5.3 1.2-3.8-1.5-7.5-5.3-8.7C65.6 45.4 27 47.8 2.2 65.8c-3.8 2.6-5 7.5-2.5 11.3 2.5 3.8 7.5 5 11.3 2.5 34.5-17.2 77.2-14.8 106.2 7.5 3.5 2.6 8.3 1.2 11-2.3 2.6-3.5 1.2-8.3-2.3-11z"/></svg>
            <span>Spotify</span>
        </a>
        <nav>
            <ul>
                <li><a href="#">Premium</a></li>
                <li><a href="#">Ayuda</a></li>
                <li><a href="#">Descargar</a></li>
            </ul>
        </nav>
    </header>

    <main>
        <!-- ==================== SECCIÓN HERO ==================== -->
        <section class="hero">
            <h1 class="animate-on-scroll">Escuchar lo es todo.</h1>
            <p class="animate-on-scroll" style="transition-delay: 0.2s;">Millones de canciones y pódcasts. No necesitas tarjeta de crédito.</p>
            <a href="#" class="cta-button animate-on-scroll" style="transition-delay: 0.4s;">OBTÉN SPOTIFY FREE</a>
        </section>

        <!-- ==================== SECCIÓN DE CARACTERÍSTICAS ==================== -->
        <section id="features" class="section">
            <h2 class="section-title animate-on-scroll">¿Por qué pasarse a Spotify?</h2>
            <div class="features-grid">
                
                <div class="feature-card animate-on-scroll">
                    <div class="icon">
                        <svg xmlns="http://www.w3.org/2000/svg" fill="currentColor" viewBox="0 0 24 24"><path d="M12 3v10.55c-.59-.34-1.27-.55-2-.55c-2.21 0-4 1.79-4 4s1.79 4 4 4s4-1.79 4-4V7h4V3h-6z"/></svg>
                    </div>
                    <h3>Playlists personalizadas.</h3>
                    <p>Creamos listas de reproducción basadas en tus gustos. Descubre nueva música y redescubre tus clásicos favoritos.</p>
                </div>

                <div class="feature-card animate-on-scroll" style="transition-delay: 0.2s;">
                    <div class="icon">
                        <svg xmlns="http://www.w3.org/2000/svg" fill="currentColor" viewBox="0 0 24 24"><path d="M4 6H2v14c0 1.1.9 2 2 2h14v-2H4V6zm16-4H8c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm-2 10h-4v4h-2v-4H8v-2h4V6h2v4h4v2z"/></svg>
                    </div>
                    <h3>Crea y comparte.</h3>
                    <p>Construye tus propias playlists desde cero. Compártelas con amigos y crea la banda sonora perfecta para cualquier momento.</p>
                </div>

                <div class="feature-card animate-on-scroll" style="transition-delay: 0.4s;">
                    <div class="icon">
                        <svg xmlns="http://www.w3.org/2000/svg" fill="currentColor" viewBox="0 0 24 24"><path d="M12 1a9 9 0 0 0-9 9v7c0 1.66 1.34 3 3 3h3v-8H5v-2c0-3.87 3.13-7 7-7s7 3.13 7 7v2h-4v8h3c1.66 0 3-1.34 3-3v-7a9 9 0 0 0-9-9z"/></svg>
                    </div>
                    <h3>Pódcasts y más.</h3>
                    <p>Sumérgete en un universo de historias, noticias y entretenimiento con miles de pódcasts disponibles al instante.</p>
                </div>

            </div>
        </section>

        <!-- ==================== SECCIÓN DE PREGUNTAS FRECUENTES ==================== -->
        <section id="faq" class="section">
            <h2 class="section-title animate-on-scroll">Preguntas frecuentes</h2>
            <div class="faq-container">

                <div class="faq-item animate-on-scroll">
                    <div class="faq-question">
                        <span>¿Cómo puedo crear una playlist?</span>
                        <span class="toggle-icon">+</span>
                    </div>
                    <div class="faq-answer">
                        <p>Es muy fácil. Simplemente ve a "Tu Biblioteca", pulsa en el icono "+" y selecciona "Playlist". Dale un nombre, añade una descripción si quieres, ¡y empieza a añadir tus canciones favoritas!</p>
                    </div>
                </div>

                <div class="faq-item animate-on-scroll" style="transition-delay: 0.1s;">
                    <div class="faq-question">
                        <span>¿Spotify es realmente gratis?</span>
                        <span class="toggle-icon">+</span>
                    </div>
                    <div class="faq-answer">
                        <p>Sí, puedes usar Spotify totalmente gratis. La versión gratuita te da acceso a todo el catálogo de música y pódcasts, pero incluye anuncios y tiene algunas limitaciones, como no poder descargar música para escuchar sin conexión.</p>
                    </div>
                </div>

                <div class="faq-item animate-on-scroll" style="transition-delay: 0.2s;">
                    <div class="faq-question">
                        <span>¿Qué ventajas ofrece Spotify Premium?</span>
                        <span class="toggle-icon">+</span>
                    </div>
                    <div class="faq-answer">
                        <p>Spotify Premium elimina todos los anuncios, te permite descargar música para escucharla sin conexión, te da saltos ilimitados y te ofrece la máxima calidad de audio disponible. ¡Es la experiencia musical definitiva!</p>
                    </div>
                </div>

                <div class="faq-item animate-on-scroll" style="transition-delay: 0.3s;">
                    <div class="faq-question">
                        <span>¿Puedo usar Spotify en varios dispositivos?</span>
                        <span class="toggle-icon">+</span>
                    </div>
                    <div class="faq-answer">
                        <p>¡Por supuesto! Puedes instalar y usar tu cuenta de Spotify en tu móvil, tablet, ordenador, smart TV, consola de videojuegos y muchos otros dispositivos. Tu música te acompaña a todas partes.</p>
                    </div>
                </div>

            </div>
        </section>
    </main>

    <!-- ==================== FOOTER ==================== -->
    <footer>
        <div class="footer-container">
            <div class="footer-column">
                <h4>Compañía</h4>
                <ul>
                    <li><a href="#">Acerca de</a></li>
                    <li><a href="#">Empleo</a></li>
                    <li><a href="#">For the Record</a></li>
                </ul>
            </div>
            <div class="footer-column">
                <h4>Comunidades</h4>
                <ul>
                    <li><a href="#">Para artistas</a></li>
                    <li><a href="#">Desarrolladores</a></li>
                    <li><a href="#">Publicidad</a></li>
                    <li><a href="#">Inversores</a></li>
                </ul>
            </div>
            <div class="footer-column">
                <h4>Enlaces útiles</h4>
                <ul>
                    <li><a href="#">Ayuda</a></li>
                    <li><a href="#">App gratis para móvil</a></li>
                    <li><a href="#">Reproductor web</a></li>
                </ul>
            </div>
        </div>
        <div class="footer-bottom">
            <p>&copy; 2024 Spotify AB. Creado por Web Dev AI como ejemplo de rediseño.</p>
        </div>
    </footer>

    <script>
        document.addEventListener('DOMContentLoaded', () => {

            // --- EFECTO DE SCROLL EN EL HEADER ---
            const header = document.getElementById('main-header');
            window.addEventListener('scroll', () => {
                if (window.scrollY > 50) {
                    header.classList.add('scrolled');
                } else {
                    header.classList.remove('scrolled');
                }
            });

            // --- ACORDEÓN DE PREGUNTAS FRECUENTES (FAQ) ---
            const faqItems = document.querySelectorAll('.faq-item');
            faqItems.forEach(item => {
                const question = item.querySelector('.faq-question');
                question.addEventListener('click', () => {
                    // Cierra otros items abiertos si quieres que solo uno esté abierto a la vez
                    // faqItems.forEach(otherItem => {
                    //     if (otherItem !== item) {
                    //         otherItem.classList.remove('active');
                    //     }
                    // });
                    item.classList.toggle('active');
                });
            });

            // --- ANIMACIONES AL HACER SCROLL ---
            const scrollElements = document.querySelectorAll('.animate-on-scroll');
            const observer = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        entry.target.classList.add('is-visible');
                        observer.unobserve(entry.target); // Dejar de observar una vez animado
                    }
                });
            }, {
                threshold: 0.1 // El elemento se activa cuando el 10% es visible
            });

            scrollElements.forEach(el => {
                observer.observe(el);
            });

            // --- EFECTO AURORA EN LAS TARJETAS ---
            const featureCards = document.querySelectorAll('.feature-card');
            featureCards.forEach(card => {
                card.addEventListener('mousemove', (e) => {
                    const rect = card.getBoundingClientRect();
                    const x = e.clientX - rect.left;
                    const y = e.clientY - rect.top;
                    card.style.setProperty('--x', `${x}px`);
                    card.style.setProperty('--y', `${y}px`);
                });
            });
        });
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

