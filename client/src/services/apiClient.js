const API_BASE_URL =
    import.meta.env.VITE_API_BASE_URL || `${window.location.protocol}//${window.location.hostname}:8000`;

const ENDPOINTS = {
    health: '/api/health',
    spotifyLoginStart: '/api/v1/auth/spotify/login',
    spotifyCallback: '/api/v1/auth/spotify/callback',
    demoStart: '/api/v1/auth/demo/start',
    demoMe: '/api/v1/auth/demo/me',
    demoLogout: '/api/v1/auth/demo/logout',
    authMe: '/api/v1/auth/me',
    authLoginPlaceholder: '/api/v1/auth/login',
    authLogout: '/api/v1/auth/logout',
    moodRecommend: '/api/v1/mood/recommend',
    moodDashboard: '/api/v1/mood/dashboard',
    moodHistory: '/api/v1/mood/history',
    favorites: '/api/v1/favorites',
};

function buildUrl(path, query = {}) {
    const url = new URL(`${API_BASE_URL}${path}`, window.location.origin);
    Object.entries(query).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== '') {
            url.searchParams.set(key, String(value));
        }
    });
    return url.toString();
}

async function request(path, options = {}) {
    const hasBody = options.body !== undefined && options.body !== null;
    const response = await fetch(`${API_BASE_URL}${path}`, {
        credentials: 'include',
        headers: {
            ...(hasBody ? { 'Content-Type': 'application/json; charset=utf-8' } : {}),
            ...(options.headers || {}),
        },
        ...options,
    });

    if (!response.ok) {
        let detail = '요청 처리에 실패했습니다.';
        let code = 'UNKNOWN_ERROR';
        try {
            const errorBody = await response.json();
            detail = errorBody.detail || detail;
            code = errorBody.code || code;
        } catch {
            // Keep default error details when body is not JSON.
        }
        const error = new Error(detail);
        error.status = response.status;
        error.code = code;
        throw error;
    }

    if (response.status === 204) {
        return null;
    }

    return response.json();
}

export function getSpotifyLoginUrl(state) {
    return buildUrl(ENDPOINTS.spotifyLoginStart, {
        ...(state ? { state } : {}),
        frontend_origin: window.location.origin,
    });
}

export function startDemoSession(payload = {}) {
    return request(ENDPOINTS.demoStart, {
        method: 'POST',
        body: JSON.stringify(payload),
    });
}

export function getDemoSession() {
    return request(ENDPOINTS.demoMe, {
        method: 'GET',
    });
}

export function getHealth() {
    return request(ENDPOINTS.health, { method: 'GET' });
}

export function getSpotifyCallback(code, state) {
    return request(
        `${ENDPOINTS.spotifyCallback}?code=${encodeURIComponent(code)}&state=${encodeURIComponent(state)}&frontend_origin=${encodeURIComponent(window.location.origin)}`,
        {
            method: 'GET',
        },
    );
}

export function getCurrentUser() {
    return request(ENDPOINTS.authMe, {
        method: 'GET',
    });
}

export function loginPlaceholder(payload) {
    return request(ENDPOINTS.authLoginPlaceholder, {
        method: 'POST',
        body: JSON.stringify(payload),
    });
}

export function logoutAccount() {
    return request(ENDPOINTS.authLogout, {
        method: 'POST',
    });
}

export function logoutDemoSession() {
    return request(ENDPOINTS.demoLogout, {
        method: 'POST',
    });
}

export function recommendMood(payload) {
    console.info('[Mood Sync] Gemini 추천 요청 시작', {
        mood: payload?.mood || null,
        hasText: Boolean(payload?.text),
    });

    return request(ENDPOINTS.moodRecommend, {
        method: 'POST',
        body: JSON.stringify(payload),
    }).then((result) => {
        const profile = result?.recommendation?.generation_profile || {};
        const status = {
            attempted: profile.gemini_copy_attempted ?? null,
            succeeded: profile.gemini_copy_succeeded ?? null,
            reasonCount: profile.gemini_reason_count ?? null,
            reasonSource: profile.reason_source ?? null,
            hasRagContext: profile.has_rag_context ?? null,
            error: profile.gemini_copy_error ?? null,
            pending: profile.gemini_copy_pending ?? false,
        };

        if (status.pending) {
            console.info('[Mood Sync] fallback 결과를 먼저 표시하고 Gemini 이유를 생성 중입니다', status);
        } else if (status.succeeded && status.reasonSource === 'gemini') {
            console.info('[Mood Sync] Gemini 추천 이유 생성 성공', status);
        } else if (status.attempted) {
            console.warn('[Mood Sync] Gemini 호출은 되었지만 fallback 이유를 사용합니다', status);
            if (status.error) {
                console.error('[Mood Sync] Gemini fallback 원인:', status.error);
            }
        } else {
            console.warn('[Mood Sync] Gemini 추천 이유가 실행되지 않았습니다', status);
        }
        return result;
    }).catch((error) => {
        console.error('[Mood Sync] 추천 요청 실패', error);
        throw error;
    });
}

export function getMoodDashboard() {
    return request(ENDPOINTS.moodDashboard, {
        method: 'GET',
    });
}

export function getMoodHistory({ year, month } = {}) {
    const params = new URLSearchParams();
    if (year !== undefined && year !== null && year !== '') params.set('year', String(year));
    if (month !== undefined && month !== null && month !== '') params.set('month', String(month));
    const query = params.toString();

    return request(query ? `${ENDPOINTS.moodHistory}?${query}` : ENDPOINTS.moodHistory, {
        method: 'GET',
    });
}

export function getFavorites() {
    return request(ENDPOINTS.favorites, {
        method: 'GET',
    });
}

export function saveFavorite(payload) {
    return request(ENDPOINTS.favorites, {
        method: 'POST',
        body: JSON.stringify(payload),
    });
}

export function removeFavorite(trackId) {
    return request(`${ENDPOINTS.favorites}/${encodeURIComponent(trackId)}`, {
        method: 'DELETE',
    });
}
