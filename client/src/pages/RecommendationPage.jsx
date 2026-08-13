import { useEffect, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import Header from '../components/Header';
import Footer from '../components/Footer';
import FavoriteToast from '../components/FavoriteToast';
import { getFavorites, getMoodDashboard, removeFavorite, saveFavorite } from '../services/apiClient';

const T = {
    bg: '#FAF8F4',
    bgSoft: '#F1ECE3',
    surface: '#FFFFFF',
    ink: '#211C26',
    inkSoft: '#6E6678',
    inkFaint: '#A39CAC',
    line: '#E5DFD3',
    lineStrong: '#D6CFC1',
    joy: '#FF6B5E',
    calm: '#7B7FF0',
    warm: '#FFB648',
    joySoft: '#FFEAE6',
    calmSoft: '#ECEDFD',
    warmSoft: '#FFF3DE',
    spotGreen: '#1ED760',
    spotBlack: '#191414',
};

/* ───────────────────────────────────────────
   ICONS
─────────────────────────────────────────── */
const Ic = ({ d, size = 20, color = 'currentColor', fill = 'none', sw = 1.8, className = '' }) => (
    <svg
        width={size}
        height={size}
        viewBox="0 0 24 24"
        fill={fill}
        stroke={color}
        strokeWidth={sw}
        strokeLinecap="round"
        strokeLinejoin="round"
        className={`inline-block shrink-0 align-middle ${className}`}
    >
        {(Array.isArray(d) ? d : [d]).map((p, i) => (
            <path key={i} d={p} />
        ))}
    </svg>
);

const I = {
    heart: 'M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z',
    play: 'M6 3l15 9-15 9V3z',
    music: 'M9 18V5l12-2v13M9 18a3 3 0 1 1-6 0 3 3 0 0 1 6 0zm12-2a3 3 0 1 1-6 0 3 3 0 0 1 6 0z',
    sparkles:
        'M9.937 15.5A2 2 0 0 0 8.5 14.063l-6.135-1.582a.5.5 0 0 1 0-.962L8.5 9.936A2 2 0 0 0 9.937 8.5l1.582-6.135a.5.5 0 0 1 .963 0L14.063 8.5A2 2 0 0 0 15.5 9.937l6.135 1.581a.5.5 0 0 1 0 .964L15.5 14.063a2 2 0 0 0-1.437 1.437l-1.582 6.135a.5.5 0 0 1-.963 0z',
    refresh: 'M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8M3 3v5h5',
    smile: [
        'M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10z',
        'M8 14s1.5 2 4 2 4-2 4-2',
        'M9 9h.01M15 9h.01',
    ],
    bulb: [
        'M9 18h6',
        'M10 22h4',
        'M12 2a7 7 0 0 1 7 7c0 2.38-1.19 4.47-3 5.74V17a2 2 0 0 1-2 2h-4a2 2 0 0 1-2-2v-2.26C6.19 13.47 5 11.38 5 9a7 7 0 0 1 7-7z',
    ],
    clock: ['M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10z', 'M12 6v6l4 2'],
    tag: ['M20.59 13.41 11 22.99l-9-9 9.59-9.59A2 2 0 0 1 13 4h6a2 2 0 0 1 2 2v6a2 2 0 0 1-.41 1.41z', 'M7 7h.01'],
    pen: 'M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z',
    arrowR: 'M5 12h14M12 5l7 7-7 7',
};

/* ───────────────────────────────────────────
   SPOTIFY MARK  (공식, 변형 금지)
─────────────────────────────────────────── */
const SpotifyMark = ({ size = 18 }) => (
    <svg width={size} height={size} viewBox="0 0 24 24" className="inline-block shrink-0">
        <circle cx="12" cy="12" r="12" fill="#1ED760" />
        <path
            d="M17.5 10.7c-3-1.8-7.9-2-10.7-1.1a.7.7 0 1 1-.4-1.4c3.2-1 8.7-.8 12.1 1.2a.7.7 0 0 1-.7 1.3h-.3zm-.1 2.9c-2.5-1.5-6.3-2-9.3-1.1a.6.6 0 1 1-.3-1.1c3.4-1 7.6-.5 10.5 1.2a.6.6 0 0 1-.6 1h-.3zm-.3 2.8c-2.2-1.3-4.9-1.6-8-.9a.5.5 0 1 1-.2-1c3.4-.8 6.4-.4 8.8 1a.5.5 0 0 1-.6.9z"
            fill="white"
        />
    </svg>
);

/* ───────────────────────────────────────────
   RESPONSIVE HOOK  (랜딩 페이지와 완전 동일)
─────────────────────────────────────────── */
const useBreakpoint = () => {
    const [bp, setBp] = useState('desktop');
    useEffect(() => {
        const check = () => {
            const w = window.innerWidth;
            setBp(w < 560 ? 'mobile' : w < 900 ? 'tablet' : 'desktop');
        };
        check();
        window.addEventListener('resize', check);
        return () => window.removeEventListener('resize', check);
    }, []);
    return bp;
};

/* ───────────────────────────────────────────
   SESSION LOGIC
─────────────────────────────────────────── */
const STORAGE_KEY = 'mood-sync:last-recommendation';

const formatDuration = (durationMs) => {
    if (!durationMs) return null;
    const totalSeconds = Math.max(0, Math.floor(durationMs / 1000));
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = String(totalSeconds % 60).padStart(2, '0');
    return `${minutes}:${seconds}`;
};

const getSavedState = () => {
    if (typeof window === 'undefined') return null;
    try {
        const raw = window.sessionStorage.getItem(STORAGE_KEY);
        return raw ? JSON.parse(raw) : null;
    } catch {
        return null;
    }
};

const saveState = (state) => {
    if (typeof window === 'undefined') return;
    try {
        window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    } catch {}
};

/* ───────────────────────────────────────────
   LINK BUTTON  — 랜딩의 BtnGhost와 동일한 feel
─────────────────────────────────────────── */
function LinkBtn({ to, children }) {
    const [hov, setHov] = useState(false);
    return (
        <Link
            to={to}
            onMouseEnter={() => setHov(true)}
            onMouseLeave={() => setHov(false)}
            className={`mt-1 inline-flex items-center gap-2 self-end rounded-full border-[1.5px] px-5 py-3 text-[14px] font-bold text-[#211C26] no-underline transition-all duration-200 ${
                hov
                    ? 'border-[#211C26] bg-white -translate-y-px shadow-[0_8px_24px_-8px_rgba(33,28,38,0.18)]'
                    : 'border-[#D6CFC1] bg-transparent'
            }`}
        >
            {children}
        </Link>
    );
}

/* ───────────────────────────────────────────
   MOOD MAP  — MoodInputPage의 MOOD_OPTIONS와 동일한 매핑
   영문 value → 한글 라벨 + 감정 컬러 테마
─────────────────────────────────────────── */
const MOOD_MAP = {
    happy: { label: '기쁨', color: '#FF6B5E', soft: '#FFEAE6' },
    excited: { label: '설렘', color: '#FFB648', soft: '#FFF3DE' },
    sad: { label: '우울', color: '#7B7FF0', soft: '#ECEDFD' },
    lonely: { label: '외로움', color: '#7B7FF0', soft: '#ECEDFD' },
    tired: { label: '피로', color: '#7B7FF0', soft: '#ECEDFD' },
    angry: { label: '분노', color: '#FF6B5E', soft: '#FFEAE6' },
    anxious: { label: '불안', color: '#7B7FF0', soft: '#ECEDFD' },
    focused: { label: '집중', color: '#FFB648', soft: '#FFF3DE' },
};

const DEFAULT_THEME = { color: '#7B7FF0', soft: '#ECEDFD', label: '오늘의 감정' };

/**
 * 감정 테마 조회
 * - MOOD_MAP에 등록된 영문 value면 한글 라벨 + 컬러로 변환
 * - 이미 한글이거나 매핑이 없으면 원문 그대로 라벨로 사용 (서버가 한글을 줄 수도 있으므로)
 */
const getMoodTheme = (mood) => {
    if (!mood) return DEFAULT_THEME;
    if (MOOD_MAP[mood]) return { ...MOOD_MAP[mood] };
    const matchedKey = Object.values(MOOD_MAP).find((m) => m.label === mood);
    if (matchedKey) return { ...matchedKey };
    return { ...DEFAULT_THEME, label: mood };
};

/**
 * 추천 메시지 빌더
 * - 서버가 자연어 메시지(recommendation.message 등)를 내려주면 그대로 사용
 * - 없으면 감정 라벨 기반으로 합리적인 기본 문구를 생성 (특정 감정 문구를 하드코딩하지 않음)
 */
const buildHeroMessage = (moodLabel, customMessage, trackCount) => {
    if (customMessage) return customMessage;
    if (moodLabel && moodLabel !== '오늘의 감정') {
        return `오늘 느낀 ‘${moodLabel}’에 어울리는 곡들을 골라봤어요. 너무 튀지 않으면서 지금 분위기와 잘 맞는 음악들이에요.`;
    }
    return `지금 감정에 어울리는 음악을 ${trackCount}곡 골라봤어요.`;
};

/**
 * 입력 노트 파서
 * MoodInputPage가 보내는 payload.text는
 *   "{자유 텍스트} 원하는 분위기: {태그1}, {태그2}." 형태로 합쳐져 있음.
 * 이 함수는 그 합쳐진 문자열을 받아 자유 텍스트와 분위기 태그 배열로 다시 분리한다.
 * 패턴이 없는 입력(자유 텍스트만 있거나 비어 있는 경우)도 그대로 처리한다.
 */
const VIBE_PATTERN = /\s*원하는\s*분위기\s*:\s*([^.]*)\.?\s*$/;

const parseInputNote = (rawNote) => {
    if (!rawNote || typeof rawNote !== 'string') return { freeText: '', vibes: [] };

    const match = rawNote.match(VIBE_PATTERN);
    if (!match) return { freeText: rawNote.trim(), vibes: [] };

    const freeText = rawNote.slice(0, match.index).trim();
    const vibes = match[1]
        .split(',')
        .map((v) => v.trim())
        .filter(Boolean);

    return { freeText, vibes };
};

/**
 * 생성 시각 포맷터 — "2026년 6월 28일 · 오후 3:42" 형식
 * 서버가 생성 시각을 안 주면 페이지가 로드된 시점(클라이언트 현재 시각)을 사용한다.
 */
const formatGeneratedAt = (dateInput) => {
    const d = dateInput ? new Date(dateInput) : new Date();
    if (Number.isNaN(d.getTime())) return '';

    const year = d.getFullYear();
    const month = d.getMonth() + 1;
    const date = d.getDate();
    let hours = d.getHours();
    const minutes = String(d.getMinutes()).padStart(2, '0');
    const period = hours < 12 ? '오전' : '오후';
    hours = hours % 12;
    if (hours === 0) hours = 12;

    return `${year}년 ${month}월 ${date}일 · ${period} ${hours}:${minutes}`;
};

/* ───────────────────────────────────────────
   SIDE PANEL  — 오른쪽 컨텍스트 패널 (sticky)
   화이트 배경 단일톤, 얇은 구분선으로만 구역을 나눔 (베이지 박스 사용 안 함)
   구역: 헤더(생성 시각) → 선택한 감정 → 원하는 분위기 → 직접 입력한 내용 → 추천 메시지 → 곡별 추천 이유
─────────────────────────────────────────── */
const PanelLabel = ({ children }) => <p className="mb-2.5 text-[11px] font-semibold uppercase tracking-[0.07em] text-[#A39CAC]">{children}</p>;

const getThemeBgClass = (color) => {
    switch (color) {
        case '#FF6B5E':
            return 'bg-[#FF6B5E]';
        case '#FFB648':
            return 'bg-[#FFB648]';
        case '#7B7FF0':
            return 'bg-[#7B7FF0]';
        case '#B9791E':
            return 'bg-[#B9791E]';
        default:
            return 'bg-[#A39CAC]';
    }
};

const getThemeSoftClass = (soft) => {
    switch (soft) {
        case '#FFEAE6':
            return 'bg-[#FFEAE6]';
        case '#FFF3DE':
            return 'bg-[#FFF3DE]';
        case '#ECEDFD':
            return 'bg-[#ECEDFD]';
        default:
            return 'bg-[#F1ECE3]';
    }
};

const getThemeToneClass = (soft, color) => `${getThemeSoftClass(soft)} ${getThemeBgClass(color)} bg-opacity-10`;

const getDelayClass = (delaySeconds) => `[animation-delay:${delaySeconds}s]`;

const SidePanel = ({ moodLabel, freeText, vibes, message, generatedAt, tracks, isMobile, isNarrow }) => {
    const theme = getMoodTheme(moodLabel);
    const hasInputDetails = vibes.length > 0 || !!freeText;
    const padXClass = isMobile ? 'px-[22px]' : 'px-[26px]';
    const dividerClass = isMobile ? 'mx-[22px]' : 'mx-[26px]';

    return (
        <div className={`rounded-[20px] border border-[#E5DFD3] bg-white ${isNarrow ? 'static' : 'sticky top-6'}`}>
            {/* ── 패널 헤더: 이게 뭔지 + 생성 시각 ── */}
            <div className={`flex flex-wrap items-center justify-between gap-2.5 py-[18px] ${padXClass}`}>
                <span className="flex items-center gap-1.5 text-[13px] font-bold tracking-[-0.01em] text-[#211C26]">
                    <span className={`h-[7px] w-[7px] shrink-0 rounded-full ${getThemeBgClass(theme.color)}`} />
                    추천 요약
                </span>
                {generatedAt && (
                    <span className="flex items-center gap-1 text-[11px] font-medium text-[#A39CAC]">
                        <Ic d={I.clock} size={11} color={T.inkFaint} />
                        {generatedAt}
                    </span>
                )}
            </div>

            <div className={`h-px bg-[#E5DFD3] ${dividerClass}`} />

            <div className={`py-5 ${padXClass}`}>
                {/* ── 선택한 감정 ── */}
                <div className={hasInputDetails ? 'mb-[22px]' : 'mb-0'}>
                    <PanelLabel>선택한 감정</PanelLabel>
                    <span className={`inline-flex items-center gap-1.5 rounded-full px-3 py-[5px] text-[12.5px] font-bold text-white ${getThemeBgClass(theme.color)}`}>
                        {theme.label}
                    </span>
                </div>

                {/* ── 원하는 분위기 ── */}
                {vibes.length > 0 && (
                    <div className="mb-[22px]">
                        <PanelLabel>원하는 분위기</PanelLabel>
                        <div className="flex flex-wrap gap-1.5">
                            {vibes.map((v) => (
                                <span key={v} className="rounded-full border border-[#D6CFC1] px-2.5 py-1 text-[11.5px] font-semibold text-[#6E6678]">
                                    {v}
                                </span>
                            ))}
                        </div>
                    </div>
                )}

                {/* ── 직접 입력한 내용 ── */}
                {freeText && (
                    <div className="mb-1">
                        <PanelLabel>직접 입력한 내용</PanelLabel>
                        <p className={`m-0 border-l-2 pl-3 text-[13.5px] leading-[1.65] text-[#211C26] ${getThemeSoftClass(theme.soft)}`}>
                            {freeText}
                        </p>
                    </div>
                )}

                {/* 입력 정보가 감정 선택뿐이었던 경우 안내 */}
                {!hasInputDetails && (
                    <p className="m-0 text-[12.5px] leading-[1.6] text-[#A39CAC]">
                        감정 선택만으로 추천했어요.
                    </p>
                )}
            </div>

            <div className={`h-px bg-[#E5DFD3] ${dividerClass}`} />

            {/* ── 추천 한 줄 메시지 ── */}
            <div className={`py-[18px] ${padXClass}`}>
                <p className="m-0 text-[13.5px] font-medium leading-[1.65] text-[#6E6678]">
                    {message}
                </p>
            </div>

            <div className={`h-px bg-[#E5DFD3] ${dividerClass}`} />

            {/* ── 곡별 추천 이유 ── */}
            <div className={`${padXClass} pt-5 ${isMobile ? 'pb-[22px]' : 'pb-[26px]'}`}>
                <PanelLabel>왜 이 곡들일까요</PanelLabel>

                <div className="flex flex-col gap-4">
                    {tracks.map((track, index) => (
                        <div key={track.track_id || `${track.name}-${index}`} className="flex items-start gap-2.5">
                            <span className={`mt-px w-4 shrink-0 text-[11px] font-bold ${getThemeBgClass(theme.color)}`}>
                                {String(index + 1).padStart(2, '0')}
                            </span>
                            <div className="min-w-0">
                                <p className="mb-[3px] truncate text-[12.5px] font-bold text-[#211C26]">
                                    {track.name}
                                </p>
                                {track.reason && (
                                    <p className="m-0 text-[12.5px] leading-[1.6] text-[#6E6678]">
                                        {track.reason}
                                    </p>
                                )}
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
};

/* ───────────────────────────────────────────
   ALBUM COVER  — 원본 유지, 변형·오버레이 없음
─────────────────────────────────────────── */
const AlbumCover = ({ track, size }) => {
    const [imageFailed, setImageFailed] = useState(false);
    const hasAlbumImage = Boolean(track.album_image_url) && !imageFailed;
    const sizeClass = size <= 64 ? 'h-[64px] w-[64px]' : 'h-[72px] w-[72px]';
    const labelClass = size <= 64 ? 'text-[10px]' : 'text-[11px]';

    return (
        <div className={`shrink-0 overflow-hidden rounded-[14px] ${sizeClass} bg-[linear-gradient(135deg,#FFEAE6_0%,#ECEDFD_100%)]`}>
            {hasAlbumImage ? (
                <img
                    src={track.album_image_url}
                    alt={`${track.album_name || track.name} 앨범 커버`}
                    onError={() => setImageFailed(true)}
                    className="block h-full w-full object-cover"
                />
            ) : (
                <div className="relative flex h-full w-full items-center justify-center overflow-hidden bg-[linear-gradient(135deg,#FFEAE6_0%,#ECEDFD_55%,#FFF3DE_100%)]">
                    <div className="absolute inset-0 bg-[radial-gradient(circle_at_30%_30%,rgba(255,255,255,0.52)_0%,transparent_36%),radial-gradient(circle_at_75%_70%,rgba(255,255,255,0.32)_0%,transparent_40%)]" />
                    <div className="relative z-10 flex h-full w-full flex-col items-center justify-center gap-1 p-2 text-center">
                        <Ic d={I.music} size={18} color={T.inkFaint} />
                        <span className={`line-clamp-2 overflow-hidden text-ellipsis font-extrabold leading-[1.1] tracking-[-0.03em] text-[#6E6678] ${labelClass}`}>
                            {track.album_name || track.name}
                        </span>
                    </div>
                </div>
            )}
        </div>
    );
};

/* ───────────────────────────────────────────
   TRACK CARD  (Spotify 정책 준수)
   - 앨범 커버 원본 유지 (변형·오버레이 없음, 라운드 처리만)
   - 곡명·아티스트·앨범커버 → Spotify 링크
   - "Provided by Spotify" 명시
   - 추천 이유를 카드의 1등 요소로 — 말풍선 형태로 항상 펼쳐서 보여줌
─────────────────────────────────────────── */
const TrackCard = ({ track, index, isMobile, theme, moodKey, initialLiked = false, onLike, onUnlike }) => {
    const [liked, setLiked] = useState(false);
    const [hov, setHov] = useState(false);
    const coverSize = isMobile ? 64 : 72;
    const spotifyUrl =
        track.spotify_url ||
        `https://open.spotify.com/search/${encodeURIComponent(`${track.name || ''} ${track.artist_name || ''}`.trim())}`;
    const favoriteTrackId = track.track_id || `${track.name || ''}-${track.artist_name || ''}`;
    useEffect(() => {
        setLiked(Boolean(initialLiked));
    }, [initialLiked]);

    const favoritePayload = {
        track_id: favoriteTrackId,
        track_name: track.name,
        artist_name: track.artist_name,
        album_name: track.album_name || null,
        album_image_url: track.album_image_url || null,
        spotify_url: track.spotify_url || null,
        duration_ms: track.duration_ms || null,
        mood: moodKey || null,
        reason: track.reason || null,
    };

    const handleLikeToggle = async () => {
        try {
            if (liked) {
                await removeFavorite(favoriteTrackId);
                setLiked(false);
                onUnlike?.(favoriteTrackId);
            } else {
                await saveFavorite(favoritePayload);
                setLiked(true);
                onLike?.(favoriteTrackId);
            }
        } catch (error) {
            console.error('좋아요 상태를 저장하지 못했어요.', error);
        }
    };

    return (
        <div
            onMouseEnter={() => setHov(true)}
            onMouseLeave={() => setHov(false)}
            className={`rounded-[22px] border bg-white transition-all duration-200 ${hov ? 'border-[#D6CFC1] -translate-y-0.5 shadow-[0_16px_40px_-16px_rgba(33,28,38,0.14)]' : 'border-[#E5DFD3] shadow-[0_1px_0_rgba(33,28,38,0.02)]'} ${isMobile ? 'p-4' : 'px-5 py-[18px]'}`}
        >
            {/* 메인 행 */}
            <div className={`flex items-center ${isMobile ? 'gap-3' : 'gap-4'}`}>
                {/* 순번 */}
                <span className="w-[18px] shrink-0 text-center text-[12px] font-bold text-[#A39CAC]">
                    {String(index + 1).padStart(2, '0')}
                </span>

                {/* 앨범 커버 — Spotify 링크, 원본 유지 */}
                {spotifyUrl ? (
                    <a
                        href={spotifyUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="block shrink-0 overflow-hidden rounded-[14px] leading-none"
                        aria-label={`${track.name} Spotify에서 열기`}
                    >
                        <AlbumCover track={track} size={coverSize} />
                    </a>
                ) : (
                    <AlbumCover track={track} size={coverSize} />
                )}

                {/* 트랙 정보 */}
                <div className="min-w-0 flex-1">
                    {spotifyUrl ? (
                        <a
                            href={spotifyUrl}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="block truncate text-[15.5px] font-bold tracking-[-0.01em] text-[#211C26] no-underline transition-colors duration-150 hover:text-[#7B7FF0]"
                        >
                            {track.name}
                        </a>
                    ) : (
                        <span className="block truncate text-[15.5px] font-bold tracking-[-0.01em] text-[#211C26]">
                            {track.name}
                        </span>
                    )}

                    <div className="mt-[3px] flex flex-wrap items-center gap-x-1.5 gap-y-0.5">
                        {spotifyUrl ? (
                            <a
                                href={spotifyUrl}
                                target="_blank"
                                rel="noopener noreferrer"
                                className={`max-w-[220px] truncate text-[13px] font-medium text-[#6E6678] no-underline hover:text-[#211C26] ${isMobile ? 'max-w-[140px]' : ''}`}
                            >
                                {track.artist_name}
                            </a>
                        ) : (
                            <span className="text-[13px] font-medium text-[#6E6678]">{track.artist_name}</span>
                        )}
                        {formatDuration(track.duration_ms) && (
                            <>
                                <span className="text-[10px] text-[#E5DFD3]">·</span>
                                <span className="text-[12px] text-[#A39CAC]">
                                    {formatDuration(track.duration_ms)}
                                </span>
                            </>
                        )}
                    </div>
                </div>

                {/* 액션 버튼 */}
                <div className="flex shrink-0 items-center gap-2">
                    <button
                        onClick={handleLikeToggle}
                        aria-label={liked ? '좋아요 취소' : '좋아요'}
                        className={`flex h-9 w-9 cursor-pointer items-center justify-center rounded-full border-[1.5px] transition-all duration-200 ${liked ? 'border-[#FF6B5E] bg-[#FFEAE6]' : 'border-[#E5DFD3] bg-transparent'}`}
                    >
                        <Ic d={I.heart} size={15} color={liked ? T.joy : T.inkFaint} fill={liked ? T.joy : 'none'} />
                    </button>

                    {spotifyUrl && (
                        <a
                            href={spotifyUrl}
                            target="_blank"
                            rel="noopener noreferrer"
                            aria-label="Spotify에서 듣기"
                            className="flex h-9 w-9 items-center justify-center rounded-full bg-[#1ED760] text-[#191414] no-underline transition-transform duration-150 hover:scale-[1.06] hover:brightness-110"
                        >
                            <Ic d={I.play} size={14} color={T.spotBlack} fill={T.spotBlack} sw={0} />
                        </a>
                    )}
                </div>
            </div>

            {/* Provided by Spotify */}
            <div className={`mt-3 flex items-center gap-1 ${isMobile ? 'ml-0' : 'ml-[34px]'}`}>
                <SpotifyMark size={10} />
                <span className="text-[10.5px] text-[#A39CAC]">Provided by Spotify</span>
            </div>
        </div>
    );
};

/* ───────────────────────────────────────────
   EMPTY STATE
─────────────────────────────────────────── */
const EmptyState = ({ isMobile, title, description, ctaLabel }) => (
    <div className={`mx-auto max-w-[480px] rounded-[28px] border border-[#E5DFD3] bg-white text-center shadow-[0_8px_32px_-12px_rgba(33,28,38,0.10)] ${isMobile ? 'px-6 py-12' : 'px-12 py-16'}`}>
        <div className="mx-auto mb-5 flex h-14 w-14 items-center justify-center rounded-2xl bg-[#ECEDFD]">
            <Ic d={I.music} size={26} color={T.calm} />
        </div>
        <h2 className="mb-2.5 text-[20px] font-extrabold tracking-[-0.02em] text-[#211C26]">
            {title || '아직 추천 결과가 없어요'}
        </h2>
        <p className="mb-7 text-[14px] leading-[1.7] text-[#6E6678]">
            {description || '감정을 선택하고 추천을 받아야 결과가 표시돼요.'}
        </p>
        <Link
            to="/mood-input"
            className="inline-flex items-center gap-2 rounded-full bg-[#211C26] px-7 py-3.5 text-[15px] font-bold text-[#FAF8F4] no-underline"
        >
            <Ic d={I.smile} size={17} color={T.bg} />
            {ctaLabel || '감정 입력하러 가기'}
        </Link>
    </div>
);

/* ═══════════════════════════════════════════
   PAGE
═══════════════════════════════════════════ */
export default function RecommendationPage() {
    const location = useLocation();
    const persistedState = getSavedState();
    const bp = useBreakpoint();
    const isMobile = bp === 'mobile';
    const isTablet = bp === 'tablet';
    const isNarrow = isMobile || isTablet;
    const [dashboardSummary, setDashboardSummary] = useState(null);
    const [dashboardLoaded, setDashboardLoaded] = useState(Boolean(location.state?.result || persistedState?.result));
    const [dashboardError, setDashboardError] = useState('');
    const [favoriteIds, setFavoriteIds] = useState(new Set());
    const [toastVisible, setToastVisible] = useState(false);
    const [toastMessage, setToastMessage] = useState('좋아요가 취소되었어요');
    const [toastTimer, setToastTimer] = useState(null);

    const wrapClass = `mx-auto max-w-[1240px] ${isMobile ? 'px-5' : isTablet ? 'min-[560px]:px-7' : 'min-[900px]:px-10 px-5'}`;
    const innerWrapClass = 'mx-auto max-w-[1080px]';

    /* ── 데이터 ── */
    const remoteResult = dashboardSummary
        ? {
              mood: dashboardSummary.latest_recommendation?.mood || dashboardSummary.today_mood?.mood || '',
              tracks: dashboardSummary.latest_recommendation?.tracks || [],
              mood_record: dashboardSummary.today_mood || null,
              recommendation: dashboardSummary.latest_recommendation || null,
          }
        : null;
    const result = location.state?.result ?? persistedState?.result ?? remoteResult ?? null;
    const payload =
        location.state?.payload ??
        persistedState?.payload ??
        (remoteResult
            ? {
                  mood: remoteResult.mood,
                  text: remoteResult.recommendation?.query || remoteResult.mood_record?.text || '',
              }
            : null);
    const generatedAt =
        location.state?.result?.recommendation?.created_at ??
        persistedState?.generatedAt ??
        dashboardSummary?.latest_recommendation?.created_at ??
        dashboardSummary?.today_mood?.created_at ??
        null;

    useEffect(() => {
        if (location.state?.result || location.state?.payload) {
            saveState({
                result: location.state?.result ?? null,
                payload: location.state?.payload ?? null,
                generatedAt: new Date().toISOString(),
            });
        }
    }, [location.state]);

    useEffect(() => {
        const persisted = getSavedState();
        if (location.state?.result || persisted?.result) {
            setDashboardLoaded(true);
            return;
        }

        let active = true;
        const loadDashboard = async () => {
            try {
                const summary = await getMoodDashboard();
                if (!active) return;
                setDashboardSummary(summary);
            } catch (error) {
                if (!active) return;
                setDashboardError(error.message || '최근 추천을 불러오지 못했어요.');
            } finally {
                if (active) setDashboardLoaded(true);
            }
        };

        loadDashboard();
        return () => {
            active = false;
        };
    }, [location.state]);

    useEffect(() => {
        let active = true;
        getFavorites()
            .then((data) => {
                if (!active) return;
                const items = Array.isArray(data) ? data : data?.items || [];
                setFavoriteIds(new Set(items.map((item) => item.track_id)));
            })
            .catch(() => {
                if (!active) return;
                setFavoriteIds(new Set());
            });

        return () => {
            active = false;
        };
    }, []);

    const showFavoriteToast = (message) => {
        setToastMessage(message);
        setToastVisible(true);
        if (toastTimer) clearTimeout(toastTimer);
        const timer = setTimeout(() => setToastVisible(false), 2800);
        setToastTimer(timer);
    };

    const handleLike = (trackId) => {
        setFavoriteIds((prev) => {
            const next = new Set(prev);
            next.add(trackId);
            return next;
        });
        showFavoriteToast('좋아요에 추가되었어요');
    };

    const handleUnlike = (trackId) => {
        setFavoriteIds((prev) => {
            const next = new Set(prev);
            next.delete(trackId);
            return next;
        });
        showFavoriteToast('좋아요가 취소되었어요');
    };

    useEffect(
        () => () => {
            if (toastTimer) clearTimeout(toastTimer);
        },
        [toastTimer]
    );

    const tracks = result?.tracks ?? result?.recommendation?.tracks ?? [];
    const mood = result?.mood ?? result?.mood_record?.mood ?? payload?.mood ?? '';
    const rawNote = payload?.text ?? result?.recommendation?.query ?? result?.mood_record?.text ?? '';
    const { freeText, vibes } = parseInputNote(rawNote);
    const moodLabel = getMoodTheme(result?.recommendation?.mood || mood).label;
    const theme = getMoodTheme(result?.recommendation?.mood || mood);
    const heroMessage = buildHeroMessage(moodLabel, result?.recommendation?.message, tracks.length);
    const generatedAtLabel = formatGeneratedAt(generatedAt);

    return (
        <div className="min-h-screen overflow-x-hidden bg-[#FAF8F4] font-[Pretendard,system-ui,sans-serif] text-[#211C26] antialiased">
            <FavoriteToast visible={toastVisible} message={toastMessage} onClose={() => setToastVisible(false)} />

            <Header />

            <main className={`relative overflow-hidden ${isMobile ? 'pt-[100px] pb-[72px]' : 'pt-[132px] pb-[120px]'}`}>
                {/* 배경 글로우 — 랜딩 hero와 동일 */}
                <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(50%_40%_at_15%_10%,rgba(255,107,94,0.07)_0%,transparent_65%),radial-gradient(40%_35%_at_85%_5%,rgba(123,127,240,0.07)_0%,transparent_65%)]" />

                <div className={`relative z-10 ${wrapClass}`}>
                    {/* ── 페이지 헤더 ── */}
                    <div className={`fu mb-8 flex flex-wrap justify-between gap-4 ${isNarrow ? 'items-start' : 'items-center'} ${getDelayClass(0.05)}`}>
                        <div>
                            {/* 배지 — 랜딩 hero pill badge와 동일 패턴 */}
                            <span className="mb-4 inline-flex items-center gap-1.5 rounded-full border border-[#E5DFD3] bg-white px-3.5 py-[6px] pl-2.5 text-[12px] font-semibold text-[#6E6678]">
                                <Ic d={I.sparkles} size={13} color={T.joy} /> 추천 결과
                            </span>

                            <h1 className={`mb-3.5 font-extrabold leading-[1.18] tracking-[-0.035em] text-[#211C26] ${isMobile ? 'text-[clamp(26px,8vw,36px)]' : 'text-[clamp(30px,4vw,44px)]'}`}>
                                지금 분위기에 맞는
                                <br />
                                <span className="bg-[linear-gradient(100deg,#FF6B5E_10%,#FFB648_55%,#7B7FF0_100%)] bg-clip-text text-transparent">
                                    추천 곡을 골랐어요
                                </span>
                            </h1>
                            <p className={`max-w-[480px] leading-[1.7] text-[#6E6678] ${isMobile ? 'text-[15px]' : 'text-[16px]'}`}>
                                감정 선택과 입력한 문장을 바탕으로 지금 들으면 좋은 트랙을 골랐어요.
                            </p>
                        </div>

                        <div className="flex flex-col items-end gap-2.5">
                            <LinkBtn to="/mood-input">
                                <Ic d={I.refresh} size={15} color={T.inkSoft} /> 다시 추천받기
                            </LinkBtn>
                        </div>
                    </div>

                    {/* ══════════════════════════════════════
                        여기부터 신규 디자인 영역
                    ══════════════════════════════════════ */}

                    {/* ── 결과 없음 ── */}
                    {!dashboardLoaded && !result ? (
                        <div className={`fu ${getDelayClass(0.1)}`}>
                            <EmptyState
                                isMobile={isMobile}
                                title="추천 결과를 불러오는 중이에요"
                                description="잠시만 기다려 주세요."
                                ctaLabel="불러오는 중"
                            />
                        </div>
                    ) : !result ? (
                        <div className={`fu ${getDelayClass(0.1)}`}>
                            <EmptyState
                                isMobile={isMobile}
                                title={dashboardError ? '최근 추천을 불러오지 못했어요' : '아직 추천 결과가 없어요'}
                                description={
                                    dashboardError ? dashboardError : '감정을 선택하고 추천을 받아야 결과가 표시돼요.'
                                }
                                ctaLabel="감정 입력하러 가기"
                            />
                        </div>
                    ) : (
                        <div className={`fu ${getDelayClass(0.1)}`}>
                            <div
                                className={`${innerWrapClass} grid items-start ${isNarrow ? 'grid-cols-1' : 'grid-cols-[minmax(0,1fr)_340px]'} ${isMobile ? 'gap-7' : isTablet ? 'gap-8' : 'gap-10'}`}
                            >
                                {/* ── 좌: 곡 목록 ── */}
                                <div className={`${isNarrow ? 'order-2' : 'order-1'} min-w-0`}>
                                    {/* 곡 수 라벨 */}
                                    <div className="mb-3.5 flex items-center justify-between">
                                        <span className="text-[12px] font-bold uppercase tracking-[0.07em] text-[#A39CAC]">
                                            추천 곡 · {tracks.length}곡
                                        </span>
                                    </div>

                                    {/* 트랙 목록 */}
                                    <div className="flex flex-col gap-2.5">
                                        {tracks.map((track, index) => (
                                            <div
                                                key={track.track_id || `${track.name}-${index}`}
                                                className={`track-in ${getDelayClass(0.12 + index * 0.07)}`}
                                            >
                                                <TrackCard
                                                    track={track}
                                                    index={index}
                                                    isMobile={isMobile}
                                                    theme={theme}
                                                    moodKey={mood}
                                                    onLike={handleLike}
                                                    onUnlike={handleUnlike}
                                                    initialLiked={favoriteIds.has(
                                                        track.track_id ||
                                                            `${track.name || ''}-${track.artist_name || ''}`
                                                    )}
                                                />
                                            </div>
                                        ))}
                                    </div>

                                    {/* 하단 액션 바 */}
                                    <div className={`mt-7 flex flex-wrap items-center justify-between gap-3 rounded-[20px] border border-[#E5DFD3] bg-white ${isMobile ? 'px-[18px] py-4' : 'px-6 py-[18px]'}`}>
                                        <span className="flex items-center gap-1.5 text-[12.5px] font-semibold text-[#A39CAC]">
                                            <SpotifyMark size={14} />곡 정보:{' '}
                                            <strong className="ml-0.5 font-bold text-[#6E6678]">
                                                Provided by Spotify
                                            </strong>
                                        </span>
                                        <div className="flex flex-wrap items-center gap-2.5">
                                            <a
                                                href="https://open.spotify.com"
                                                target="_blank"
                                                rel="noopener noreferrer"
                                                className="inline-flex items-center gap-1.5 rounded-full bg-[#1ED760] px-[18px] py-[9px] text-[12.5px] font-extrabold text-[#191414] no-underline transition-transform duration-150 hover:-translate-y-px hover:brightness-105"
                                            >
                                                <Ic
                                                    d={I.play}
                                                    size={11}
                                                    color={T.spotBlack}
                                                    fill={T.spotBlack}
                                                    sw={0}
                                                />
                                                모두 Spotify에서 듣기
                                            </a>
                                        </div>
                                    </div>
                                </div>

                                {/* ── 우: 감정 · 분위기 · 입력 내용 · 곡별 추천 이유 패널 (sticky) ── */}
                                <div className={isNarrow ? 'order-1' : 'order-2'}>
                                    <SidePanel
                                        moodLabel={moodLabel}
                                        freeText={freeText}
                                        vibes={vibes}
                                        message={heroMessage}
                                        generatedAt={generatedAtLabel}
                                        tracks={tracks}
                                        isMobile={isMobile}
                                        isNarrow={isNarrow}
                                    />
                                </div>
                            </div>
                        </div>
                    )}
                </div>
            </main>

            <Footer wrap={wrapClass} isMobile={isMobile} />
        </div>
    );
}
