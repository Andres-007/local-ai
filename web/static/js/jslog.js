document.addEventListener('DOMContentLoaded', function() {
    // --- Selectores de Modales ---
    const authModal = document.getElementById('authModal');
    const authBtn = document.getElementById('authBtn');
    const closeModalBtn = document.getElementById('closeModalBtn');
    const authTabs = document.querySelectorAll('#authModal .modal-tab');
    const authFormContainers = document.querySelectorAll('#authModal .form-container');
    const errorMessage = document.getElementById('errorMessage');
    const forgotPasswordLink = document.getElementById('forgotPasswordLink');
    const forgotPasswordModal = document.getElementById('forgotPasswordModal');
    const closeForgotModalBtn = document.getElementById('closeForgotModalBtn');
    const forgotPasswordForm = document.getElementById('forgotPasswordForm');
    const forgotErrorMessage = document.getElementById('forgotErrorMessage');
    const forgotSuccessMessage = document.getElementById('forgotSuccessMessage');

    const projectDetailsModal = document.getElementById('projectDetailsModal');
    const closeProjectModalBtn = document.getElementById('closeProjectModalBtn');
    const projectDetailsTabs = document.querySelectorAll('#projectDetailsTabs .modal-tab');
    const projectDetailsTitle = document.getElementById('projectDetailsTitle');
    const projectPreviewContainer = document.getElementById('projectPreviewContainer');
    const projectPreviewIframe = document.getElementById('projectPreview'); // FIXED: Removed duplicate "document ="
    const projectCodeContainer = document.getElementById('projectCodeContainer');
    const projectCodeBlock = document.getElementById('projectCode');
    const swiperWrapper = document.querySelector('#projectsCarousel .swiper-wrapper');

    // --- Lógica General de Modales ---
    const openModal = (modalId) => {
        const modal = document.getElementById(modalId);
        if (modal) modal.classList.add('active');
    };

    const closeModal = (modalId) => {
        const modal = document.getElementById(modalId);
        if (modal) modal.classList.remove('active');
        
        // Limpiar iframe y resetear contenedores al cerrar modal de proyecto
        if (modalId === 'projectDetailsModal') {
            projectPreviewIframe.src = 'about:blank';
            projectPreviewIframe.srcdoc = '';
            projectCodeBlock.textContent = '';
            
            // Resetear la visibilidad de los contenedores
            projectPreviewContainer.classList.remove('active');
            projectCodeContainer.classList.remove('active');
        }
    };

    // --- Event Listeners para Modal de Auth ---
    authBtn.addEventListener('click', () => {
        switchAuthTab('login');
        openModal('authModal');
    });
    closeModalBtn.addEventListener('click', () => closeModal('authModal'));
    authModal.addEventListener('click', (e) => e.target === authModal && closeModal('authModal'));

    // --- Olvidé mi contraseña ---
    forgotPasswordLink.addEventListener('click', (e) => {
        e.preventDefault();
        closeModal('authModal');
        forgotErrorMessage.style.display = 'none';
        forgotSuccessMessage.style.display = 'none';
        document.getElementById('forgotEmail').value = '';
        openModal('forgotPasswordModal');
    });
    closeForgotModalBtn.addEventListener('click', () => closeModal('forgotPasswordModal'));
    forgotPasswordModal.addEventListener('click', (e) => e.target === forgotPasswordModal && closeModal('forgotPasswordModal'));
    forgotPasswordForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        forgotErrorMessage.style.display = 'none';
        forgotSuccessMessage.style.display = 'none';
        const email = document.getElementById('forgotEmail').value.trim();
        try {
            const res = await fetch('/forgot-password', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email })
            });
            const data = await res.json();
            if (res.ok) {
                forgotSuccessMessage.textContent = data.message || 'Si existe una cuenta con ese email, recibirás un enlace para restablecer tu contraseña.';
                forgotSuccessMessage.style.display = 'block';
                forgotPasswordForm.reset();
            } else {
                forgotErrorMessage.textContent = data.error || 'Error al enviar. Intenta de nuevo.';
                forgotErrorMessage.style.display = 'block';
            }
        } catch (err) {
            forgotErrorMessage.textContent = 'Error de conexión. Intenta de nuevo.';
            forgotErrorMessage.style.display = 'block';
        }
    });

    authTabs.forEach(tab => {
        tab.addEventListener('click', () => {
            switchAuthTab(tab.getAttribute('data-tab'));
        });
    });

    // Función específica para las pestañas de autenticación
    function switchAuthTab(activeTab) {
        authTabs.forEach(t => {
            t.classList.toggle('active', t.getAttribute('data-tab') === activeTab);
        });
        authFormContainers.forEach(c => {
            c.classList.toggle('active', c.getAttribute('data-tab') === activeTab);
        });
        errorMessage.style.display = 'none';
    }

    // --- Event Listeners para Modal de Proyecto ---
    closeProjectModalBtn.addEventListener('click', () => closeModal('projectDetailsModal'));
    projectDetailsModal.addEventListener('click', (e) => e.target === projectDetailsModal && closeModal('projectDetailsModal'));

    projectDetailsTabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const activeTab = tab.getAttribute('data-tab');
            
            // Activar la pestaña seleccionada
            projectDetailsTabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');

            // Mostrar solo el contenedor correspondiente
            if (activeTab === 'preview') {
                projectPreviewContainer.classList.add('active');
                projectCodeContainer.classList.remove('active');
            } else if (activeTab === 'code') {
                projectPreviewContainer.classList.remove('active');
                projectCodeContainer.classList.add('active');
                
                // Re-resaltar el código
                setTimeout(() => {
                    if (hljs) { 
                        hljs.highlightElement(projectCodeBlock);
                    }
                }, 0);
            }
        });
    });

    // --- Lógica de carga de Proyectos y Swiper ---
    let swiperInstance; 
    const projectsPaging = { limit: 12, offset: 0, hasMore: false, loading: false };

    async function fetchProjectsFromDB(reset = true) {
        if (projectsPaging.loading) return;
        projectsPaging.loading = true;
        try {
            if (reset) {
                projectsPaging.offset = 0;
                swiperWrapper.innerHTML = '';
            }
            const params = new URLSearchParams({
                limit: projectsPaging.limit,
                offset: projectsPaging.offset
            });
            const res = await fetch(`/api/projects?${params.toString()}`); 
            
            if (!res.ok) {
                throw new Error(`Error del servidor: ${res.status}`);
            }
            
            const data = await res.json();
            const projects = data.projects; 
            
            if (!projects || projects.length === 0) {
                 swiperWrapper.innerHTML = `<div class="projects-loading">No hay proyectos para mostrar.</div>`;
                 return;
            }

            renderProjects(projects, !reset);
            projectsPaging.hasMore = Boolean(data.has_more);
            updateProjectsLoadMoreSlide();

        } catch (error) {
            console.error('Error al cargar los proyectos:', error);
            swiperWrapper.innerHTML = `<div class="projects-loading">No se pudieron cargar los proyectos.</div>`;
        } finally {
            projectsPaging.loading = false;
        }
    }

    function renderProjects(projects, append = false) {
        if (!append) {
            swiperWrapper.innerHTML = '';
        }
        const frag = document.createDocumentFragment();
        projects.forEach(project => {
            const slide = document.createElement('div');
            slide.classList.add('swiper-slide');
            
            const fallbackImg = `https://placehold.co/600x400/1c1c2b/f0f0f5?text=Error+Img`;

            slide.innerHTML = `
                <div class="project-card">
                    <img src="${project.imageUrl || fallbackImg}" alt="Vista previa de ${project.title}" onerror="this.src='${fallbackImg}'">
                    <div class="project-card-content">
                        <h3>${project.title}</h3>
                        <p>${project.description}</p>
                        <button class="btn btn-secondary view-project-btn">
                            Ver Proyecto
                        </button>
                    </div>
                </div>
            `;
            
            slide.querySelector('.view-project-btn').addEventListener('click', () => {
                projectDetailsTitle.textContent = project.title;

                // Primero, resetear todo - ocultar ambos contenedores
                projectPreviewContainer.classList.remove('active');
                projectCodeContainer.classList.remove('active');

                projectPreviewIframe.srcdoc = ""; 
                projectPreviewIframe.src = "about:blank"; 

                const code = project.codeSnippet || "";
                const url = project.projectUrl || "#";

                const isFullHtml = code.trim().toLowerCase().startsWith('<!doctype html>') || 
                                   code.trim().toLowerCase().startsWith('<html>');

                if (isFullHtml) {
                    const scriptToNeutralizeLinks = `
                        <script>
                            document.addEventListener('DOMContentLoaded', function() {
                                document.querySelectorAll('a[href^="#"]').forEach(link => {
                                    link.addEventListener('click', function(event) {
                                        event.preventDefault(); 
                                        console.log('Enlace de ancla bloqueado en previsualización: ' + link.getAttribute('href'));
                                    });
                                });
                            });
                        <\/script> 
                    `; 
                    
                    projectPreviewIframe.srcdoc = code.replace(/<\/body>/i, scriptToNeutralizeLinks + '</body>');
                } else {
                    if (url !== "#" && url !== "") {
                         projectPreviewIframe.src = url;
                    } else {
                        projectPreviewIframe.srcdoc = `<body style="font-family: Poppins, sans-serif; color: #a0a0b5; background: #0f0f1a; padding: 2rem; text-align: center;"><h2>Sin previsualización ejecutable</h2><p>Este proyecto es un fragmento de código o no tiene una URL de previsualización en vivo.</p><p>Puedes ver el código en la pestaña 'Código'.</p></body>`;
                    }
                }

                projectCodeBlock.textContent = code;
                
                if (hljs) { 
                    hljs.highlightElement(projectCodeBlock);
                }

                // Resetear todas las pestañas primero
                projectDetailsTabs.forEach(t => t.classList.remove('active'));
                
                // Activar solo la pestaña de "Previsualización"
                const previewTab = document.querySelector('#projectDetailsTabs .modal-tab[data-tab="preview"]');
                if (previewTab) {
                    previewTab.classList.add('active');
                }
                
                // Mostrar SOLO el contenedor de previsualización
                projectPreviewContainer.classList.add('active');

                openModal('projectDetailsModal');
            });


            frag.appendChild(slide);
        });
        swiperWrapper.appendChild(frag);

        if (swiperInstance) {
            swiperInstance.destroy(true, true); 
        }
        swiperInstance = new Swiper('.mySwiper', {
            loop: swiperWrapper.querySelectorAll('.swiper-slide').length > 2,
            grabCursor: true,
            slidesPerView: 1,
            spaceBetween: 30,
            speed: 600,
            autoplay: {
                delay: 3000,
                disableOnInteraction: false,
            },

            breakpoints: {
                768: {
                    slidesPerView: 2,
                    spaceBetween: 30
                },
                1024: {
                    slidesPerView: 3,
                    spaceBetween: 30
                }
            },

            pagination: {
                el: '.swiper-pagination',
                clickable: true,
            },
        });
    }

    function updateProjectsLoadMoreSlide() {
        const existing = swiperWrapper.querySelector('.load-more-slide');
        if (existing) existing.remove();
        if (!projectsPaging.hasMore) return;
        const slide = document.createElement('div');
        slide.classList.add('swiper-slide', 'load-more-slide');
        slide.innerHTML = `
            <div class="project-card">
                <div class="project-card-content" style="text-align:center;">
                    <h3>Cargar más</h3>
                    <button class="btn btn-secondary load-more-projects-btn">Ver más proyectos</button>
                </div>
            </div>
        `;
        slide.querySelector('.load-more-projects-btn').addEventListener('click', async () => {
            if (projectsPaging.loading) return;
            projectsPaging.offset += projectsPaging.limit;
            await fetchProjectsFromDB(false);
        });
        swiperWrapper.appendChild(slide);
        if (swiperInstance) {
            swiperInstance.update();
        }
    }
    
    fetchProjectsFromDB();

    // --- Lógica de Formularios (Login/Registro) ---
    const showError = (message) => {
        errorMessage.textContent = message;
        errorMessage.style.display = 'block';
    };

    document.getElementById('loginForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        errorMessage.style.display = 'none';
        const email = document.getElementById('loginEmail').value;
        const password = document.getElementById('loginPassword').value;
        
        try {
            const res = await fetch('/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, password })
            });
            const data = await res.json();
            if (res.ok) {
                window.location.href = '/chat'; 
            } else {
                showError(data.error || 'Error desconocido.');
            }
        } catch (err) { showError('Error de conexión con el servidor.'); }
    });
    
    document.getElementById('registerForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        errorMessage.style.display = 'none';
        const email = document.getElementById('registerEmail').value;
        const password = document.getElementById('registerPassword').value;
        const confirm = document.getElementById('registerConfirmPassword').value;
        
        if (password !== confirm) {
            showError('Las contraseñas no coinciden.');
            return;
        }

        try {
            const res = await fetch('/register', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, password })
            });
            const data = await res.json();
            if (res.ok) {
                window.location.href = '/chat';
            } else {
                showError(data.error || 'Error desconocido.');
            }
        } catch (err) { showError('Error de conexión con el servidor.'); }
    });

    // --- Mostrar error en URL (ej. ?error=oauth_failed) ---
    const urlParams = new URLSearchParams(window.location.search);
    const urlError = urlParams.get('error');
    if (urlError) {
        const messages = {
            google_not_configured: 'Inicio con Google no está configurado. Usa email y contraseña.',
            oauth_failed: 'Error al iniciar sesión con Google. Intenta de nuevo o usa email.',
            invalid_google_user: 'No se pudo obtener tu información de Google.',
            service_unavailable: 'Servicio no disponible. Intenta más tarde.',
            create_failed: 'No se pudo crear la cuenta. Intenta más tarde.'
        };
        const msg = messages[urlError] || 'Ha ocurrido un error.';
        authBtn.click();
        setTimeout(() => {
            errorMessage.textContent = msg;
            errorMessage.style.display = 'block';
        }, 300);
        window.history.replaceState({}, '', window.location.pathname);
    }

    // --- Animación de Scroll ---
    const faders = document.querySelectorAll('.fade-in');
    const appearOnScroll = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (!entry.isIntersecting) return;
            entry.target.classList.add('visible');
            observer.unobserve(entry.target);
        });
    }, { threshold: 0.1, rootMargin: "0px 0px -50px 0px" });
    faders.forEach(fader => appearOnScroll.observe(fader));
});