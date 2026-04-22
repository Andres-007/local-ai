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
    const projectDetailsTitle = document.getElementById('projectDetailsTitle');
    const projectDetailTabs = document.getElementById('projectDetailTabs');
    const projectTabPreview = document.getElementById('projectTabPreview');
    const projectTabCode = document.getElementById('projectTabCode');
    const projectPreviewContainer = document.getElementById('projectPreviewContainer');
    const projectPreviewFrame = document.getElementById('projectPreviewFrame');
    const projectCodeContainer = document.getElementById('projectCodeContainer');
    const projectCodeBlock = document.getElementById('projectCode');
    const swiperWrapper = document.querySelector('#projectsCarousel .swiper-wrapper');

    function escapeHtml(s) {
        return String(s)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    function safeHttpImageUrl(url, fallback) {
        const u = String(url || '').trim();
        if (/^https?:\/\//i.test(u)) return u;
        return fallback;
    }

    function isLikelyHtmlDocument(code) {
        const s = String(code || '').trim();
        if (!s || s.charAt(0) !== '<') return false;
        const head = s.slice(0, 8000).toLowerCase();
        return head.includes('<!doctype html') ||
            /^<\s*html[\s>]/i.test(s) ||
            (head.includes('<html') && head.includes('</html>'));
    }

    function setProjectPreviewSrcdoc(html) {
        const navigationInterceptorScript = `
            <script>
                document.addEventListener('DOMContentLoaded', function() {
                    document.querySelectorAll('a').forEach(function(link) {
                        link.addEventListener('click', function(event) {
                            event.preventDefault();
                        });
                    });
                    document.querySelectorAll('form').forEach(function(form) {
                        form.addEventListener('submit', function(event) {
                            event.preventDefault();
                        });
                    });
                });
            <\/script>
        `;
        const doc = String(html || '');
        if (doc.includes('</body>')) {
            projectPreviewFrame.srcdoc = doc.replace('</body>', navigationInterceptorScript + '</body>');
        } else if (doc.includes('</html>')) {
            projectPreviewFrame.srcdoc = doc.replace('</html>', navigationInterceptorScript + '</html>');
        } else {
            projectPreviewFrame.srcdoc = doc + navigationInterceptorScript;
        }
    }

    function setProjectDetailTab(panel) {
        const isPreview = panel === 'preview';
        projectTabPreview.classList.toggle('active', isPreview);
        projectTabCode.classList.toggle('active', !isPreview);
        projectTabPreview.setAttribute('aria-selected', isPreview ? 'true' : 'false');
        projectTabCode.setAttribute('aria-selected', isPreview ? 'false' : 'true');
        projectPreviewContainer.classList.toggle('active', isPreview);
        projectCodeContainer.classList.toggle('active', !isPreview);
    }

    function resetProjectDetailsModal() {
        projectCodeBlock.textContent = '';
        projectPreviewFrame.removeAttribute('srcdoc');
        projectPreviewFrame.src = 'about:blank';
        projectDetailTabs.classList.remove('is-hidden');
        projectTabPreview.classList.remove('active');
        projectTabCode.classList.remove('active');
        projectPreviewContainer.classList.remove('active');
        projectCodeContainer.classList.remove('active');
    }

    // --- Lógica General de Modales ---
    let scrollYOnModalOpen = 0;

    const openModal = (modalId) => {
        const modal = document.getElementById(modalId);
        if (modal) {
            if (!document.querySelector('.modal-overlay.active')) {
                scrollYOnModalOpen = window.scrollY || window.pageYOffset;
            }
            modal.classList.add('active');
            document.documentElement.classList.add('modal-open');
            document.body.classList.add('modal-open');
        }
    };

    const closeModal = (modalId) => {
        const modal = document.getElementById(modalId);
        if (modal) modal.classList.remove('active');

        if (!document.querySelector('.modal-overlay.active')) {
            document.documentElement.classList.remove('modal-open');
            document.body.classList.remove('modal-open');
            window.scrollTo(0, scrollYOnModalOpen);
        }

        // Limpiar contenido al cerrar modal de proyecto
        if (modalId === 'projectDetailsModal') {
            resetProjectDetailsModal();
        }
    };

    // Evitar que la rueda del ratón en el overlay haga scroll en el fondo
    document.querySelectorAll('.modal-overlay').forEach(function (overlay) {
        overlay.addEventListener('wheel', function (e) {
            if (e.target === overlay) {
                e.preventDefault();
            }
        }, { passive: false });
    });

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

    projectTabPreview.addEventListener('click', () => {
        if (projectDetailTabs.classList.contains('is-hidden')) return;
        setProjectDetailTab('preview');
    });
    projectTabCode.addEventListener('click', () => {
        setProjectDetailTab('code');
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
            const imgSrc = safeHttpImageUrl(project.imageUrl, fallbackImg);
            const t = escapeHtml(String(project.title ?? ''));
            const d = escapeHtml(String(project.description ?? ''));

            slide.innerHTML = `
                <div class="project-card">
                    <img src="${imgSrc}" alt="Vista previa de ${t}" onerror="this.src='${fallbackImg}'">
                    <div class="project-card-content">
                        <h3>${t}</h3>
                        <p>${d}</p>
                        <button class="btn btn-secondary view-project-btn">
                            Ver Proyecto
                        </button>
                    </div>
                </div>
            `;
            
            slide.querySelector('.view-project-btn').addEventListener('click', () => {
                projectDetailsTitle.textContent = project.title;
                const code = project.codeSnippet || "";
                const canPreview = isLikelyHtmlDocument(code);
                projectCodeBlock.textContent = code;
                if (typeof hljs !== 'undefined' && hljs.highlightElement) {
                    hljs.highlightElement(projectCodeBlock);
                }
                if (canPreview) {
                    projectDetailTabs.classList.remove('is-hidden');
                    setProjectPreviewSrcdoc(code);
                    setProjectDetailTab('preview');
                } else {
                    projectDetailTabs.classList.add('is-hidden');
                    projectPreviewFrame.removeAttribute('srcdoc');
                    projectPreviewFrame.src = 'about:blank';
                    setProjectDetailTab('code');
                }
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
        const submitBtn = e.target.querySelector('.form-submit');
        submitBtn.disabled = true;
        submitBtn.textContent = 'Iniciando sesión...';
        try {
            const res = await fetch('/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'same-origin',
                body: JSON.stringify({ email, password })
            });
            const data = await res.json();
            if (res.ok) {
                window.location.replace('/chat');
            } else {
                showError(data.error || 'Error desconocido.');
                submitBtn.disabled = false;
                submitBtn.textContent = 'Iniciar sesión';
            }
        } catch (err) {
            showError('Error de conexión con el servidor.');
            submitBtn.disabled = false;
            submitBtn.textContent = 'Iniciar sesión';
        }
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
        if (password.length < 8) {
            showError('La contraseña debe tener al menos 8 caracteres.');
            return;
        }
        const submitBtn = e.target.querySelector('.form-submit');
        submitBtn.disabled = true;
        submitBtn.textContent = 'Creando cuenta...';
        try {
            const res = await fetch('/register', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'same-origin',
                body: JSON.stringify({ email, password })
            });
            const data = await res.json();
            if (res.ok) {
                window.location.replace('/chat');
            } else {
                showError(data.error || 'Error desconocido.');
                submitBtn.disabled = false;
                submitBtn.textContent = 'Crear cuenta';
            }
        } catch (err) {
            showError('Error de conexión con el servidor.');
            submitBtn.disabled = false;
            submitBtn.textContent = 'Crear cuenta';
        }
    });

    // --- Mostrar error en URL (ej. ?error=oauth_failed) ---
    const urlParams = new URLSearchParams(window.location.search);
    const urlError = urlParams.get('error');
    if (urlError) {
        const messages = {
            github_not_configured: 'Inicio con GitHub no está configurado. Usa email y contraseña.',
            oauth_failed: 'Error al iniciar sesión con GitHub. Intenta de nuevo o usa email.',
            invalid_github_user: 'No se pudo obtener tu información de GitHub.',
            github_email_required: 'Tu cuenta de GitHub debe tener un email visible. Configúralo en GitHub o usa email.',
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
