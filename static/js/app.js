/* ══════════════════════════════════════════════════════
   HAMDAM — Telegram Mini App Client Engine v3
   ══════════════════════════════════════════════════════ */

const tg = window.Telegram?.WebApp;
if (tg) { tg.ready(); tg.expand(); try { tg.setHeaderColor('#0a0d14'); tg.setBackgroundColor('#0a0d14'); } catch(e){} }

const S = { user: null, consts: {}, cands: [], idx: 0, filters: { gender:'', city:'', min_age:18, max_age:45 }, selInterests: [] };

document.addEventListener('DOMContentLoaded', () => { setupNav(); setupModals(); setupActions(); setupForm(); init(); });

// ── API ──
async function api(url, method='GET', body=null, isForm=false) {
    const h = { 'X-Telegram-Init-Data': tg?.initData || '' };
    const o = { method, headers: h };
    if (body) { if (isForm) { o.body = body; } else { h['Content-Type'] = 'application/json'; o.body = JSON.stringify(body); } }
    try { const r = await fetch(url, o); return await r.json(); } catch(e) { toast('خطا در ارتباط'); return { success: false }; }
}

// ── Init ──
async function init() {
    const r = await api('/api/init');
    if (!r.success) { toast(r.error || 'خطا'); return; }
    S.consts = r.constants; S.user = r.user; S.user.daily_likes_used = r.daily_likes_used;
    fillDropdowns();
    if (!S.user.is_complete) { openModal('modal-profile'); document.getElementById('btn-close-profile').classList.add('hidden'); }
    else { updateProfileUI(); loadCandidates(); }
}

// ── Fill Dropdowns ──
function fillDropdowns() {
    const c = S.consts;
    const cities = c.cities || []; const goals = c.goals || []; const edu = c.education || []; const ints = c.interests || [];

    const fCity = document.getElementById('f-city');
    const flCity = document.getElementById('filter-city');
    const fGoal = document.getElementById('f-goal');
    const fEdu = document.getElementById('f-edu');
    const chips = document.getElementById('chips');

    fCity.innerHTML = '<option value="" disabled selected>انتخاب شهر</option>';
    flCity.innerHTML = '<option value="">همه شهرها</option>';
    fGoal.innerHTML = '<option value="">انتخاب هدف</option>';
    fEdu.innerHTML = '<option value="">انتخاب</option>';

    cities.forEach(v => { fCity.innerHTML += `<option value="${v}">${v}</option>`; flCity.innerHTML += `<option value="${v}">${v}</option>`; });
    goals.forEach(v => { fGoal.innerHTML += `<option value="${v}">${v}</option>`; });
    edu.forEach(v => { fEdu.innerHTML += `<option value="${v}">${v}</option>`; });

    chips.innerHTML = '';
    ints.forEach(v => {
        const d = document.createElement('div');
        d.className = 'px-3 py-1.5 rounded-full text-xs font-medium border cursor-pointer transition-all duration-200 ';
        d.className += S.selInterests.includes(v) ? 'bg-brand/20 border-brand text-white' : 'bg-white/5 border-white/10 text-white/50';
        d.textContent = v;
        d.onclick = () => toggleChip(d, v);
        chips.appendChild(d);
    });
}

function toggleChip(el, val) {
    if (S.selInterests.includes(val)) {
        S.selInterests = S.selInterests.filter(i => i !== val);
        el.className = 'px-3 py-1.5 rounded-full text-xs font-medium border cursor-pointer transition-all duration-200 bg-white/5 border-white/10 text-white/50';
    } else {
        if (S.selInterests.length >= 5) { toast('حداکثر ۵ مورد'); return; }
        S.selInterests.push(val);
        el.className = 'px-3 py-1.5 rounded-full text-xs font-medium border cursor-pointer transition-all duration-200 bg-brand/20 border-brand text-white';
    }
}

// ── Update Profile UI ──
function updateProfileUI() {
    if (!S.user) return;
    document.getElementById('my-name').textContent = `${S.user.name || 'کاربر'}، ${S.user.age || ''}`;
    document.getElementById('my-city').querySelector('span').textContent = S.user.city || '—';
    document.getElementById('stat-likes').textContent = (S.consts.daily_like_limit || 50) - (S.user.daily_likes_used || 0);
    if (S.user.photo_url) { document.getElementById('my-photo').src = S.user.photo_url; }
}

// ── Navigation ──
function setupNav() {
    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.nav-btn').forEach(b => { b.classList.remove('active'); b.classList.add('text-white/40'); });
            btn.classList.add('active'); btn.classList.remove('text-white/40');
            const tid = btn.dataset.tab;
            document.querySelectorAll('.tab-pane').forEach(p => p.classList.add('hidden'));
            document.getElementById(tid).classList.remove('hidden');
            if (tid === 'tab-matches') loadMatches();
            haptic('selection');
        });
    });
}

// ── Candidates ──
async function loadCandidates() {
    const deck = document.getElementById('card-deck');
    deck.innerHTML = ''; S.cands = []; S.idx = 0;
    const r = await api('/api/candidates', 'POST', S.filters);
    if (r.success && r.candidates?.length) { S.cands = r.candidates; document.getElementById('empty-state').classList.add('hidden'); renderDeck(); }
    else { document.getElementById('empty-state').classList.remove('hidden'); }
}

function renderDeck() {
    const deck = document.getElementById('card-deck'); deck.innerHTML = '';
    S.cands.forEach((c, i) => {
        if (i < S.idx) return;
        const card = document.createElement('div');
        card.className = 'absolute inset-0 rounded-3xl overflow-hidden card-shadow';
        card.style.zIndex = S.cands.length - i;
        card.style.transition = 'transform .2s ease, opacity .2s ease';
        card.style.touchAction = 'none';

        const photo = c.photo_url || "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Crect width='100' height='100' fill='%231e2433'/%3E%3Ctext x='50' y='55' text-anchor='middle' fill='%23ffffff30' font-size='28'%3E👤%3C/text%3E%3C/svg%3E";
        const goalTag = c.goal ? `<span class="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-brand/20 border border-brand/30 text-[11px] text-pink-200 backdrop-blur-md"><i class="ph-fill ph-target"></i>${c.goal}</span>` : '';
        const jobTag = c.job ? `<span class="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-white/10 border border-white/10 text-[11px] text-white/80 backdrop-blur-md"><i class="ph-fill ph-briefcase"></i>${c.job}</span>` : '';
        const bioLine = c.bio ? `<p class="text-[13px] text-white/70 line-clamp-2 leading-relaxed mt-1">${c.bio}</p>` : '';

        card.innerHTML = `
            <img src="${photo}" class="absolute inset-0 w-full h-full object-cover" alt="">
            <div class="absolute inset-0 bg-gradient-to-b from-black/10 via-transparent to-dark-900/95 pointer-events-none"></div>
            <div class="stamp-like absolute top-8 right-6 px-4 py-1.5 rounded-xl text-xl font-black border-[3px] border-neon-green text-neon-green opacity-0 rotate-12 scale-75 transition-all pointer-events-none z-10 shadow-lg shadow-green-500/30">LIKE</div>
            <div class="stamp-pass absolute top-8 left-6 px-4 py-1.5 rounded-xl text-xl font-black border-[3px] border-neon-red text-neon-red opacity-0 -rotate-12 scale-75 transition-all pointer-events-none z-10 shadow-lg shadow-red-500/30">NOPE</div>
            <div class="absolute bottom-0 left-0 right-0 p-5 z-[5]">
                <div class="flex items-baseline gap-2 mb-1.5">
                    <h2 class="text-2xl font-extrabold text-white">${c.name}</h2>
                    <span class="text-xl font-light text-white/80">${c.age}</span>
                </div>
                <div class="flex flex-wrap gap-1.5 mb-1">
                    <span class="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-white/10 border border-white/10 text-[11px] text-white/80 backdrop-blur-md"><i class="ph-fill ph-map-pin"></i>${c.city}</span>
                    ${goalTag}${jobTag}
                </div>
                ${bioLine}
            </div>
        `;

        if (i === S.idx) initDrag(card, c);
        deck.appendChild(card);
    });
}

// ── Swipe Drag Engine ──
function initDrag(card, cand) {
    let sx = 0, cx = 0, drag = false;
    const lk = card.querySelector('.stamp-like'), ps = card.querySelector('.stamp-pass');

    const start = e => { drag = true; sx = (e.touches ? e.touches[0].clientX : e.clientX); card.style.transition = 'none'; card.style.cursor = 'grabbing'; };
    const move = e => { if (!drag) return; cx = (e.touches ? e.touches[0].clientX : e.clientX) - sx; card.style.transform = `translate3d(${cx}px,0,0) rotate(${cx*.08}deg)`;
        if (cx > 20) { lk.style.opacity = Math.min(cx/100,1); lk.style.transform = 'rotate(12deg) scale(1)'; ps.style.opacity = 0; }
        else if (cx < -20) { ps.style.opacity = Math.min(Math.abs(cx)/100,1); ps.style.transform = 'rotate(-12deg) scale(1)'; lk.style.opacity = 0; }
        else { lk.style.opacity = 0; ps.style.opacity = 0; }
    };
    const end = () => { if (!drag) return; drag = false; card.style.cursor = 'grab';
        if (cx > 110) doSwipe('like', card, cand);
        else if (cx < -110) doSwipe('pass', card, cand);
        else { card.style.transition = 'transform .3s ease'; card.style.transform = ''; lk.style.opacity = 0; ps.style.opacity = 0; }
    };

    card.addEventListener('touchstart', start, {passive:true});
    card.addEventListener('touchmove', move, {passive:true});
    card.addEventListener('touchend', end);
    card.addEventListener('mousedown', start);
    window.addEventListener('mousemove', move);
    window.addEventListener('mouseup', end);
}

async function doSwipe(action, el, cand) {
    const like = action === 'like';
    haptic(like ? 'impactMedium' : 'impactLight');
    const fly = like ? window.innerWidth * 1.5 : -window.innerWidth * 1.5;
    el.style.transition = 'transform .4s ease, opacity .3s ease';
    el.style.transform = `translate3d(${fly}px,0,0) rotate(${like?35:-35}deg)`;
    el.style.opacity = '0';
    setTimeout(() => el.remove(), 400);

    S.idx++;
    if (S.idx >= S.cands.length) { document.getElementById('empty-state').classList.remove('hidden'); }
    else { const next = document.querySelectorAll('#card-deck > div')[0]; if (next) initDrag(next, S.cands[S.idx]); }

    const r = await api('/api/swipe', 'POST', { target_id: cand.user_id, action });
    if (!r.success && r.error) toast(r.error);
    if (r.success && r.is_match) showMatch(cand);
}

// ── Match Modal ──
function showMatch(partner) {
    haptic('notificationSuccess');
    document.getElementById('match-name').textContent = partner.name;
    document.getElementById('match-partner-img').src = partner.photo_url || '';
    document.getElementById('match-my-img').src = S.user.photo_url || '';
    const link = document.getElementById('match-tg-link');
    if (partner.username) { link.href = `https://t.me/${partner.username}`; link.classList.remove('hidden'); }
    else { link.classList.add('hidden'); }
    openModal('modal-match');
}

// ── Action Buttons ──
function setupActions() {
    document.getElementById('btn-like').onclick = () => { const c = document.querySelector('#card-deck > div'); if (c && S.cands[S.idx]) doSwipe('like', c, S.cands[S.idx]); };
    document.getElementById('btn-pass').onclick = () => { const c = document.querySelector('#card-deck > div'); if (c && S.cands[S.idx]) doSwipe('pass', c, S.cands[S.idx]); };
    document.getElementById('btn-reset-seen').onclick = async () => { const r = await api('/api/reset-seen','POST'); if (r.success) { toast('بازنشانی شد'); loadCandidates(); } };
}

// ── Modals ──
function setupModals() {
    document.querySelectorAll('[data-close]').forEach(b => b.onclick = () => closeModal(b.dataset.close));
    document.getElementById('btn-filters').onclick = () => openModal('modal-filters');
    document.getElementById('btn-edit-profile').onclick = () => { fillProfileForm(); document.getElementById('btn-close-profile').classList.remove('hidden'); document.getElementById('profile-modal-title').textContent = 'ویرایش پروفایل'; openModal('modal-profile'); };
    document.getElementById('btn-close-match').onclick = () => closeModal('modal-match');

    const mn = document.getElementById('filter-min-age'), mx = document.getElementById('filter-max-age'), disp = document.getElementById('age-display');
    const upd = () => disp.textContent = `${mn.value} — ${mx.value}`;
    mn.oninput = upd; mx.oninput = upd;

    document.getElementById('btn-apply-filters').onclick = () => {
        S.filters.gender = document.querySelector('input[name="fg"]:checked').value;
        S.filters.city = document.getElementById('filter-city').value;
        S.filters.min_age = parseInt(mn.value); S.filters.max_age = parseInt(mx.value);
        closeModal('modal-filters'); loadCandidates();
    };
}

function openModal(id) { document.getElementById(id).classList.remove('hidden'); }
function closeModal(id) { document.getElementById(id).classList.add('hidden'); }

// ── Profile Form ──
function setupForm() {
    document.getElementById('form-profile').onsubmit = async e => {
        e.preventDefault();
        const payload = {
            name: document.getElementById('f-name').value, age: parseInt(document.getElementById('f-age').value),
            gender: document.getElementById('f-gender').value, city: document.getElementById('f-city').value,
            goal: document.getElementById('f-goal').value, education: document.getElementById('f-edu').value,
            job: document.getElementById('f-job').value, bio: document.getElementById('f-bio').value,
            interests: S.selInterests
        };
        const r = await api('/api/profile', 'POST', payload);
        if (r.success) { S.user = { ...S.user, ...payload, is_complete: 1 }; updateProfileUI(); closeModal('modal-profile'); toast('پروفایل ذخیره شد ✨'); loadCandidates(); }
        else toast(r.error || 'خطا');
    };

    document.getElementById('photo-upload').onchange = async e => {
        const f = e.target.files[0]; if (!f) return;
        const fd = new FormData(); fd.append('photo', f);
        toast('در حال آپلود...');
        const r = await api('/api/photo', 'POST', fd, true);
        if (r.success) { S.user.photo_url = r.photo_url; updateProfileUI(); toast('عکس آپلود شد ✅'); }
        else toast(r.error || 'خطا');
    };
}

function fillProfileForm() {
    if (!S.user) return;
    document.getElementById('f-name').value = S.user.name || '';
    document.getElementById('f-age').value = S.user.age || '';
    document.getElementById('f-gender').value = S.user.gender || '';
    document.getElementById('f-city').value = S.user.city || '';
    document.getElementById('f-goal').value = S.user.goal || '';
    document.getElementById('f-edu').value = S.user.education || '';
    document.getElementById('f-job').value = S.user.job || '';
    document.getElementById('f-bio').value = S.user.bio || '';
    if (S.user.interests) {
        S.selInterests = typeof S.user.interests === 'string' ? S.user.interests.split(',').map(i=>i.trim()).filter(Boolean) : (Array.isArray(S.user.interests) ? [...S.user.interests] : []);
    } else { S.selInterests = []; }
    document.querySelectorAll('#chips > div').forEach(c => {
        const sel = S.selInterests.includes(c.textContent);
        c.className = 'px-3 py-1.5 rounded-full text-xs font-medium border cursor-pointer transition-all duration-200 ' + (sel ? 'bg-brand/20 border-brand text-white' : 'bg-white/5 border-white/10 text-white/50');
    });
}

// ── Matches ──
async function loadMatches() {
    const list = document.getElementById('matches-list'), empty = document.getElementById('matches-empty');
    list.innerHTML = '';
    const r = await api('/api/matches');
    if (r.success && r.matches?.length) {
        empty.classList.add('hidden'); list.classList.remove('hidden');
        document.getElementById('matches-badge').textContent = r.matches.length;
        document.getElementById('stat-matches').textContent = r.matches.length;
        r.matches.forEach(m => {
            const ph = m.photo_url || "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Crect width='100' height='100' fill='%231e2433'/%3E%3Ctext x='50' y='55' text-anchor='middle' fill='%23ffffff30' font-size='28'%3E👤%3C/text%3E%3C/svg%3E";
            const d = document.createElement('div');
            d.className = 'relative aspect-[3/4] rounded-2xl overflow-hidden bg-dark-700 border border-white/5 shadow-lg cursor-pointer active:scale-[.97] transition-transform';
            d.innerHTML = `<img src="${ph}" class="w-full h-full object-cover"><div class="absolute inset-0 bg-gradient-to-t from-black/90 via-transparent to-transparent flex flex-col justify-end p-3"><h4 class="text-sm font-bold text-white">${m.name}</h4><span class="text-[11px] text-white/50">${m.city||''}</span></div>`;
            d.onclick = () => { if (m.username) window.open(`https://t.me/${m.username}`, '_blank'); else toast('آیدی تلگرام ثبت نشده'); };
            list.appendChild(d);
        });
    } else { empty.classList.remove('hidden'); list.classList.add('hidden'); document.getElementById('matches-badge').textContent = '۰'; }
}

// ── Utilities ──
function toast(msg) {
    const t = document.getElementById('toast'); document.getElementById('toast-msg').textContent = msg;
    t.classList.remove('hidden'); t.style.opacity = '1'; t.style.transform = 'translateX(-50%) translateY(0)';
    setTimeout(() => { t.style.opacity = '0'; t.style.transform = 'translateX(-50%) translateY(-10px)'; setTimeout(() => t.classList.add('hidden'), 300); }, 3000);
}

function haptic(type) {
    try {
        if (!tg?.HapticFeedback) return;
        if (type==='impactMedium') tg.HapticFeedback.impactOccurred('medium');
        else if (type==='impactLight') tg.HapticFeedback.impactOccurred('light');
        else if (type==='notificationSuccess') tg.HapticFeedback.notificationOccurred('success');
        else if (type==='selection') tg.HapticFeedback.selectionChanged();
    } catch(e){}
}
