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

    // 6. Donation appeal picker -> detail modal chain
    var appealPickerModalEl = document.getElementById('appealPickerModal');
    var appealDetailModalEl = document.getElementById('appealDetailModal');

    function populateAppealDetailModal(data) {
        var titleEl = document.getElementById('appealDetailTitle');
        var contentEl = document.getElementById('appealDetailContent');
        if (titleEl) titleEl.textContent = data.title;
        if (contentEl) contentEl.innerHTML = data.content;

        var imgEl = document.getElementById('appealDetailImg');
        var imgErrorEl = document.getElementById('appealDetailImgError');
        if (imgEl && imgErrorEl) {
            if (data.image) {
                imgEl.src = data.image;
                imgEl.classList.remove('d-none');
                imgErrorEl.classList.add('d-none');
                imgEl.onerror = function () {
                    imgEl.classList.add('d-none');
                    imgErrorEl.classList.remove('d-none');
                };
            } else {
                imgEl.removeAttribute('src');
                imgEl.classList.add('d-none');
                imgErrorEl.classList.remove('d-none');
            }
        }

        // Setup story-style progress indicators and image clicking slider
        var progressContainer = document.getElementById('appealDetailProgressIndicators');
        var images = [data.image, data.image2, data.image3, data.image4].filter(Boolean);
        var currentImgIdx = 0;

        function updateSliderImage() {
            if (images.length === 0) return;
            imgEl.src = images[currentImgIdx];
            if (progressContainer) {
                var indicators = progressContainer.querySelectorAll('.slider-bar-indicator');
                indicators.forEach(function (indicator, idx) {
                    if (idx === currentImgIdx) {
                        indicator.style.backgroundColor = '#198754'; // Active green bar
                    } else {
                        indicator.style.backgroundColor = 'rgba(255, 255, 255, 0.4)'; // Inactive translucent white
                    }
                });
            }
        }

        if (progressContainer) {
            progressContainer.innerHTML = '';
            if (images.length > 1) {
                images.forEach(function (_, idx) {
                    var bar = document.createElement('div');
                    bar.className = 'slider-bar-indicator flex-grow-1';
                    bar.style.height = '4px';
                    bar.style.borderRadius = '2px';
                    bar.style.backgroundColor = idx === 0 ? '#198754' : 'rgba(255, 255, 255, 0.4)';
                    bar.style.transition = 'background-color 0.2s ease';
                    progressContainer.appendChild(bar);
                });
                progressContainer.classList.remove('d-none');
            } else {
                progressContainer.classList.add('d-none');
            }
        }

        if (imgEl && images.length > 1) {
            // Recreate image element to clear previous click listeners
            var newImgEl = imgEl.cloneNode(true);
            imgEl.parentNode.replaceChild(newImgEl, imgEl);
            imgEl = newImgEl;

            imgEl.addEventListener('click', function (e) {
                var rect = imgEl.getBoundingClientRect();
                var clickX = e.clientX - rect.left;
                // Click left 40% goes to previous image, right 60% goes to next image
                if (clickX < rect.width * 0.4) {
                    currentImgIdx = (currentImgIdx - 1 + images.length) % images.length;
                } else {
                    currentImgIdx = (currentImgIdx + 1) % images.length;
                }
                updateSliderImage();
            });
        }

        var suppliesWrap = document.getElementById('appealDetailSuppliesWrap');
        var suppliesEl = document.getElementById('appealDetailSupplies');
        if (suppliesEl && suppliesWrap) {
            suppliesEl.innerHTML = '';
            if (data.supplies && data.supplies.length > 0) {
                data.supplies.forEach(function (item) {
                    var col = document.createElement('div');
                    col.className = 'col-md-6 d-flex align-items-center gap-2 small mb-2';
                    col.innerHTML = '<i class="bi bi-check-circle-fill text-success" style="font-size: 1.15rem; color: #198754 !important;"></i> <span class="text-dark"><strong>' +
                        item.name + '</strong> &ndash; ' + item.quantity + ' ' + item.unit + '</span>';
                    suppliesEl.appendChild(col);
                });
                suppliesWrap.classList.remove('d-none');
            } else {
                suppliesWrap.classList.add('d-none');
            }
        }

        var appealDonateCampaignIdInput = document.getElementById('appealDonateCampaignId');
        if (appealDonateCampaignIdInput) appealDonateCampaignIdInput.value = data.campaignId;

        var appealDonateForm = document.getElementById('appealDonateForm');
        if (appealDonateForm) {
            appealDonateForm.action = '/donate/appeal/' + data.appealId + '/';
        }

        // Reset the amount picker back to the default preset each time a new story opens
        var defaultAmount = 500;
        var appealDonateAmountInput = document.getElementById('appealDonateAmount');
        if (appealDonateAmountInput) appealDonateAmountInput.value = defaultAmount;
        
        var cards = document.querySelectorAll('#appealAmountPills .hr-amount-card');
        cards.forEach(function (card) {
            card.classList.toggle('active', parseInt(card.getAttribute('data-amount'), 10) === defaultAmount);
        });
    }

    function openAppealById(appealId) {
        if (!appealDetailModalEl) return;
        var link = document.querySelector(`.appeal-picker-link[data-appeal-id="${appealId}"]`);
        if (!link) return;

        var supplies = [];
        try {
            supplies = JSON.parse(link.getAttribute('data-appeal-supplies') || '[]');
        } catch (e) {
            supplies = [];
        }

        var data = {
            appealId: link.getAttribute('data-appeal-id') || '',
            title: link.getAttribute('data-appeal-title') || '',
            content: link.getAttribute('data-appeal-content') || '',
            image: link.getAttribute('data-appeal-image') || '',
            image2: link.getAttribute('data-appeal-image2') || '',
            image3: link.getAttribute('data-appeal-image3') || '',
            image4: link.getAttribute('data-appeal-image4') || '',
            campaignId: link.getAttribute('data-appeal-campaign-id') || '',
            supplies: supplies,
        };

        populateAppealDetailModal(data);
        var detailModal = bootstrap.Modal.getOrCreateInstance(appealDetailModalEl);
        if (detailModal) detailModal.show();
    }

    if (appealPickerModalEl) {
        appealPickerModalEl.addEventListener('click', function (event) {
            var link = event.target.closest('.appeal-picker-link');
            if (!link) return;

            var appealId = link.getAttribute('data-appeal-id');
            var pickerModal = bootstrap.Modal.getOrCreateInstance(appealPickerModalEl);
            if (pickerModal) pickerModal.hide();

            openAppealById(appealId);
        });
    }

    // Auto-open appeal detail modal if 'appeal' parameter is in the URL query string
    var urlParams = new URLSearchParams(window.location.search);
    var appealIdParam = urlParams.get('appeal');
    if (appealIdParam) {
        setTimeout(function() {
            openAppealById(appealIdParam);
        }, 400);
    }

    // ---- Appeal donate amount cards ----
    var appealAmountPills = document.getElementById('appealAmountPills');
    var appealDonateAmountInput = document.getElementById('appealDonateAmount');
    if (appealAmountPills && appealDonateAmountInput) {
        appealAmountPills.addEventListener('click', function (event) {
            var card = event.target.closest('.hr-amount-card');
            if (!card) return;
            appealAmountPills.querySelectorAll('.hr-amount-card').forEach(function (c) {
                c.classList.remove('active');
            });
            card.classList.add('active');
            appealDonateAmountInput.value = card.getAttribute('data-amount');
        });
        appealDonateAmountInput.addEventListener('input', function () {
            appealAmountPills.querySelectorAll('.hr-amount-card').forEach(function (c) {
                c.classList.toggle('active', c.getAttribute('data-amount') === appealDonateAmountInput.value);
            });
        });
    }

    // 7. Story Detail Modal — populate from data attributes
    const storyDetailModal = document.getElementById('storyDetailModal');
    if (storyDetailModal) {
        const storyImg = document.getElementById('storyDetailImg');
        const storyImgError = document.getElementById('storyDetailImgError');
        const storyAvatar = document.getElementById('storyDetailAvatar');

        storyDetailModal.addEventListener('show.bs.modal', function (event) {
            const button = event.relatedTarget;
            const name = button.dataset.testimonialName || '';
            const role = button.dataset.testimonialRole || '';
            const title = button.dataset.testimonialTitle || '';
            const message = button.dataset.testimonialMessage || '';
            const rating = parseInt(button.dataset.testimonialRating) || 0;
            const category = button.dataset.testimonialCategory || '';
            const photoUrl = button.dataset.testimonialPhoto || '';
            const hasPhoto = button.dataset.testimonialHasPhoto === 'true';

            const nameEl = document.getElementById('storyDetailName');
            const roleEl = document.getElementById('storyDetailRole');
            const titleEl = document.getElementById('storyDetailTitle');
            const messageEl = document.getElementById('storyDetailMessage');
            const categoryEl = document.getElementById('storyDetailCategory');
            const ratingEl = document.getElementById('storyDetailRating');

            if (nameEl) nameEl.textContent = name;
            if (roleEl) roleEl.textContent = role;
            if (titleEl) titleEl.textContent = title;
            if (messageEl) messageEl.textContent = message;
            if (categoryEl) categoryEl.textContent = category;

            if (ratingEl) {
                ratingEl.innerHTML = '';
                for (let i = 1; i <= 5; i++) {
                    const star = document.createElement('i');
                    star.className = 'bi ' + (i <= rating ? 'bi-star-fill' : 'bi-star') + ' text-warning';
                    ratingEl.appendChild(star);
                }
                const ratingSpan = document.createElement('span');
                ratingSpan.className = 'text-muted small ms-1';
                ratingSpan.textContent = rating + '.0';
                ratingEl.appendChild(ratingSpan);
            }

            if (storyAvatar) {
                if (hasPhoto && photoUrl) {
                    storyAvatar.innerHTML = '<img src="' + photoUrl + '" alt="' + name + '">';
                } else {
                    const avatarInitial = name ? name.charAt(0).toUpperCase() : '?';
                    storyAvatar.innerHTML = '<img src="https://ui-avatars.com/api/?name=' + encodeURIComponent(avatarInitial) + '&background=26e07f&color=fff&size=96&bold=true" alt="' + name + '">';
                }
            }

            if (storyImg && storyImgError) {
                if (hasPhoto && photoUrl) {
                    storyImg.src = photoUrl;
                    storyImg.style.display = 'block';
                    storyImgError.classList.add('d-none');
                } else {
                    storyImg.style.display = 'none';
                    storyImgError.classList.remove('d-none');
                }
            }
        });

        storyDetailModal.addEventListener('hidden.bs.modal', function () {
            if (storyImg) {
                storyImg.style.display = 'block';
                storyImgError.classList.add('d-none');
                storyImg.src = 'data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7';
            }
            if (storyAvatar) {
                storyAvatar.innerHTML = '';
            }
        });

        if (storyImg) {
            storyImg.addEventListener('error', function () {
                storyImg.style.display = 'none';
                storyImgError.classList.remove('d-none');
            });
        }
    }

    // ---- Bootstrap 5 Form Client-side Validation ----
    var validationForms = document.querySelectorAll('.needs-validation');
    validationForms.forEach(function (form) {
        form.addEventListener('submit', function (event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        }, false);
    });
});
