document.addEventListener('DOMContentLoaded', () => {
    // Reveal Observer for smooth scroll animations
    const revealOptions = {
        threshold: 0.15,
        rootMargin: "0px 0px -50px 0px"
    };

    const revealObserver = new IntersectionObserver(function(entries, observer) {
        entries.forEach(entry => {
            if (!entry.isIntersecting) {
                return;
            } else {
                entry.target.classList.add('active');
                observer.unobserve(entry.target);
            }
        });
    }, revealOptions);

    const reveals = document.querySelectorAll('.reveal');
    reveals.forEach(reveal => {
        revealObserver.observe(reveal);
    });

    // Navbar scroll effect
    const navbar = document.querySelector('.navbar');
    window.addEventListener('scroll', () => {
        if (window.scrollY > 50) {
            navbar.classList.add('scrolled');
        } else {
            navbar.classList.remove('scrolled');
        }
    });

    // Usecase Dictionary Database
    const usecases = {
        support: {
            title: 'Customer Support',
            history: [
                { role: 'user', text: 'I have a new phone number: 555-346-0123' },
                { role: 'system', text: 'Updated your contact information with the new number.' }
            ],
            trigger: 'My internet is slow again',
            targetResponse: 'I see this is the third time this month with your Netgear router. Let me run targeted diagnostics.',
            memories: [
                { text: 'Contact number is 555-0123', tag: 'Contact', date: 'Just now' },
                { text: 'Is a premium plan customer with Netgear hardware', tag: 'Account', date: '1 Jan, 2021', isTarget: true }
            ]
        },
        health: {
            title: 'Healthcare',
            history: [
                { role: 'user', text: 'Im feeling a bit fatigued lately.' },
                { role: 'system', text: 'Logged into your daily journal.' }
            ],
            trigger: 'What supplements should I take?',
            targetResponse: 'Based on your history of Iron deficiency, I recommend considering iron and vitamin C supplements.',
            memories: [
                { text: 'Patient reports recent fatigue', tag: 'Journal', date: '2 days ago' },
                { text: 'Diagnosed with Iron Deficiency', tag: 'Medical', date: 'Aug 2024', isTarget: true }
            ]
        },
        edu: {
            title: 'Education',
            history: [
                { role: 'user', text: 'I finally finished the calculus module.' },
                { role: 'system', text: 'Great job! I have updated your progress.' }
            ],
            trigger: 'Give me a practice problem for today.',
            targetResponse: 'Since you struggled with Integration by Parts yesterday, try this integral: ∫ x cos(x) dx',
            memories: [
                { text: 'Finished Calculus Module 1', tag: 'Progress', date: 'Yesterday' },
                { text: 'Struggled with Integration by Parts concepts', tag: 'Analytics', date: 'Yesterday', isTarget: true }
            ]
        },
        sales: {
            title: 'Sales & CRM',
            history: [
                { role: 'user', text: 'Had a great call with Acme Corp.' },
                { role: 'system', text: 'Notes saved to Acme Corp profile.' }
            ],
            trigger: 'Draft a follow-up email to them.',
            targetResponse: 'Certainly. I will mention their Q3 scale-up initiative that you discussed yesterday.',
            memories: [
                { text: 'Acme Corp call completed', tag: 'Activity', date: 'Yesterday' },
                { text: 'Acme Corp is prioritizing Q3 AI scale-up', tag: 'Notes', date: 'Yesterday', isTarget: true }
            ]
        },
        ecom: {
            title: 'E Commerce',
            history: [
                { role: 'user', text: 'I liked those blue running shoes.' },
                { role: 'system', text: 'Added to your favorites list.' }
            ],
            trigger: 'Recommend me some workout clothes.',
            targetResponse: 'I recommend the Aero-Fit shorts; they pair perfectly with the blue running shoes you like.',
            memories: [
                { text: 'Bought size M cotton t-shirts', tag: 'Purchase', date: '2 mths ago' },
                { text: 'Favorited blue running shoes', tag: 'Preference', date: '1 mth ago', isTarget: true }
            ]
        }
    };

    let activeUsecase = 'support';
    let animationTimeout = null;
    let timingArr = [];
    let typingInterval = null;
    let lineUpdateFrame = null;

    const chatContainer = document.getElementById('chatMessages');
    const memContainer = document.getElementById('dynamicMemories');
    const titleEl = document.getElementById('dynamicUsecaseTitle');
    const startBtn = document.getElementById('startDemoBtn');
    const svgPath = document.getElementById('animPath');
    const svgLine = document.getElementById('connectionLine');
    const tabs = document.querySelectorAll('.tab-btn');

    function updateSVGPath() {
        const triggerMsg = document.getElementById('triggerMsg');
        const targetMemory = document.getElementById('targetMemory');
        const container = document.querySelector('.demo-ui-wrapper');
        
        if(triggerMsg && targetMemory && container && svgPath) {
            const fromRect = triggerMsg.getBoundingClientRect();
            const toRect = targetMemory.getBoundingClientRect();
            const containerRect = container.getBoundingClientRect();
            
            const startX = fromRect.right - containerRect.left;
            const startY = fromRect.top + (fromRect.height / 2) - containerRect.top;
            
            const endX = toRect.left - containerRect.left;
            const endY = toRect.top + (toRect.height / 2) - containerRect.top;
            
            const controlX = startX + (endX - startX) / 2;
            svgPath.setAttribute('d', `M ${startX} ${startY} C ${controlX} ${startY}, ${controlX} ${endY}, ${endX} ${endY}`);
        }
        lineUpdateFrame = requestAnimationFrame(updateSVGPath);
    }

    function loadUsecase(id) {
        activeUsecase = id;
        const data = usecases[id];
        
        // Reset Visuals and Timeouts
        clearTimeout(animationTimeout);
        timingArr.forEach(t => clearTimeout(t));
        timingArr = [];
        clearInterval(typingInterval);
        if(lineUpdateFrame) cancelAnimationFrame(lineUpdateFrame);
        
        if (svgLine) svgLine.style.display = 'none';
        if (svgPath) {
            svgPath.style.animation = 'none';
            svgPath.style.opacity = '1';
        }
        if (startBtn) {
            startBtn.disabled = false;
            startBtn.style.opacity = '1';
            startBtn.innerText = 'Run Agent Workflow';
        }
        if (titleEl) titleEl.innerText = `Usecase: ${data.title}`;
        
        // Render Chat HTML
        if (chatContainer) {
            chatContainer.innerHTML = '';
            data.history.forEach(msg => {
                chatContainer.innerHTML += `<div class="message ${msg.role}-msg"><p>${msg.text}</p></div>`;
            });
            chatContainer.innerHTML += `
                <div class="message user-msg hidden-msg" id="triggerMsg">
                    <p>${data.trigger}</p>
                </div>
                <div class="message system-msg hidden-msg" id="responseMsg">
                    <p id="responseText"></p>
                </div>
            `;
        }
        
        // Render Memories
        if (memContainer) {
            memContainer.innerHTML = '';
            data.memories.forEach((mem, idx) => {
                memContainer.innerHTML += `
                    <div class="memory-card" id="${mem.isTarget ? 'targetMemory' : 'mem_'+idx}">
                        <p class="memory-text">${mem.text}</p>
                        <div class="memory-meta">
                            <span class="tag tag-blue">${mem.tag}</span>
                            <span class="date">${mem.date}</span>
                        </div>
                    </div>
                `;
            });
        }
        
        // Active Class on Tabs
        tabs.forEach(t => t.classList.remove('active'));
        const activeTab = document.querySelector(`.tab-btn[data-id="${id}"]`);
        if(activeTab) activeTab.classList.add('active');
    }

    // Initialize System
    if(chatContainer && memContainer) {
        loadUsecase('support');
        
        tabs.forEach(tab => {
            tab.addEventListener('click', (e) => {
                loadUsecase(e.target.getAttribute('data-id'));
            });
        });

        // Top Navigation Dropdown mapping
        const dropdownLinks = document.querySelectorAll('.dropdown-link');
        dropdownLinks.forEach(link => {
            link.addEventListener('click', (e) => {
                const targetId = e.currentTarget.getAttribute('data-id');
                loadUsecase(targetId);
            });
        });

        startBtn.addEventListener('click', () => {
            if(startBtn.disabled) return;
            startBtn.disabled = true;
            startBtn.style.opacity = '0.5';
            startBtn.innerText = 'Retrieving...';
            
            const triggerMsg = document.getElementById('triggerMsg');
            const targetMemory = document.getElementById('targetMemory');
            const responseMsg = document.getElementById('responseMsg');
            const responseText = document.getElementById('responseText');
            const containerRect = document.querySelector('.demo-ui-wrapper').getBoundingClientRect();
            
            const data = usecases[activeUsecase];

            // 1. Show User Input Trigger
            triggerMsg.classList.add('show');
            
            animationTimeout = setTimeout(() => {
                // 2. Start tracking dynamic math SVG via Animation Frame
                if(lineUpdateFrame) cancelAnimationFrame(lineUpdateFrame);
                updateSVGPath();
                
                svgLine.style.display = 'block';
                void svgPath.offsetWidth; // Reflow reset SVG
                svgPath.style.animation = 'drawPath 0.8s forwards ease-in-out';
                
                timingArr.push(setTimeout(() => {
                    // 3. Highlight relevant memory
                    targetMemory.classList.add('highlight-pulse');
                    
                    timingArr.push(setTimeout(() => {
                        // 4. Begin Typing Response
                        responseMsg.classList.add('show');
                        responseMsg.classList.add('typing-cursor');
                        responseText.innerText = '';
                        svgPath.style.opacity = '0.2';
                        
                        let charIdx = 0;
                        let currentStr = '';
                        const fullText = data.targetResponse;
                        startBtn.innerText = 'Synthesizing...';
                        
                        typingInterval = setInterval(() => {
                            currentStr += fullText.charAt(charIdx);
                            responseText.textContent = currentStr;
                            charIdx++;
                            if(charIdx >= fullText.length) {
                                clearInterval(typingInterval);
                                responseMsg.classList.remove('typing-cursor');
                                targetMemory.classList.remove('highlight-pulse');
                                targetMemory.style.borderColor = 'rgba(59, 130, 246, 0.4)';
                                startBtn.innerText = 'Workflow Complete';
                            }
                        }, 25);
                        
                    }, 800));
                }, 800));
            }, 600);
        });
    }
});
