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
        "title": "Sitio Web Burger Bliss",
        "description": "Una landing page vibrante y moderna para un restaurante de comida rápida, 'Burger Bliss'. Creada con HTML, CSS puro y animaciones dinámicas al hacer scroll.",
        "imageUrl": "https://placehold.co/600x400/FF6B6B/ffffff?text=Burger+Bliss",
        "projectUrl": "#", # Usamos '#' como placeholder. El iframe lo mostrará como una página vacía.
        "codeSnippet": """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Burger Bliss - Sabor Inigualable</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700&display=swap" rel="stylesheet">
    
    <style>
        /* --- RESET Y VARIABLES GLOBALES --- */
        :root {
            --primary-color: #FF6B6B;
            --secondary-color: #FFE66D;
            --dark-color: #2c3e50;
            --light-color: #ecf0f1;
            --background-color: #fdfdfd;
            --shadow: 0 10px 30px rgba(0, 0, 0, 0.07);
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
            background-color: var(--background-color);
            color: var(--dark-color);
            line-height: 1.6;
            overflow-x: hidden;
        }

        .container {
            max-width: 1100px;
            margin: 0 auto;
            padding: 0 2rem;
        }

        h1, h2, h3 {
            font-weight: 600;
            line-height: 1.2;
        }

        h1 { font-size: 3.5rem; }
        h2 { font-size: 2.5rem; }
        h3 { font-size: 1.5rem; }

        p {
            margin-bottom: 1rem;
        }

        img {
            max-width: 100%;
            height: auto;
            display: block;
        }

        /* --- ANIMACIONES Y CLASES DE UTILIDAD --- */
        .animate-on-scroll {
            opacity: 0;
            transform: translateY(30px);
            transition: opacity 0.6s ease-out, transform 0.6s ease-out;
        }

        .animate-on-scroll.is-visible {
            opacity: 1;
            transform: translateY(0);
        }

        .btn {
            display: inline-block;
            padding: 12px 28px;
            background-color: var(--primary-color);
            color: white;
            text-decoration: none;
            border-radius: 50px;
            font-weight: 600;
            transition: transform 0.3s ease, background-color 0.3s ease;
            box-shadow: 0 4px 15px rgba(255, 107, 107, 0.3);
        }

        .btn:hover {
            transform: translateY(-3px);
            background-color: #ff4757;
        }

        /* --- HEADER Y NAVEGACIÓN --- */
        .main-header {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            z-index: 1000;
            padding: 1rem 0;
            background-color: rgba(253, 253, 253, 0.85);
            backdrop-filter: blur(10px);
            transition: box-shadow 0.3s ease;
        }
        
        .main-header.scrolled {
            box-shadow: var(--shadow);
        }

        .main-header .container {
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .logo {
            font-size: 1.8rem;
            font-weight: 700;
            color: var(--dark-color);
            text-decoration: none;
        }

        .logo span {
            color: var(--primary-color);
        }

        .main-nav ul {
            display: flex;
            list-style: none;
        }

        .main-nav ul li {
            margin-left: 2rem;
        }

        .main-nav ul li a {
            text-decoration: none;
            color: var(--dark-color);
            font-weight: 600;
            position: relative;
            padding-bottom: 5px;
            transition: color 0.3s ease;
        }

        .main-nav ul li a::after {
            content: '';
            position: absolute;
            bottom: 0;
            left: 0;
            width: 0;
            height: 2px;
            background-color: var(--primary-color);
            transition: width 0.4s cubic-bezier(0.25, 0.8, 0.25, 1);
        }

        .main-nav ul li a:hover {
            color: var(--primary-color);
        }

        .main-nav ul li a:hover::after {
            width: 100%;
        }

        /* --- SECCIÓN HERO --- */
        .hero {
            height: 100vh;
            display: flex;
            align-items: center;
            text-align: center;
            padding-top: 80px; /* Header height */
        }

        .hero-content {
            animation: fadeIn 1s ease-in-out forwards;
        }

        .hero-content h1 {
            margin-bottom: 1rem;
            animation: slideInUp 0.8s ease-out 0.2s forwards;
            opacity: 0;
        }

        .hero-content p {
            font-size: 1.2rem;
            max-width: 600px;
            margin: 0 auto 2rem auto;
            color: #555;
            animation: slideInUp 0.8s ease-out 0.4s forwards;
            opacity: 0;
        }

        .hero-content .btn {
            animation: slideInUp 0.8s ease-out 0.6s forwards;
            opacity: 0;
        }

        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }

        @keyframes slideInUp {
            from {
                transform: translateY(50px);
                opacity: 0;
            }
            to {
                transform: translateY(0);
                opacity: 1;
            }
        }

        /* --- SECCIÓN MENÚ --- */
        #menu {
            padding: 6rem 0;
        }

        .section-header {
            text-align: center;
            margin-bottom: 4rem;
        }

        .section-header h2 {
            margin-bottom: 0.5rem;
        }

        .section-header p {
            color: #777;
            max-width: 500px;
            margin: 0 auto;
        }

        .menu-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 2.5rem;
        }

        .menu-item {
            background: white;
            border-radius: 15px;
            overflow: hidden;
            box-shadow: var(--shadow);
            transition: transform 0.4s cubic-bezier(0.25, 0.8, 0.25, 1), box-shadow 0.4s cubic-bezier(0.25, 0.8, 0.25, 1);
        }
        
        .menu-item:hover {
            transform: translateY(-10px);
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
        }

        .menu-item-image {
            height: 220px;
            overflow: hidden;
        }

        .menu-item-image img {
            width: 100%;
            height: 100%;
            object-fit: cover;
            transition: transform 0.5s ease;
        }

        .menu-item:hover .menu-item-image img {
            transform: scale(1.1);
        }

        .menu-item-content {
            padding: 1.5rem;
        }

        .menu-item-content h3 {
            margin-bottom: 0.5rem;
        }

        .menu-item-content p {
            font-size: 0.9rem;
            color: #666;
            margin-bottom: 1rem;
        }

        .menu-item-price {
            font-size: 1.3rem;
            font-weight: 700;
            color: var(--primary-color);
        }

        /* --- SECCIÓN SOBRE NOSOTROS --- */
        #about {
            padding: 6rem 0;
            background-color: #f9f9f9;
        }

        .about-content {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 4rem;
            align-items: center;
        }

        .about-image {
            border-radius: 15px;
            overflow: hidden;
            box-shadow: var(--shadow);
        }
        
        .about-image img {
             border-radius: 15px;
        }

        /* --- FOOTER --- */
        .main-footer {
            background-color: var(--dark-color);
            color: var(--light-color);
            padding: 4rem 0;
            text-align: center;
        }

        .footer-content h3 {
            color: white;
            margin-bottom: 1rem;
        }

        .footer-content p {
            margin-bottom: 2rem;
            color: #bdc3c7;
        }

        .social-links a {
            color: white;
            text-decoration: none;
            font-size: 1.5rem;
            margin: 0 1rem;
            transition: color 0.3s ease, transform 0.3s ease;
            display: inline-block;
        }

        .social-links a:hover {
            color: var(--primary-color);
            transform: translateY(-3px);
        }

        .copyright {
            margin-top: 3rem;
            font-size: 0.9rem;
            color: #7f8c8d;
        }

        /* --- RESPONSIVE DESIGN --- */
        @media (max-width: 768px) {
            h1 { font-size: 2.8rem; }
            h2 { font-size: 2rem; }

            .main-header .container {
                flex-direction: column;
            }
            .main-nav ul {
                margin-top: 1rem;
            }
            .main-nav ul li {
                margin: 0 1rem;
            }

            .hero {
                height: auto;
                padding: 10rem 0 4rem 0;
            }

            .about-content {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>

    <!-- HEADER -->
    <header class="main-header" id="main-header">
        <div class="container">
            <a href="#" class="logo">Burger<span>Bliss</span></a>
            <nav class="main-nav">
                <ul>
                    <li><a href="#hero">Inicio</a></li>
                    <li><a href="#menu">Menú</a></li>
                    <li><a href="#about">Nosotros</a></li>
                    <li><a href="#contact">Contacto</a></li>
                </ul>
            </nav>
        </div>
    </header>

    <main>
        <!-- SECCIÓN HERO -->
        <section class="hero" id="hero">
            <div class="container">
                <div class="hero-content">
                    <h1>El Sabor que te Hace Sonreír.</h1>
                    <p>Ingredientes frescos, recetas secretas y una pasión por la perfección. Cada bocado es una experiencia única.</p>
                    <a href="#menu" class="btn">Ver Nuestro Menú</a>
                </div>
            </div>
        </section>

        <!-- SECCIÓN MENÚ -->
        <section id="menu">
            <div class="container">
                <div class="section-header animate-on-scroll">
                    <h2>Nuestro Menú Estrella</h2>
                    <p>Hechos con amor, servidos con orgullo. Estos son los favoritos de nuestros clientes.</p>
                </div>
                <div class="menu-grid">
                    <!-- Item 1 -->
                    <div class="menu-item animate-on-scroll">
                        <div class="menu-item-image">
                            <img src="https://images.unsplash.com/photo-1568901346375-23c9450c58cd?q=80&w=800&auto=format&fit=crop" alt="Hamburguesa Clásica">
                        </div>
                        <div class="menu-item-content">
                            <h3>Bliss Clásica</h3>
                            <p>Carne de res premium, queso cheddar, lechuga fresca, tomate y nuestra salsa secreta en pan brioche.</p>
                            <span class="menu-item-price">$8.99</span>
                        </div>
                    </div>
                    <!-- Item 2 -->
                    <div class="menu-item animate-on-scroll" style="transition-delay: 0.1s;">
                        <div class="menu-item-image">
                            <img src="https://images.unsplash.com/photo-1594041682983-703e7815d39d?q=80&w=800&auto=format&fit=crop" alt="Papas Fritas">
                        </div>
                        <div class="menu-item-content">
                            <h3>Papas Doradas</h3>
                            <p>Crujientes por fuera, suaves por dentro. Cortadas a mano y fritas a la perfección con un toque de sal marina.</p>
                            <span class="menu-item-price">$3.49</span>
                        </div>
                    </div>
                    <!-- Item 3 -->
                    <div class="menu-item animate-on-scroll" style="transition-delay: 0.2s;">
                        <div class="menu-item-image">
                            <img src="https://images.unsplash.com/photo-1625863836693-a2565eb62a12?q=80&w=800&auto=format&fit=crop" alt="Malteada de Chocolate">
                        </div>
                        <div class="menu-item-content">
                            <h3>Malteada de Ensueño</h3>
                            <p>Cremosa malteada de chocolate belga, coronada con nata montada y sirope de cacao.</p>
                            <span class="menu-item-price">$5.99</span>
                        </div>
                    </div>
                </div>
            </div>
        </section>

        <!-- SECCIÓN SOBRE NOSOTROS -->
        <section id="about">
            <div class="container">
                <div class="about-content">
                    <div class="about-text animate-on-scroll">
                        <h2 style="margin-bottom: 1.5rem;">Nuestra Historia: <br>Pasión por la Comida</h2>
                        <p>Burger Bliss nació de un sueño simple: crear la hamburguesa perfecta. Empezamos en un pequeño local, obsesionados con la calidad de cada ingrediente. Creemos que la comida rápida no tiene por qué ser comida de baja calidad.</p>
                        <p>Hoy, seguimos siendo fieles a nuestros principios, sirviendo comida deliciosa que une a las personas y crea momentos felices.</p>
                    </div>
                    <div class="about-image animate-on-scroll" style="transition-delay: 0.2s;">
                        <img src="https://images.unsplash.com/photo-1550547660-d9450f859349?q=80&w=800&auto=format&fit=crop" alt="Interior del restaurante">
                    </div>
                </div>
            </div>
        </section>
    </main>

    <!-- FOOTER -->
    <footer class="main-footer" id="contact">
        <div class="container animate-on-scroll">
            <div class="footer-content">
                <h3>Burger<span>Bliss</span></h3>
                <p>Ven y descubre por qué una hamburguesa puede ser una obra de arte.</p>
                <div class="social-links">
                    <a href="#" aria-label="Instagram">
                        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="2" width="20" height="20" rx="5" ry="5"></rect><path d="M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z"></path><line x1="17.5" y1="6.5" x2="17.51" y2="6.5"></line></svg>
                    </a>
                    <a href="#" aria-label="Facebook">
                        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 2h-3a5 5 0 0 0-5 5v3H7v4h3v8h4v-8h3l1-4h-4V7a1 1 0 0 1 1-1h3z"></path></svg>
                    </a>
                    <a href="#" aria-label="Twitter">
                        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M23 3a10.9 10.9 0 0 1-3.14 1.53 4.48 4.48 0 0 0-7.86 3v1A10.66 10.66 0 0 1 3 4s-4 9 5 13a11.64 11.64 0 0 1-7 2c9 5 20 0 20-11.5a4.5 4.5 0 0 0-.08-.83A7.72 7.72 0 0 0 23 3z"></path></svg>
                    </a>
                </div>
                <p class="copyright">&copy; 2024 Burger Bliss. Todos los derechos reservados.</p>
            </div>
        </div>
    </footer>

    <script>
        document.addEventListener('DOMContentLoaded', function() {
            
            // --- Animación de Sombra en el Header al hacer Scroll ---
            const header = document.getElementById('main-header');
            window.addEventListener('scroll', () => {
                if (window.scrollY > 50) {
                    header.classList.add('scrolled');
                } else {
                    header.classList.remove('scrolled');
                }
            });

            // --- Animación de Elementos al Entrar en la Vista (On Scroll) ---
            const animatedElements = document.querySelectorAll('.animate-on-scroll');

            // Usamos IntersectionObserver para un rendimiento óptimo
            const observer = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    // Si el elemento está en la vista (intersecting)
                    if (entry.isIntersecting) {
                        entry.target.classList.add('is-visible');
                    }
                });
            }, {
                threshold: 0.1 // El elemento se considera visible cuando el 10% de él se ve
            });

            // Observar cada elemento con la clase .animate-on-scroll
            animatedElements.forEach(el => {
                observer.observe(el);
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
        print(" Error: No se pudo encontrar el archivo 'config.py'.")
        print("Asegúrate de que 'config.py' exista en la raíz y contenga MONGODB_URI y MONGODB_DB_NAME.")
        return

    # Sobrescribir temporalmente la config si no está
    if not hasattr(Config, 'MONGODB_URI') or not hasattr(Config, 'MONGODB_DB_NAME'):
        print("Error: MONGODB_URI o MONGODB_DB_NAME no están definidos en config.py.")
        return

    db = ChatDatabase()
    if not db.client:
        print(" No se pudo conectar a la DB. Abortando 'seed'.")
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
            print(f" Proyecto procesado: '{project['title']}'")
        except Exception as e:
            print(f" Error añadiendo/actualizando proyecto '{project['title']}': {e}")
    
    print("\nProceso de 'seed' completado.")
    print(f"Total de proyectos en la colección: {db.projects.count_documents({})}")

if __name__ == "__main__":
    seed_projects()

