// script.js — HopeRise Rich Micro-Interactions & JS Animations

document.addEventListener('DOMContentLoaded', function () {
    
    // 1. Navbar Glassmorphic Blur on Scroll
    const navbar = document.querySelector('.hr-navbar');
    if (navbar) {
        window.addEventListener('scroll', function () {
            if (window.scrollY > 30) {
                navbar.classList.add('scrolled');
            } else {
                navbar.classList.remove('scrolled');
            }
        });
    }

    // 2. Interactive Treatment Stage Pills (Get Help Form)
    const stagePills = document.querySelectorAll('.hr-stage-pill');
    stagePills.forEach(pill => {
        pill.addEventListener('click', function () {
            stagePills.forEach(p => p.classList.remove('active'));
            this.classList.add('active');
        });
    });

    // 3. Scroll Reveal Observer (with a staggered delay per sibling for a nicer cascade)
    const revealGroups = document.querySelectorAll('.row.g-4, .hr-section');
    revealGroups.forEach(group => {
        const items = group.querySelectorAll(':scope > .hr-card-beige, :scope > .hr-card-white, :scope .hr-story-card, .hr-gethelp-card, .hr-section h2');
        items.forEach((el, i) => {
            el.classList.add('reveal-on-scroll');
            el.style.transitionDelay = Math.min(i * 90, 360) + 'ms';
        });
    });

    const revealElements = document.querySelectorAll('.hr-card-beige, .hr-card-white, .hr-story-card, .hr-gethelp-card, .hr-section h2');
    revealElements.forEach(el => el.classList.add('reveal-on-scroll'));

    const observer = new IntersectionObserver((entries, obs) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('revealed');
                obs.unobserve(entry.target);
            }
        });
    }, { threshold: 0.15 });

    revealElements.forEach(el => observer.observe(el));

    // 4. Counter Animation for Impact Number (Counts up to target value)
    const impactNum = document.querySelector('.hr-impact-number');
    if (impactNum) {
        let counted = false;
        const targetStr = impactNum.textContent.trim();
        const targetVal = parseInt(targetStr.replace(/[^0-9]/g, '')) || 215;
        const prefix = targetStr.replace(/[0-9]/g, '');

        const counterObserver = new IntersectionObserver((entries) => {
            if (entries[0].isIntersecting && !counted) {
                counted = true;
                let current = 0;
                const duration = 1800; // ms
                const increment = Math.ceil(targetVal / (duration / 16));

                const timer = setInterval(() => {
                    current += increment;
                    if (current >= targetVal) {
                        current = targetVal;
                        clearInterval(timer);
                    }
                    impactNum.textContent = current + prefix;
                }, 16);
            }
        }, { threshold: 0.5 });

        counterObserver.observe(impactNum);
    }

    // 4b. Progress Bar Animation (grow width on scroll-into-view)
    const progressBars = document.querySelectorAll('.hr-progress-bar');
    progressBars.forEach(bar => {
        const progressWidth = bar.style.width;
        bar.style.width = '0';
        const progressObserver = new IntersectionObserver((entries) => {
            if (entries[0].isIntersecting) {
                bar.style.width = progressWidth;
                progressObserver.unobserve(bar);
            }
        }, { threshold: 0.5 });
        progressObserver.observe(bar);
    });

    // 5. News & Stories Arrow Navigation
    const newsCards = document.querySelectorAll('.hr-section .row .col-lg-3 .hr-story-card');
    const prevArrow = document.querySelector('.bi-arrow-left')?.parentElement;
    const nextArrow = document.querySelector('.bi-arrow-right')?.parentElement;

    if (newsCards.length > 0 && nextArrow) {
        let activeIdx = 0;
        nextArrow.addEventListener('click', () => {
            newsCards[activeIdx].style.transform = 'scale(0.95)';
            activeIdx = (activeIdx + 1) % newsCards.length;
            newsCards[activeIdx].style.transform = 'scale(1.05)';
            setTimeout(() => { newsCards.forEach(c => c.style.transform = 'none'); }, 400);
        });

        if (prevArrow) {
            prevArrow.addEventListener('click', () => {
                newsCards[activeIdx].style.transform = 'scale(0.95)';
                activeIdx = (activeIdx - 1 + newsCards.length) % newsCards.length;
                newsCards[activeIdx].style.transform = 'scale(1.05)';
                setTimeout(() => { newsCards.forEach(c => c.style.transform = 'none'); }, 400);
            });
        }
    }

    // 6. Quick Donate Modal — "Choose Amount" popup interactions
    const quickDonateModal = document.getElementById('quickDonateModal');
    if (quickDonateModal) {
        const amountInput = document.getElementById('donateAmountInput');
        const currencySelect = document.getElementById('donateCurrency');
        const pills = document.querySelectorAll('.hr-amount-pill');
        const monthlyToggle = document.getElementById('monthlyToggle');
        const labelOneTime = document.getElementById('labelOneTime');
        const labelMonthly = document.getElementById('labelMonthly');
        const anonymousCheck = document.getElementById('anonymousCheck');
        const nameInput = document.getElementById('donateNameInput');
        const termsCheck = document.getElementById('termsCheck');
        const donateSubmitBtn = document.getElementById('donateSubmitBtn');
        const useQrBtn = document.getElementById('useQrBtn');
        const qrBackBtn = document.getElementById('qrBackBtn');
        const flipInner = document.getElementById('donateFlipInner');
        const qrCodeImg = document.getElementById('qrCodeImg');
        const qrAmountLabel = document.getElementById('qrAmountLabel');
        const qrDoneBtn = document.getElementById('qrDoneBtn');

        // Preset pills fill the amount box and mark themselves active
        pills.forEach(pill => {
            pill.addEventListener('click', () => {
                pills.forEach(p => p.classList.remove('active'));
                pill.classList.add('active');
                amountInput.value = pill.dataset.amount;
            });
        });

        // Typing a custom amount clears any preset selection
        amountInput.addEventListener('input', () => {
            pills.forEach(p => p.classList.remove('active'));
            const match = Array.from(pills).find(p => p.dataset.amount === amountInput.value);
            if (match) match.classList.add('active');
        });

        // Currency select updates the pill labels for consistency
        currencySelect.addEventListener('change', () => {
            pills.forEach(p => {
                p.textContent = currencySelect.value + p.dataset.amount;
            });
        });

        // One-Time / Monthly toggle swaps the emphasis + button label
        monthlyToggle.addEventListener('change', () => {
            const isMonthly = monthlyToggle.checked;
            labelOneTime.classList.toggle('active', !isMonthly);
            labelMonthly.classList.toggle('active', isMonthly);
            donateSubmitBtn.textContent = isMonthly ? 'SUBSCRIBE MONTHLY' : 'DONATE';
        });

        // Donate anonymously collapses the name field smoothly
        anonymousCheck.addEventListener('change', () => {
            nameInput.classList.toggle('is-collapsed', anonymousCheck.checked);
            if (anonymousCheck.checked) nameInput.value = '';
        });

        // Require the Terms checkbox before allowing submission
        termsCheck.addEventListener('change', () => {
            donateSubmitBtn.disabled = !termsCheck.checked;
        });

        function buildCheckoutUrl() {
            const baseUrl = quickDonateModal.dataset.donateUrl || '/donate/';
            const params = new URLSearchParams();
            params.set('amount', amountInput.value || '0');
            if (!anonymousCheck.checked && nameInput.value.trim()) {
                params.set('name', nameInput.value.trim());
            }
            return baseUrl + '?' + params.toString();
        }

        // DONATE -> hand off to the full checkout flow (email + payment method)
        donateSubmitBtn.addEventListener('click', () => {
            if (donateSubmitBtn.disabled) return;
            window.location.href = buildCheckoutUrl();
        });

        // USE QR CODE -> 3D-flip the card to a scannable QR face
        useQrBtn.addEventListener('click', () => {
            const amount = amountInput.value || '0';
            const currency = currencySelect.value;
            qrCodeImg.src = 'https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=' +
                encodeURIComponent('upi://pay?pa=helpinghands@upi&pn=HopeRise&am=' + amount);
            qrAmountLabel.textContent = currency + ' ' + amount;
            flipInner.classList.add('is-flipped');
        });

        qrBackBtn.addEventListener('click', () => {
            flipInner.classList.remove('is-flipped');
        });

        qrDoneBtn.addEventListener('click', () => {
            window.location.href = buildCheckoutUrl();
        });

        // Reset to the front face + defaults every time the modal is closed
        quickDonateModal.addEventListener('hidden.bs.modal', () => {
            flipInner.classList.remove('is-flipped');
        });
    }
});
