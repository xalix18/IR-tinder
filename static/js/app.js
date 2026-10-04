/* ==========================================================================
   HAMDAM TELEGRAM MINI APP CLIENT ENGINE
   ========================================================================== */

const tg = window.Telegram?.WebApp;
if (tg) {
    tg.ready();
    tg.expand();
    try {
        tg.setHeaderColor('#0B0E14');
        tg.setBackgroundColor('#0B0E14');
    } catch (e) {}
}

const state = {
    user: null,
    constants: {},
    candidates: [],
    currentIndex: 0,
    filters: { gender: '', city: '', min_age: 18, max_age: 45 },
    selectedInterests: []
};

// --- Initialization ---
document.addEventListener('DOMContentLoaded', async () => {
    setupNavigation();
    setupModals();
    setupSwipeButtons();
    setupProfileForm();
    await loadInitialData();
});

// --- API Request Helper ---
async function apiCall(endpoint, method = 'GET', body = null, isFormData = false) {
    const headers = { 'X-Telegram-Init-Data': tg?.initData || '' };
    const options = { method, headers };

    if (body) {
        if (isFormData) {
            options.body = body;
        } else {
            headers['Content-Type'] = 'application/json';
            options.body = JSON.stringify(body);
        }
    }

    try {
        const res = await fetch(endpoint, options);
        return await res.json();
    } catch (err) {
        showToast('خطا در ارتباط با سرور');
        return { success: false, error: err.message };
    }
}

// --- Load Initial Data ---
async function loadInitialData() {
    const res = await apiCall('/api/init');
    if (!res.success) {
        showToast(res.error || 'خطا در بارگذاری اولیه');
        return;
    }

    state.constants = res.constants;
    state.user = res.user;

    populateFormDropdowns();

    if (!state.user.is_complete) {
        openModal('modal-profile-form');
        document.getElementById('btn-close-profile-modal').classList.add('hidden');
    } else {
        updateMyProfileUI();
        await loadCandidates();
    }
}

// --- Populate Dropdowns ---
function populateFormDropdowns() {
    const citySelect = document.getElementById('input-city');
    const filterCitySelect = document.getElementById('filter-city');
    const goalSelect = document.getElementById('input-goal');
    const eduSelect = document.getElementById('input-education');
    const chipGrid = document.getElementById('interests-chip-grid');

    // Cities
    state.constants.CITIES?.forEach(city => {
        citySelect.innerHTML += `<option value="${city}">${city}</option>`;
        filterCitySelect.innerHTML += `<option value="${city}">${city}</option>`;
    });

    // Goals
    state.constants.GOALS?.forEach(goal => {
        goalSelect.innerHTML += `<option value="${goal}">${goal}</option>`;
    });

    // Education
    state.constants.EDUCATION?.forEach(edu => {
        eduSelect.innerHTML += `<option value="${edu}">${edu}</option>`;
    });

    // Interests
    chipGrid.innerHTML = '';
    state.constants.INTERESTS?.forEach(interest => {
        const chip = document.createElement('div');
        chip.className = 'chip-item';
        chip.textContent = interest;
        chip.onclick = () => toggleInterestChip(chip, interest);
        chipGrid.appendChild(chip);
    });
}

function toggleInterestChip(el, interest) {
    if (state.selectedInterests.includes(interest)) {
        state.selectedInterests = state.selectedInterests.filter(i => i !== interest);
        el.classList.remove('selected');
    } else {
        if (state.selectedInterests.length >= 5) {
            showToast('حداکثر ۵ مورد می‌توانید انتخاب کنید');
            return;
        }
        state.selectedInterests.push(interest);
        el.classList.add('selected');
    }
}

// --- Update Profile View ---
function updateMyProfileUI() {
    if (!state.user) return;
    document.getElementById('my-profile-name-age').textContent = `${state.user.name || 'کاربر'}, ${state.user.age || ''}`;
    document.getElementById('my-profile-city').innerHTML = `<i class="ph-fill ph-map-pin"></i> ${state.user.city || 'ثبت نشده'}`;
    document.getElementById('stat-likes-remaining').textContent = 50 - (state.user.daily_likes_used || 0);

    if (state.user.photo_url) {
        document.getElementById('my-profile-img').src = state.user.photo_url;
        document.getElementById('match-my-avatar').src = state.user.photo_url;
    }
}

// --- Navigation Handling ---
function setupNavigation() {
    const navItems = document.querySelectorAll('.nav-item');
    navItems.forEach(item => {
        item.addEventListener('click', () => {
            navItems.forEach(n => n.classList.remove('active'));
            item.classList.add('active');

            const tabId = item.dataset.tab;
            document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
            document.getElementById(tabId).classList.add('active');

            if (tabId === 'tab-matches') loadMatches();
            haptic('selection');
        });
    });
}

// --- Candidates Deck & Swiping ---
async function loadCandidates() {
    const deck = document.getElementById('card-deck');
    const emptyState = document.getElementById('empty-state');
    deck.innerHTML = '';
    state.candidates = [];
    state.currentIndex = 0;

    const res = await apiCall('/api/candidates', 'POST', state.filters);
    if (res.success && res.candidates?.length > 0) {
        state.candidates = res.candidates;
        emptyState.classList.add('hidden');
        renderCards();
    } else {
        emptyState.classList.remove('hidden');
    }
}

function renderCards() {
    const deck = document.getElementById('card-deck');
    deck.innerHTML = '';

    state.candidates.forEach((cand, idx) => {
        if (idx < state.currentIndex) return;

        const card = document.createElement('div');
        card.className = 'tinder-card';
        card.style.zIndex = state.candidates.length - idx;

        const photo = cand.photo_url || '/static/img/default-avatar.png';
        const goalBadge = cand.goal ? `<span class="meta-pill highlight"><i class="ph-fill ph-target"></i> ${cand.goal}</span>` : '';
        const jobBadge = cand.job ? `<span class="meta-pill"><i class="ph-fill ph-briefcase"></i> ${cand.job}</span>` : '';

        card.innerHTML = `
            <div class="card-image-wrapper">
                <img src="${photo}" alt="${cand.name}">
                <div class="card-gradient-overlay"></div>
            </div>
            
            <div class="swipe-stamp stamp-like">LIKE</div>
            <div class="swipe-stamp stamp-pass">NOPE</div>

            <div class="card-info-content">
                <div class="card-title-row">
                    <h2>${cand.name}</h2>
                    <span class="card-age">${cand.age}</span>
                </div>
                <div class="card-meta-chips">
                    <span class="meta-pill"><i class="ph-fill ph-map-pin"></i> ${cand.city}</span>
                    ${goalBadge}
                    ${jobBadge}
                </div>
                ${cand.bio ? `<p class="card-bio-text">${cand.bio}</p>` : ''}
            </div>
        `;

        if (idx === state.currentIndex) {
            initCardDrag(card, cand);
        }

        deck.appendChild(card);
    });
}

// --- Touch & Mouse Swiping Engine ---
function initCardDrag(card, candidate) {
    let startX = 0, currentX = 0, isDragging = false;
    const likeStamp = card.querySelector('.stamp-like');
    const passStamp = card.querySelector('.stamp-pass');

    const onStart = (e) => {
        isDragging = true;
        startX = e.type.includes('touch') ? e.touches[0].clientX : e.clientX;
        card.classList.add('moving');
    };

    const onMove = (e) => {
        if (!isDragging) return;
        currentX = (e.type.includes('touch') ? e.touches[0].clientX : e.clientX) - startX;
        const rotate = currentX * 0.08;

        card.style.transform = `translate3d(${currentX}px, 0, 0) rotate(${rotate}deg)`;

        if (currentX > 20) {
            likeStamp.style.opacity = Math.min(currentX / 100, 1);
            passStamp.style.opacity = 0;
        } else if (currentX < -20) {
            passStamp.style.opacity = Math.min(Math.abs(currentX) / 100, 1);
            likeStamp.style.opacity = 0;
        } else {
            likeStamp.style.opacity = 0;
            passStamp.style.opacity = 0;
        }
    };

    const onEnd = () => {
        if (!isDragging) return;
        isDragging = false;
        card.classList.remove('moving');

        if (currentX > 110) {
            triggerSwipe('like', card, candidate);
        } else if (currentX < -110) {
            triggerSwipe('pass', card, candidate);
        } else {
            card.style.transform = '';
            likeStamp.style.opacity = 0;
            passStamp.style.opacity = 0;
        }
    };

    card.addEventListener('touchstart', onStart, { passive: true });
    card.addEventListener('touchmove', onMove, { passive: true });
    card.addEventListener('touchend', onEnd);

    card.addEventListener('mousedown', onStart);
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onEnd);
}

// --- Trigger Swipe Action ---
async function triggerSwipe(action, cardEl, candidate) {
    const isLike = action === 'like';
    haptic(isLike ? 'impactMedium' : 'impactLight');

    const flyX = isLike ? window.innerWidth * 1.3 : -window.innerWidth * 1.3;
    cardEl.style.transition = 'transform 0.4s ease, opacity 0.3s ease';
    cardEl.style.transform = `translate3d(${flyX}px, 0, 0) rotate(${isLike ? 35 : -35}deg)`;
    cardEl.style.opacity = '0';

    setTimeout(() => cardEl.remove(), 400);

    state.currentIndex++;
    if (state.currentIndex >= state.candidates.length) {
        document.getElementById('empty-state').classList.remove('hidden');
    } else {
        const nextCard = document.querySelectorAll('.tinder-card')[1];
        if (nextCard) initCardDrag(nextCard, state.candidates[state.currentIndex]);
    }

    const res = await apiCall('/api/swipe', 'POST', {
        target_id: candidate.user_id,
        action: action
    });

    if (res.success && res.is_match) {
        showMatchCelebration(candidate);
    }
}

// --- Match Celebration Modal ---
function showMatchCelebration(partner) {
    haptic('notificationSuccess');
    document.getElementById('match-partner-name').textContent = partner.name;
    document.getElementById('match-partner-avatar').src = partner.photo_url || '/static/img/default-avatar.png';
    
    const tgBtn = document.getElementById('btn-match-telegram-link');
    if (partner.username) {
        tgBtn.href = `https://t.me/${partner.username}`;
        tgBtn.classList.remove('hidden');
    } else {
        tgBtn.classList.add('hidden');
    }

    openModal('modal-match-success');
}

// --- Swipe Bottom Buttons ---
function setupSwipeButtons() {
    document.getElementById('btn-like').onclick = () => {
        const currentCard = document.querySelectorAll('.tinder-card')[0];
        if (currentCard && state.candidates[state.currentIndex]) {
            triggerSwipe('like', currentCard, state.candidates[state.currentIndex]);
        }
    };

    document.getElementById('btn-pass').onclick = () => {
        const currentCard = document.querySelectorAll('.tinder-card')[0];
        if (currentCard && state.candidates[state.currentIndex]) {
            triggerSwipe('pass', currentCard, state.candidates[state.currentIndex]);
        }
    };

    document.getElementById('btn-reset-seen').onclick = async () => {
        const res = await apiCall('/api/reset-seen', 'POST');
        if (res.success) {
            showToast('لیست افراد بازنشانی شد.');
            await loadCandidates();
        }
    };
}

// --- Modals Management ---
function setupModals() {
    document.querySelectorAll('[data-close]').forEach(btn => {
        btn.onclick = () => closeModal(btn.dataset.close);
    });

    document.getElementById('btn-filters').onclick = () => openModal('modal-filters');
    document.getElementById('btn-edit-profile-open').onclick = () => {
        populateProfileFormFields();
        openModal('modal-profile-form');
    };
    document.getElementById('btn-close-match-modal').onclick = () => closeModal('modal-match-success');

    // Filter Sliders Display
    const minAge = document.getElementById('filter-min-age');
    const maxAge = document.getElementById('filter-max-age');
    const rangeDisp = document.getElementById('age-range-display');

    const updateAgeDisplay = () => {
        rangeDisp.textContent = `${minAge.value} تا ${maxAge.value} سال`;
    };
    minAge.oninput = updateAgeDisplay;
    maxAge.oninput = updateAgeDisplay;

    document.getElementById('btn-apply-filters').onclick = () => {
        state.filters.gender = document.querySelector('input[name="filter-gender"]:checked').value;
        state.filters.city = document.getElementById('filter-city').value;
        state.filters.min_age = parseInt(minAge.value);
        state.filters.max_age = parseInt(maxAge.value);
        closeModal('modal-filters');
        loadCandidates();
    };
}

function openModal(id) {
    document.getElementById(id).classList.remove('hidden');
}

function closeModal(id) {
    document.getElementById(id).classList.add('hidden');
}

// --- Profile Form Submit ---
function setupProfileForm() {
    document.getElementById('form-profile').onsubmit = async (e) => {
        e.preventDefault();
        const payload = {
            name: document.getElementById('input-name').value,
            age: parseInt(document.getElementById('input-age').value),
            gender: document.getElementById('input-gender').value,
            city: document.getElementById('input-city').value,
            goal: document.getElementById('input-goal').value,
            education: document.getElementById('input-education').value,
            job: document.getElementById('input-job').value,
            bio: document.getElementById('input-bio').value,
            interests: state.selectedInterests
        };

        const res = await apiCall('/api/profile', 'POST', payload);
        if (res.success) {
            state.user = { ...state.user, ...payload, is_complete: 1 };
            updateMyProfileUI();
            closeModal('modal-profile-form');
            document.getElementById('btn-close-profile-modal').classList.remove('hidden');
            showToast('پروفایل با موفقیت ثبت شد ✨');
            loadCandidates();
        } else {
            showToast(res.error || 'خطا در ثبت پروفایل');
        }
    };

    // Photo Upload
    document.getElementById('input-photo-upload').onchange = async (e) => {
        const file = e.target.files[0];
        if (!file) return;

        const formData = new FormData();
        formData.append('photo', file);

        showToast('در حال بهینه‌سازی و آپلود عکس...');
        const res = await apiCall('/api/photo', 'POST', formData, true);
        if (res.success) {
            state.user.photo_url = res.photo_url;
            updateMyProfileUI();
            showToast('عکس با موفقیت تغییر کرد ✅');
        } else {
            showToast(res.error || 'خطا در آپلود عکس');
        }
    };
}

function populateProfileFormFields() {
    if (!state.user) return;
    document.getElementById('input-name').value = state.user.name || '';
    document.getElementById('input-age').value = state.user.age || '';
    document.getElementById('input-gender').value = state.user.gender || '';
    document.getElementById('input-city').value = state.user.city || '';
    document.getElementById('input-goal').value = state.user.goal || '';
    document.getElementById('input-education').value = state.user.education || '';
    document.getElementById('input-job').value = state.user.job || '';
    document.getElementById('input-bio').value = state.user.bio || '';

    state.selectedInterests = state.user.interests ? state.user.interests.split(',') : [];
    document.querySelectorAll('.chip-item').forEach(chip => {
        chip.classList.toggle('selected', state.selectedInterests.includes(chip.textContent));
    });
}

// --- Matches List Loader ---
async function loadMatches() {
    const listEl = document.getElementById('matches-list');
    const emptyEl = document.getElementById('matches-empty');
    listEl.innerHTML = '';

    const res = await apiCall('/api/matches');
    if (res.success && res.matches?.length > 0) {
        emptyEl.classList.add('hidden');
        document.getElementById('matches-count-badge').textContent = `${res.matches.length} مچ`;
        document.getElementById('stat-matches-total').textContent = res.matches.length;

        res.matches.forEach(m => {
            const card = document.createElement('div');
            card.className = 'match-card';
            card.innerHTML = `
                <img src="${m.photo_url || '/static/img/default-avatar.png'}" alt="${m.name}">
                <div class="match-card-overlay">
                    <h4>${m.name}</h4>
                    <span>${m.city || ''}</span>
                </div>
            `;
            card.onclick = () => {
                if (m.username) {
                    window.open(`https://t.me/${m.username}`, '_blank');
                } else {
                    showToast('کاربر آیدی تلگرام تنظیم نکرده است.');
                }
            };
            listEl.appendChild(card);
        });
    } else {
        emptyEl.classList.remove('hidden');
        document.getElementById('matches-count-badge').textContent = '۰ مچ';
    }
}

// --- Toast & Haptics ---
function showToast(msg) {
    const toast = document.getElementById('toast');
    document.getElementById('toast-message').textContent = msg;
    toast.classList.remove('hidden');
    setTimeout(() => toast.classList.add('hidden'), 3200);
}

function haptic(type) {
    try {
        if (tg?.HapticFeedback) {
            if (type === 'impactMedium') tg.HapticFeedback.impactOccurred('medium');
            else if (type === 'impactLight') tg.HapticFeedback.impactOccurred('light');
            else if (type === 'notificationSuccess') tg.HapticFeedback.notificationOccurred('success');
            else if (type === 'selection') tg.HapticFeedback.selectionChanged();
        }
    } catch (e) {}
}
