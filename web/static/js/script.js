document.addEventListener('DOMContentLoaded', function () {
    const chatForm = document.getElementById('chat-form');
    const chatInput = document.getElementById('chat-input');
    const chatMessages = document.getElementById('chat-messages');
    const sendBtn = document.getElementById('send-btn');
    const modal = document.getElementById('preview-modal');
    const closeModalBtn = document.getElementById('close-modal');
    const runnerFrame = document.getElementById('runner-frame');

    // Inicializa markdown-it
    const md = window.markdownit({
        highlight: function (str, lang) {
            if (lang && hljs.getLanguage(lang)) {
                try {
                    return '<pre><code class="hljs ' + lang + '">' +
                           hljs.highlight(str, { language: lang, ignoreIllegals: true }).value +
                           '</code></pre>';
                } catch (__) {}
            }
            return '<pre><code class="hljs">' + md.utils.escapeHtml(str) + '</code></pre>';
        }
    });

    // --- MANEJO DEL FORMULARIO DE CHAT ---

    chatForm.addEventListener('submit', async function(event) {
        // **FIX**: Previene la recarga de la página, que es el comportamiento por defecto del formulario.
        event.preventDefault();

        const userMessage = chatInput.value.trim();
        if (!userMessage) return;

        // Limpia el input y deshabilita el botón
        chatInput.value = '';
        sendBtn.disabled = true;

        // Muestra el mensaje del usuario
        appendMessage(userMessage, 'user');

        // Muestra el indicador de "escribiendo..."
        appendMessage('<div class="typing-indicator"><span></span><span></span><span></span></div>', 'bot', true);

        try {
            const response = await fetch('/api/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ prompt: userMessage }),
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Error en la respuesta del servidor.');
            }

            const data = await response.json();
            
            // Reemplaza el indicador de "escribiendo..." con la respuesta real
            updateLastBotMessage(data.response);

        } catch (error) {
            console.error('Error al contactar la API:', error);
            updateLastBotMessage(`Lo siento, ocurrió un error: ${error.message}`);
        } finally {
            // Habilita el botón de nuevo
            sendBtn.disabled = false;
        }
    });

    // --- FUNCIONES AUXILIARES ---

    /**
     * Añade un mensaje al contenedor del chat.
     * @param {string} text - El contenido del mensaje (puede ser HTML).
     * @param {string} sender - 'user' o 'bot'.
     * @param {boolean} isTyping - Si es el indicador de "escribiendo".
     */
    function appendMessage(text, sender, isTyping = false) {
        const messageElement = document.createElement('div');
        messageElement.classList.add('message', `${sender}-message`);
        
        if (isTyping) {
            messageElement.innerHTML = text; // Inserta el HTML del indicador
            messageElement.id = 'typing-indicator-msg';
        } else if (sender === 'bot') {
            // Renderiza la respuesta como Markdown
            messageElement.innerHTML = md.render(text);
        } else {
            messageElement.textContent = text;
        }
        
        chatMessages.appendChild(messageElement);
        chatMessages.scrollTop = chatMessages.scrollHeight; // Auto-scroll
    }

    /**
     * Actualiza el último mensaje del bot (reemplaza el "escribiendo..." por la respuesta).
     * @param {string} text - El nuevo contenido del mensaje.
     */
    function updateLastBotMessage(text) {
        let typingIndicator = document.getElementById('typing-indicator-msg');
        if (typingIndicator) {
            typingIndicator.innerHTML = md.render(text);
            // Agrega el botón de previsualizar si hay un bloque de código HTML
            addPreviewButtonIfNeeded(typingIndicator);
            typingIndicator.removeAttribute('id'); // Ya no es el indicador
        }
    }
    
    /**
     * Añade un botón de "Previsualizar" a un mensaje si contiene código HTML.
     * @param {HTMLElement} messageElement - El elemento del mensaje del bot.
     */
    function addPreviewButtonIfNeeded(messageElement) {
        const codeBlock = messageElement.querySelector('code.html, code.language-html');
        if (codeBlock) {
            const previewBtn = document.createElement('button');
            previewBtn.textContent = 'Previsualizar Código';
            previewBtn.className = 'preview-btn';
            previewBtn.onclick = () => {
                // El contenido del código ya está decodificado por highlight.js
                const codeToRun = codeBlock.innerText;
                runnerFrame.srcdoc = codeToRun;
                modal.style.display = 'flex';
            };
            messageElement.appendChild(previewBtn);
        }
    }

    // --- MANEJO DEL MODAL ---
    closeModalBtn.addEventListener('click', () => {
        modal.style.display = 'none';
        runnerFrame.srcdoc = ''; // Limpia el iframe
    });

    window.addEventListener('click', (event) => {
        if (event.target == modal) {
            modal.style.display = 'none';
            runnerFrame.srcdoc = ''; // Limpia el iframe
        }
    });
});

