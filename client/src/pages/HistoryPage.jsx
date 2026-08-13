import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import Header from '../components/Header';
import Footer from '../components/Footer';
import { getMoodHistory } from '../services/apiClient';

/* ─────────────────────────────────────────
   ICONS
───────────────────────────────────────── */
const Ic = ({ d, size = 20, color = 'currentColor', fill = 'none', sw = 1.8, className = '' }) => (
    <svg
        width={size}
        height={size}
        viewBox="0 0 24 24"
        fill={fill}
        stroke={color}
        strokeWidth={sw}햐
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
    sparkles:
        'M9.937 15.5A2 2 0 0 0 8.5 14.063l-6.135-1.582a.5.5 0 0 1 0-.962L8.5 9.936A2 2 0 0 0 9.937 8.5l1.582-6.135a.5.5 0 0 1 .963 0L14.063 8.5A2 2 0 0 0 15.5 9.937l6.135 1.581a.5.5 0 0 1 0 .964L15.5 14.063a2 2 0 0 0-1.437 1.437l-1.582 6.135a.5.5 0 0 1-.963 0z',
    calHeart: [
        'M8 2v4M16 2v4M3 10h18M3 6a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h18a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2H3z',
        'M12 17a2 2 0 0 0 2-2c0-1-1-2-2-3-1 1-2 2-2 3a2 2 0 0 0 2 2z',
    ],
    chevL: 'M15 18l-6-6 6-6',
    chevR: 'M9 18l6-6-6-6',
    chevDown: 'M6 9l6 6 6-6',
    chevUp: 'M18 15l-6-6-6 6',
    music: 'M9 18V5l12-2v13M9 18a3 3 0 1 1-6 0 3 3 0 0 1 6 0zm12-2a3 3 0 1 1-6 0 3 3 0 0 1 6 0z',
    play: 'M6 3l15 9-15 9V3z',
    heart: 'M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z',
    bulb: [
        'M9 18h6',
        'M10 22h4',
        'M12 2a7 7 0 0 1 7 7c0 2.38-1.19 4.47-3 5.74V17a2 2 0 0 1-2 2h-4a2 2 0 0 1-2-2v-2.26C6.19 13.47 5 11.38 5 9a7 7 0 0 1 7-7z',
    ],
    bar: ['M3 3v18h18', 'M7 16v-5', 'M11 16v-9', 'M15 16v-3'],
    cloud: 'M17.5 19H9a7 7 0 1 1 6.71-9h1.79a4.5 4.5 0 1 1 0 9z',
    pen: 'M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z',
};

/* ─────────────────────────────────────────
   SPOTIFY MARK
───────────────────────────────────────── */
const SpotifyMark = ({ size = 16 }) => (
    <svg width={size} height={size} viewBox="0 0 24 24" className="inline-block shrink-0">
        <circle cx="12" cy="12" r="12" fill="#1ED760" />
        <path
            d="M17.5 10.7c-3-1.8-7.9-2-10.7-1.1a.7.7 0 1 1-.4-1.4c3.2-1 8.7-.8 12.1 1.2a.7.7 0 0 1-.7 1.3h-.3zm-.1 2.9c-2.5-1.5-6.3-2-9.3-1.1a.6.6 0 1 1-.3-1.1c3.4-1 7.6-.5 10.5 1.2a.6.6 0 0 1-.6 1h-.3zm-.3 2.8c-2.2-1.3-4.9-1.6-8-.9a.5.5 0 1 1-.2-1c3.4-.8 6.4-.4 8.8 1a.5.5 0 0 1-.6.9z"
            fill="white"
        />
    </svg>
);

/* ─────────────────────────────────────────
   RESPONSIVE HOOK
───────────────────────────────────────── */
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

/* ─────────────────────────────────────────
   VIBE PATTERN PARSER
   RecommendationPage의 parseInputNote와 동일한 로직.
   payload.text = "{자유텍스트} 원하는 분위기: {태그1}, {태그2}." 형태를 분리.
───────────────────────────────────────── */
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

/* ─────────────────────────────────────────
   MOOD MAP
───────────────────────────────────────── */
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
const DEFAULT_THEME = { color: '#7B7FF0', soft: '#ECEDFD', label: '기록' };
const getMoodTheme = (mood) => {
    if (!mood) return DEFAULT_THEME;
    if (MOOD_MAP[mood]) return { ...MOOD_MAP[mood] };
    const matched = Object.values(MOOD_MAP).find((m) => m.label === mood);
    return matched ? { ...matched } : { ...DEFAULT_THEME, label: mood };
};

const getThemeBgClass = (color) => {
    switch (color) {
        case '#FF6B5E':
            return 'bg-[#FF6B5E]';
        case '#FFB648':
            return 'bg-[#FFB648]';
        case '#7B7FF0':
            return 'bg-[#7B7FF0]';
        case '#9B8FD4':
            return 'bg-[#9B8FD4]';
        case '#B9791E':
            return 'bg-[#B9791E]';
        case '#E8805A':
            return 'bg-[#E8805A]';
        case '#C97EB6':
            return 'bg-[#C97EB6]';
        default:
            return 'bg-[#A39CAC]';
    }
};

const getThemeTextClass = (color) => {
    switch (color) {
        case '#FF6B5E':
            return 'text-[#FF6B5E]';
        case '#FFB648':
            return 'text-[#FFB648]';
        case '#7B7FF0':
            return 'text-[#7B7FF0]';
        case '#9B8FD4':
            return 'text-[#9B8FD4]';
        case '#B9791E':
            return 'text-[#B9791E]';
        case '#E8805A':
            return 'text-[#E8805A]';
        case '#C97EB6':
            return 'text-[#C97EB6]';
        default:
            return 'text-[#211C26]';
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
        case '#F1ECE3':
            return 'bg-[#F1ECE3]';
        case '#EDEAFC':
            return 'bg-[#EDEAFC]';
        case '#FFF0EC':
            return 'bg-[#FFF0EC]';
        default:
            return 'bg-[#F1ECE3]';
    }
};

const getThemeBorderLeftClass = (soft) => {
    switch (soft) {
        case '#FFEAE6':
            return 'border-l-[#FFEAE6]';
        case '#FFF3DE':
            return 'border-l-[#FFF3DE]';
        case '#ECEDFD':
            return 'border-l-[#ECEDFD]';
        case '#F1ECE3':
            return 'border-l-[#F1ECE3]';
        case '#EDEAFC':
            return 'border-l-[#EDEAFC]';
        case '#FFF0EC':
            return 'border-l-[#FFF0EC]';
        default:
            return 'border-l-[#F1ECE3]';
    }
};

const getThemeToneClass = (soft, color) => `${getThemeSoftClass(soft)} ${getThemeTextClass(color)}`;
const getDelayClass = (seconds) => `[animation-delay:${seconds}s]`;
const getProgressWidthClass = (count) => {
    const safe = Math.max(1, Math.min(4, count));
    switch (safe) {
        case 1:
            return 'w-1/4';
        case 2:
            return 'w-1/2';
        case 3:
            return 'w-3/4';
        case 4:
        default:
            return 'w-full';
    }
};

/* ─────────────────────────────────────────
   DATE HELPERS
───────────────────────────────────────── */
const pad2 = (n) => String(n).padStart(2, '0');
const toKey = (y, m, d) => `${y}-${pad2(m + 1)}-${pad2(d)}`;
const WEEKDAYS = ['월', '화', '수', '목', '금', '토', '일'];

const buildCalendarGrid = (year, month) => {
    const firstDay = new Date(year, month, 1);
    const startOffset = (firstDay.getDay() + 6) % 7;
    const daysInMonth = new Date(year, month + 1, 0).getDate();
    const cells = [];
    for (let i = 0; i < startOffset; i++) cells.push(null);
    for (let d = 1; d <= daysInMonth; d++) cells.push(d);
    while (cells.length % 7 !== 0) cells.push(null);
    const rows = [];
    for (let i = 0; i < cells.length; i += 7) rows.push(cells.slice(i, i + 7));
    return rows;
};

const formatYMDLabel = (year, month, day) => `${year}.${pad2(month + 1)}.${pad2(day)}`;
const formatShortDate = (dateStr) => {
    const parts = dateStr.split('-');
    return parts.length !== 3 ? dateStr : `${parts[1]}.${parts[2]}`;
};

/* ─────────────────────────────────────────
   DUMMY DATA
───────────────────────────────────────── */
const buildDummyHistory = (year, month) => {
    const sample = [
        {
            day: 28,
            mood: 'tired',
            rawText: '5시간밖에 못 자서 잔잔한 스탠다드 재즈가 듣고싶어.. 원하는 분위기: 감성적인, 차분한, 잔잔한.',
            useJazz: true,
        },
        {
            day: 27,
            mood: 'tired',
            rawText: '오늘 좀 피곤하고 아무것도 하기 싫었어요. 원하는 분위기: 잔잔한, 위로되는.',
        },
        { day: 25, mood: 'excited', rawText: '내일 여행 가는 생각에 계속 들떴어요. 원하는 분위기: 신나는, 들뜨는.' },
        { day: 23, mood: 'sad', rawText: '괜히 마음이 가라앉는 하루였어요. 원하는 분위기: 잔잔한.' },
        { day: 21, mood: 'focused', rawText: '집중해서 할 일을 끝낸 날.' },
        { day: 18, mood: 'happy', rawText: '친구들과 즐거운 시간을 보냈어요. 원하는 분위기: 신나는, 밝은.' },
    ];

    const dummyTracks = [
        {
            track_id: 'd1',
            name: 'Dynamite',
            artist_name: 'BTS',
            album_image_url: 'https://images.unsplash.com/photo-1493225457124-a3eb161ffa5f?w=200&q=80',
            spotify_url: 'https://open.spotify.com',
            reason: '밝고 리듬감 있는 곡으로 기분을 끌어올려줘요.',
        },
        {
            track_id: 'd2',
            name: 'Good Days',
            artist_name: 'SZA',
            album_image_url: 'https://images.unsplash.com/photo-1514525253161-7a46d19cd819?w=200&q=80',
            spotify_url: 'https://open.spotify.com',
            reason: '따뜻한 멜로디가 마음을 편하게 해줘요.',
        },
    ];
    const jazzTracks = [
        {
            track_id: 'j1',
            name: 'Autumn Leaves',
            artist_name: 'Bill Evans Trio',
            album_image_url: 'https://images.unsplash.com/photo-1493225457124-a3eb161ffa5f?w=200&q=80',
            spotify_url: 'https://open.spotify.com',
            reason: '느린 템포의 피아노 트리오 연주가 차분하게 마음을 가라앉혀줘요.',
        },
        {
            track_id: 'j2',
            name: 'My Funny Valentine',
            artist_name: 'Chet Baker',
            album_image_url: 'https://images.unsplash.com/photo-1514525253161-7a46d19cd819?w=200&q=80',
            spotify_url: 'https://open.spotify.com',
            reason: '담백한 보컬과 트럼펫이 잔잔하게 흘러가는 곡이에요.',
        },
    ];

    const records = sample.map((s) => ({
        date: toKey(year, month, s.day),
        mood: s.mood,
        rawText: s.rawText || '',
        tracks: s.useJazz ? jazzTracks : dummyTracks,
    }));

    const moodCounts = records.reduce((acc, r) => {
        acc[r.mood] = (acc[r.mood] || 0) + 1;
        return acc;
    }, {});
    const topMoodKey = Object.entries(moodCounts).sort((a, b) => b[1] - a[1])[0]?.[0] || null;

    // 더미는 rawText에 분위기가 포함된 형태로 저장 → 파싱해서 집계
    const allVibes = records.flatMap((r) => parseInputNote(r.rawText).vibes);
    const vibeCounts = allVibes.reduce((acc, v) => {
        acc[v] = (acc[v] || 0) + 1;
        return acc;
    }, {});
    const topVibe = Object.entries(vibeCounts).sort((a, b) => b[1] - a[1])[0]?.[0] || null;

    return {
        summary: { recordedDays: records.length, topMood: topMoodKey, topVibe, moodCounts },
        records,
    };
};

/* ─────────────────────────────────────────
   SUMMARY CARD
───────────────────────────────────────── */
function SummaryCard({ icon, iconBg, iconColor, label, value, valueColor }) {
    return (
        <div className="flex items-center gap-4 bg-white border border-[#E5DFD3] rounded-3xl px-5 py-5 sm:px-6 sm:py-6">
            <div className={`w-12 h-12 rounded-2xl flex items-center justify-center shrink-0 ${getThemeSoftClass(iconBg)}`}>
                <Ic d={icon} size={22} color={iconColor} />
            </div>
            <div className="min-w-0">
                <p className="text-[11px] font-bold text-[#A39CAC] uppercase tracking-[0.06em] mb-1">{label}</p>
                <p className={`text-[19px] font-extrabold tracking-[-0.02em] truncate ${valueColor ? getThemeTextClass(valueColor) : 'text-[#211C26]'}`}>
                    {value}
                </p>
            </div>
        </div>
    );
}

/* ─────────────────────────────────────────
   YEAR / MONTH PICKER
───────────────────────────────────────── */
const MONTH_LABELS = ['1월', '2월', '3월', '4월', '5월', '6월', '7월', '8월', '9월', '10월', '11월', '12월'];

function YearMonthPicker({ year, month, onChange, onClose }) {
    const [pickerYear, setPickerYear] = useState(year);
    return (
        <div
            className="absolute left-0 top-[calc(100%+8px)] z-30 w-[260px] bg-white border border-[#E5DFD3] rounded-2xl p-4 shadow-[0_16px_40px_-12px_rgba(33,28,38,0.18)]"
            role="dialog"
            aria-label="년월 선택"
        >
            <div className="flex items-center justify-between mb-3">
                <button
                    onClick={() => setPickerYear((y) => y - 1)}
                    aria-label="이전 연도"
                    className="w-7 h-7 rounded-full flex items-center justify-center hover:bg-[#F1ECE3] transition-colors"
                >
                    <Ic d={I.chevL} size={14} color="#6E6678" />
                </button>
                <span className="text-[14px] font-extrabold text-[#211C26]">{pickerYear}년</span>
                <button
                    onClick={() => setPickerYear((y) => y + 1)}
                    aria-label="다음 연도"
                    className="w-7 h-7 rounded-full flex items-center justify-center hover:bg-[#F1ECE3] transition-colors"
                >
                    <Ic d={I.chevR} size={14} color="#6E6678" />
                </button>
            </div>
            <div className="grid grid-cols-4 gap-[6px]">
                {MONTH_LABELS.map((label, idx) => {
                    const isActive = pickerYear === year && idx === month;
                    return (
                        <button
                            key={label}
                            onClick={() => {
                                onChange(pickerYear, idx);
                                onClose();
                            }}
                            className={`text-[12.5px] font-semibold py-2 rounded-lg transition-colors ${
                                isActive
                                    ? 'bg-[#211C26] text-white'
                                    : 'text-[#6E6678] hover:bg-[#F1ECE3] hover:text-[#211C26]'
                            }`}
                        >
                            {label}
                        </button>
                    );
                })}
            </div>
        </div>
    );
}

/* ─────────────────────────────────────────
   CALENDAR
───────────────────────────────────────── */
function MoodCalendar({ year, month, onPrevMonth, onNextMonth, onJumpTo, recordsByDate, selectedDate, onSelectDate }) {
    const grid = useMemo(() => buildCalendarGrid(year, month), [year, month]);
    const todayKey = toKey(new Date().getFullYear(), new Date().getMonth(), new Date().getDate());
    const [pickerOpen, setPickerOpen] = useState(false);

    useEffect(() => {
        if (!pickerOpen) return;
        const closeOnOutside = () => setPickerOpen(false);
        document.addEventListener('click', closeOnOutside);
        return () => document.removeEventListener('click', closeOnOutside);
    }, [pickerOpen]);

    return (
        <div className="bg-white border border-[#E5DFD3] rounded-3xl p-5 sm:p-6">
            {/* 월 네비게이션
                핵심: 피커 드롭다운을 flex row 완전히 밖 별도 relative wrapper에 배치.
                flex row 안에 있으면 pickerOpen 시 flex 자식으로 취급되어 화살표가 밀림. */}
            <div className="relative mb-6">
                {/* flex row — 년월 버튼 + 화살표. 피커는 여기 없음 */}
                <div className="flex items-center justify-between">
                    <button
                        onClick={(e) => {
                            e.stopPropagation();
                            setPickerOpen((v) => !v);
                        }}
                        className="flex items-center gap-[6px] text-[16px] font-extrabold text-[#211C26] tracking-[-0.01em] px-2 -ml-2 py-1 rounded-lg hover:bg-[#F1ECE3] transition-colors"
                    >
                        {year}년 {month + 1}월
                        <Ic d={pickerOpen ? I.chevUp : I.chevDown} size={14} color="#A39CAC" />
                    </button>
                    <div className="flex items-center gap-1">
                        <button
                            onClick={onPrevMonth}
                            aria-label="이전 달"
                            className="w-8 h-8 rounded-full flex items-center justify-center border border-[#E5DFD3] hover:border-[#D6CFC1] hover:bg-[#F1ECE3] transition-colors"
                        >
                            <Ic d={I.chevL} size={15} color="#6E6678" />
                        </button>
                        <button
                            onClick={onNextMonth}
                            aria-label="다음 달"
                            className="w-8 h-8 rounded-full flex items-center justify-center border border-[#E5DFD3] hover:border-[#D6CFC1] hover:bg-[#F1ECE3] transition-colors"
                        >
                            <Ic d={I.chevR} size={15} color="#6E6678" />
                        </button>
                    </div>
                </div>
                {/* 피커: position absolute라 레이아웃 흐름 완전히 이탈 → 화살표 절대 안 밀림 */}
                {pickerOpen && (
                    <div className="absolute left-0 top-[calc(100%+4px)] z-30" onClick={(e) => e.stopPropagation()}>
                        <YearMonthPicker
                            year={year}
                            month={month}
                            onChange={onJumpTo}
                            onClose={() => setPickerOpen(false)}
                        />
                    </div>
                )}
            </div>

            {/* 요일 헤더 */}
            <div className="grid grid-cols-7 mb-1">
                {WEEKDAYS.map((w) => (
                    <div key={w} className="text-center text-[11px] font-semibold text-[#A39CAC] py-1">
                        {w}
                    </div>
                ))}
            </div>

            {/* 날짜 그리드
                ↓ 수정 1: h-11 sm:h-12 → h-[52px] sm:h-[56px] (높이 조금 더 키움) */}
            <div className="grid grid-cols-7 gap-x-[2px] gap-y-[2px]">
                {grid.flat().map((day, idx) => {
                    if (day === null) return <div key={idx} className="h-[52px] sm:h-[56px]" />;

                    const dateKey = toKey(year, month, day);
                    const record = recordsByDate[dateKey];
                    const theme = record ? getMoodTheme(record.mood) : null;
                    const isSelected = selectedDate === dateKey;
                    const isToday = dateKey === todayKey;

                    return (
                        <button
                            key={idx}
                            onClick={() => onSelectDate(dateKey)}
                            className={`h-[52px] sm:h-[56px] flex flex-col items-center justify-center gap-[3px] rounded-xl transition-all ${
                                isSelected ? 'bg-[#211C26]' : isToday ? 'bg-[#F1ECE3]' : 'hover:bg-[#FAF8F4]'
                            }`}
                        >
                            <span
                                className={`text-[13px] ${isSelected ? 'font-bold text-white' : 'font-medium text-[#211C26]'}`}
                            >
                                {day}
                            </span>
                            <span
                                className="w-[5px] h-[5px] rounded-full"
                                className={`w-[5px] h-[5px] rounded-full ${record ? (isSelected ? 'bg-white' : getThemeBgClass(theme.color)) : 'bg-transparent'}`}
                            />
                        </button>
                    );
                })}
            </div>
        </div>
    );
}

/* ─────────────────────────────────────────
   ALBUM COVER (RecommendationPage 폴백 스타일)
───────────────────────────────────────── */
function AlbumCover({ track, className = '', roundedClass = 'rounded-[10px]', iconSize = 12 }) {
    const [imageFailed, setImageFailed] = useState(false);
    const hasAlbumImage = Boolean(track?.album_image_url) && !imageFailed;

    return (
        <div className={`shrink-0 overflow-hidden bg-[linear-gradient(135deg,#FFEAE6_0%,#ECEDFD_55%,#FFF3DE_100%)] ${roundedClass} ${className}`}>
            {hasAlbumImage ? (
                <img
                    src={track.album_image_url}
                    alt={`${track.name} 앨범 커버`}
                    onError={() => setImageFailed(true)}
                    className="block h-full w-full object-cover"
                />
            ) : (
                <div className="flex h-full w-full flex-col items-center justify-center gap-0.5 p-1.5 text-center">
                    <Ic d={I.music} size={iconSize} color="#A39CAC" />
                    <span className="line-clamp-2 overflow-hidden text-ellipsis text-[10px] font-bold leading-[1.1] text-[#6E6678]">
                        {track.album_name || track.name}
                    </span>
                </div>
            )}
        </div>
    );
}

/* ─────────────────────────────────────────
   TRACK ROW
───────────────────────────────────────── */
function TrackRow({ track, index }) {
    return (
        <div className="flex items-center gap-3 py-2">
            <span className="text-[11px] font-bold text-[#A39CAC] w-4 shrink-0 text-center">
                {String(index + 1).padStart(2, '0')}
            </span>
            <a
                href={track.spotify_url}
                target="_blank"
                rel="noopener noreferrer"
                className="block shrink-0 rounded-[10px] overflow-hidden leading-none"
                aria-label={`${track.name} Spotify에서 열기`}
            >
                <AlbumCover track={track} className="w-10 h-10" roundedClass="rounded-[10px]" iconSize={12} />
            </a>
            <div className="flex-1 min-w-0">
                <a
                    href={track.spotify_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="block text-[13.5px] font-bold text-[#211C26] no-underline truncate hover:text-[#7B7FF0] transition-colors"
                >
                    {track.name}
                </a>
                <a
                    href={track.spotify_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="block text-[12px] text-[#6E6678] no-underline truncate"
                >
                    {track.artist_name}
                </a>
            </div>
                    <a
                        href={track.spotify_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        aria-label="Spotify에서 듣기"
                        className="w-8 h-8 rounded-full flex items-center justify-center shrink-0 transition-transform hover:scale-105 bg-[#1ED760]"
                    >
                <Ic d={I.play} size={12} color="#191414" fill="#191414" sw={0} />
            </a>
        </div>
    );
}

/* ─────────────────────────────────────────
   SELECTED DAY PANEL

   수정 사항:
   1. rawText를 parseInputNote로 파싱 → freeText / vibes 분리
   2. "선택한 감정" 영역에서 아이콘 제거 (pill 텍스트만)
   3. "원하는 분위기"와 "직접 입력한 내용"을 별도 블록으로 표시
───────────────────────────────────────── */
function SelectedDayPanel({ dateKey, record }) {
    const [expanded, setExpanded] = useState(false);

    const dateObj = useMemo(() => {
        const [y, m, d] = dateKey.split('-').map(Number);
        return formatYMDLabel(y, m - 1, d);
    }, [dateKey]);

    useEffect(() => {
        setExpanded(false);
    }, [dateKey]);

    if (!record) {
        return (
            <div className="bg-white border border-[#E5DFD3] rounded-3xl p-6 sm:p-7 text-center">
                <p className="text-[12px] font-bold text-[#A39CAC] uppercase tracking-[0.06em] mb-3">{dateObj}</p>
                <div className="w-12 h-12 rounded-2xl flex items-center justify-center mx-auto mb-4 bg-[#ECEDFD]">
                    <Ic d={I.cloud} size={22} color="#7B7FF0" />
                </div>
                <p className="text-[14px] font-semibold text-[#211C26] mb-1">아직 기록된 감정이 없어요</p>
                <p className="text-[13px] text-[#6E6678] mb-5">오늘의 감정을 남겨볼까요?</p>
                <Link
                    to="/mood-input"
                    className="inline-flex items-center gap-2 text-[13.5px] font-bold text-white bg-[#211C26] px-5 py-3 rounded-full no-underline hover:-translate-y-px transition-transform"
                >
                    <Ic d={I.sparkles} size={15} color="#FFB648" />
                    감정 기록하기
                </Link>
            </div>
        );
    }

    const theme = getMoodTheme(record.mood);
    const trackCount = record.tracks?.length || 0;
    const representativeTrack = record.tracks?.[0];

    /* ↓ 수정 2: rawText → parseInputNote로 파싱해서 freeText / vibes 분리 */
    const { freeText, vibes: parsedVibes } = parseInputNote(record.rawText || record.text || '');
    const vibes = record.vibes?.length ? record.vibes : parsedVibes;
    const hasVibes = vibes.length > 0;
    const hasFreeText = Boolean(freeText);

    return (
        <div className="bg-white border border-[#E5DFD3] rounded-3xl p-6 sm:p-7">
            <p className="text-[12px] font-bold text-[#A39CAC] uppercase tracking-[0.06em] mb-4">{dateObj}</p>

            {/* ↓ 수정 3: 선택한 감정 — 아이콘 없이 pill 텍스트만 */}
            <div className="mb-5">
                <p className="text-[11px] font-semibold text-[#A39CAC] uppercase tracking-[0.06em] mb-2">선택한 감정</p>
                <span className={`inline-flex items-center rounded-full px-3 py-1 text-[12.5px] font-bold text-white ${getThemeBgClass(theme.color)}`}>
                    {theme.label}
                </span>
            </div>

            {/* 원하는 분위기 — vibes 배열에서 별도 렌더 */}
            {hasVibes && (
                <div className="mb-5">
                    <p className="text-[11px] font-semibold text-[#A39CAC] uppercase tracking-[0.06em] mb-2">
                        원하는 분위기
                    </p>
                    <div className="flex flex-wrap gap-[6px]">
                        {vibes.map((v) => (
                            <span
                                key={v}
                                className="text-[11.5px] font-semibold text-[#6E6678] border border-[#D6CFC1] px-[10px] py-1 rounded-full"
                            >
                                {v}
                            </span>
                        ))}
                    </div>
                </div>
            )}

            {/* 직접 입력한 내용 — freeText만 별도 렌더 */}
            {hasFreeText && (
                <div className="mb-5">
                    <p className="text-[11px] font-semibold text-[#A39CAC] uppercase tracking-[0.06em] mb-2">
                        직접 입력한 내용
                    </p>
                    <p className={`border-l-2 pl-3 text-[13.5px] leading-relaxed text-[#211C26] ${getThemeBorderLeftClass(theme.soft)}`}>
                        {freeText}
                    </p>
                </div>
            )}

            {!hasVibes && !hasFreeText && (
                <p className="text-[12.5px] text-[#A39CAC] leading-relaxed mb-5">감정 선택만으로 추천했어요.</p>
            )}

            {/* 추천 음악 */}
            {trackCount > 0 && (
                <div className="border-t border-[#E5DFD3] pt-4">
                    <div className="flex items-center justify-between mb-3">
                        <p className="text-[11px] font-bold text-[#A39CAC] uppercase tracking-[0.06em]">
                            추천받은 음악 · {trackCount}곡
                        </p>
                    </div>

                    {!expanded && representativeTrack && (
                        <div className="flex items-center gap-3 mb-4">
                            <a
                                href={representativeTrack.spotify_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="block shrink-0 rounded-[10px] overflow-hidden leading-none"
                            >
                                <AlbumCover track={representativeTrack} className="w-11 h-11" roundedClass="rounded-[10px]" iconSize={13} />
                            </a>
                            <div className="min-w-0 flex-1">
                                <a
                                    href={representativeTrack.spotify_url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="block text-[13.5px] font-bold text-[#211C26] no-underline truncate"
                                >
                                    {representativeTrack.name}
                                </a>
                                <p className="text-[12px] text-[#6E6678] truncate">{representativeTrack.artist_name}</p>
                            </div>
                        </div>
                    )}

                    {expanded && (
                        <div className="flex flex-col divide-y divide-[#F1ECE3] mb-3">
                            {record.tracks.map((track, idx) => (
                                <TrackRow key={track.track_id || idx} track={track} index={idx} />
                            ))}
                        </div>
                    )}

                    <button
                        onClick={() => setExpanded((v) => !v)}
                        className="flex items-center justify-center gap-[6px] w-full text-[12.5px] font-bold text-[#6E6678] hover:text-[#211C26] py-2 rounded-full border border-[#E5DFD3] hover:border-[#D6CFC1] transition-colors"
                    >
                        {expanded ? '추천 기록 닫기' : '추천 기록 보기'}
                        <Ic d={expanded ? I.chevUp : I.chevDown} size={14} color="currentColor" />
                    </button>

                    <div className="flex items-center gap-[6px] mt-4 pt-3 border-t border-[#F1ECE3]">
                        <SpotifyMark size={13} />
                        <span className="text-[11px] text-[#A39CAC]">곡 정보 및 앨범 커버: Provided by Spotify</span>
                    </div>
                </div>
            )}
        </div>
    );
}

/* ─────────────────────────────────────────
   RECENT RECORD ITEM
───────────────────────────────────────── */
function RecentRecordItem({ record, isSelected, onClick }) {
    const theme = getMoodTheme(record.mood);
    const representativeTrack = record.tracks?.[0];
    const trackCount = record.tracks?.length || 0;
    const { vibes: parsedVibes } = parseInputNote(record.rawText || record.text || '');
    const vibes = record.vibes?.length ? record.vibes : parsedVibes;

    return (
        <button
            onClick={onClick}
            className={`w-full text-left bg-white border rounded-2xl px-4 py-4 sm:px-5 transition-all ${
                isSelected ? 'border-[#211C26]' : 'border-[#E5DFD3] hover:border-[#D6CFC1] hover:-translate-y-px'
            }`}
        >
            <div className="flex items-center gap-3">
                <div
                    className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 ${getThemeSoftClass(theme.soft)}`}
                >
                    <Ic d={I.calHeart} size={18} color={theme.color} />
                </div>
                <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2 mb-[2px]">
                        <span className="text-[13px] font-bold text-[#211C26]">{formatShortDate(record.date)}</span>
                        <span className={`rounded-full px-2 py-[2px] text-[11.5px] font-bold ${getThemeToneClass(theme.soft, theme.color)}`}>
                            {theme.label}
                        </span>
                    </div>
                    {vibes.length > 0 && <p className="text-[12px] text-[#A39CAC] truncate">{vibes.join(' · ')}</p>}
                </div>
                {representativeTrack?.spotify_url && (
                    <a
                        href={representativeTrack.spotify_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        onClick={(e) => e.stopPropagation()}
                        aria-label="Spotify에서 듣기"
                        className="w-9 h-9 rounded-full flex items-center justify-center shrink-0 transition-transform hover:scale-105 bg-[#1ED760]"
                    >
                        <Ic d={I.play} size={13} color="#191414" fill="#191414" sw={0} />
                    </a>
                )}
            </div>
            {trackCount > 0 && (
                <p className="flex items-center gap-[5px] text-[11.5px] text-[#A39CAC] mt-3 pl-[52px]">
                    <Ic d={I.music} size={11} color="#A39CAC" />
                    추천 음악 {trackCount}곡
                    {representativeTrack && (
                        <span className="text-[#6E6678] font-medium truncate">
                            · {representativeTrack.name} - {representativeTrack.artist_name}
                        </span>
                    )}
                </p>
            )}
        </button>
    );
}

/* ═══════════════════════════════════════════
   PAGE
═══════════════════════════════════════════ */
export default function HistoryPage() {
    const bp = useBreakpoint();
    const isMobile = bp === 'mobile';
    const isTablet = bp === 'tablet';

    const now = new Date();
    const [year, setYear] = useState(now.getFullYear());
    const [month, setMonth] = useState(now.getMonth());
    const [selectedDate, setSelectedDate] = useState(toKey(now.getFullYear(), now.getMonth(), now.getDate()));

    const [history, setHistory] = useState(null);
    const [loading, setLoading] = useState(true);
    const [loadError, setLoadError] = useState('');

    const wrapCls = isMobile ? 'px-5' : isTablet ? 'px-7' : 'px-10';

    useEffect(() => {
        let active = true;
        setLoading(true);
        setLoadError('');
        const load = async () => {
            try {
                const data = await getMoodHistory({ year, month: month + 1 });
                if (!active) return;
                setHistory(data);
            } catch (err) {
                if (!active) return;
                setLoadError(err.message || '감정 기록을 불러오지 못했어요.');
                setHistory(buildDummyHistory(year, month));
            } finally {
                if (active) setLoading(false);
            }
        };
        load();
        return () => {
            active = false;
        };
    }, [year, month]);

    const recordsByDate = useMemo(() => {
        const map = {};
        (history?.records || []).forEach((r) => {
            map[r.date] = r;
        });
        return map;
    }, [history]);

    const sortedRecords = useMemo(
        () => [...(history?.records || [])].sort((a, b) => (a.date < b.date ? 1 : -1)),
        [history]
    );

    const handlePrevMonth = () => {
        if (month === 0) {
            setYear((y) => y - 1);
            setMonth(11);
        } else {
            setMonth((m) => m - 1);
        }
    };
    const handleNextMonth = () => {
        if (month === 11) {
            setYear((y) => y + 1);
            setMonth(0);
        } else {
            setMonth((m) => m + 1);
        }
    };
    const handleJumpTo = (jumpYear, jumpMonth) => {
        setYear(jumpYear);
        setMonth(jumpMonth);
    };

    const summary = history?.summary;
    const topMoodTheme = summary?.topMood ? getMoodTheme(summary.topMood) : null;
    const moodDistribution = useMemo(() => {
        const entries = Object.entries(summary?.moodCounts || {});
        return entries.sort((a, b) => b[1] - a[1]).slice(0, 4);
    }, [summary]);
    const selectedRecord = recordsByDate[selectedDate] || null;

    return (
        <div className="font-['Pretendard',-apple-system,BlinkMacSystemFont,system-ui,sans-serif] bg-[#FAF8F4] text-[#211C26] antialiased overflow-x-hidden min-h-screen">
            <link
                rel="stylesheet"
                crossOrigin="anonymous"
                href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.css"
            />
            <Header />

            <main className={`relative ${isMobile ? 'pt-[100px] pb-[72px]' : 'pt-[132px] pb-[120px]'} ${wrapCls}`}>
                <div className="max-w-[1240px] mx-auto">
                    {/* 페이지 헤더 */}
                    <div className={`fu mb-12 ${getDelayClass(0.05)}`}>
                        <span className="inline-flex items-center gap-[6px] text-[12px] font-semibold text-[#6E6678] bg-white border border-[#E5DFD3] px-[14px] py-[6px] rounded-full mb-4">
                            <Ic d={I.calHeart} size={13} color="#FF6B5E" />
                            감정 기록
                        </span>
                        <h1 className="text-[clamp(26px,4vw,36px)] font-extrabold tracking-[-0.03em] leading-tight mb-2">
                            지나온 감정과 음악을 돌아봐요
                        </h1>
                        <p className="text-[15px] text-[#6E6678] leading-relaxed max-w-[480px]">
                            날짜를 눌러 그날의 감정과 추천받은 음악을 다시 확인할 수 있어요.
                        </p>
                    </div>

                    {loadError && (
                        <p className={`fu text-[12.5px] text-[#A39CAC] mb-6 ${getDelayClass(0.07)}`}>
                            {loadError} 임시로 예시 데이터를 보여드리고 있어요.
                        </p>
                    )}

                    {/* 요약 */}
                    <div className={`fu mb-5 ${getDelayClass(0.08)}`}>
                        <span className="inline-flex items-center gap-[6px] text-[12px] font-bold text-[#FF6B5E] uppercase tracking-[0.06em]">
                            <Ic d={I.bar} size={13} color="#FF6B5E" />
                            This Month
                        </span>
                    </div>
                    <div
                        className={`fu grid gap-3 mb-12 ${isMobile ? 'grid-cols-1' : 'grid-cols-3'} ${getDelayClass(0.1)}`}
                    >
                        <SummaryCard
                            icon={I.calHeart}
                            iconBg="#ECEDFD"
                            iconColor="#7B7FF0"
                            label="이번 달 기록"
                            value={loading ? '–' : `${summary?.recordedDays ?? 0}일`}
                        />
                        <SummaryCard
                            icon={I.bar}
                            iconBg={topMoodTheme ? topMoodTheme.soft : '#F1ECE3'}
                            iconColor={topMoodTheme ? topMoodTheme.color : '#A39CAC'}
                            label="가장 많은 감정"
                            value={loading ? '–' : topMoodTheme ? topMoodTheme.label : '기록 없음'}
                            valueColor={topMoodTheme ? topMoodTheme.color : undefined}
                        />
                        <SummaryCard
                            icon={I.music}
                            iconBg="#FFF3DE"
                            iconColor="#B9791E"
                            label="자주 선택한 분위기"
                            value={loading ? '–' : summary?.topVibe || '기록 없음'}
                        />
                    </div>

                    {moodDistribution.length > 0 && (
                        <div className={`fu mb-12 ${getDelayClass(0.12)}`}>
                            <div className="mb-3 flex items-center gap-2">
                                <Ic d={I.bar} size={13} color="#7B7FF0" />
                                <p className="text-[12px] font-bold text-[#7B7FF0] uppercase tracking-[0.06em]">
                                    최근 감정 분포
                                </p>
                            </div>
                            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                                {moodDistribution.map(([mood, count]) => {
                                    const theme = getMoodTheme(mood);
                                    return (
                                        <div
                                            key={mood}
                                            className="rounded-2xl border border-[#E5DFD3] bg-white px-4 py-3"
                                        >
                                            <div className="flex items-center justify-between gap-2 mb-2">
                                                <span className={`rounded-full px-2 py-[2px] text-[12px] font-bold ${getThemeToneClass(theme.soft, theme.color)}`}>
                                                    {theme.label}
                                                </span>
                                                <span className="text-[12px] font-bold text-[#211C26]">{count}회</span>
                                            </div>
                                            <div className="h-[6px] rounded-full bg-[#F1ECE3] overflow-hidden">
                                                <div
                                                    className={`h-full rounded-full ${getThemeBgClass(theme.color)} ${getProgressWidthClass(count)}`}
                                                />
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        </div>
                    )}

                    {/* 캘린더 + 선택 패널 */}
                    <div className={`fu mb-5 ${getDelayClass(0.13)}`}>
                        <span className="inline-flex items-center gap-[6px] text-[12px] font-bold text-[#7B7FF0] uppercase tracking-[0.06em]">
                            <Ic d={I.calHeart} size={13} color="#7B7FF0" />
                            Calendar
                        </span>
                    </div>
                    <div
                        className={`fu grid gap-4 mb-12 ${
                            isMobile ? 'grid-cols-1' : isTablet ? 'grid-cols-[1fr_300px]' : 'grid-cols-[1fr_360px]'
                        } ${getDelayClass(0.16)}`}
                    >
                        <MoodCalendar
                            year={year}
                            month={month}
                            onPrevMonth={handlePrevMonth}
                            onNextMonth={handleNextMonth}
                            onJumpTo={handleJumpTo}
                            recordsByDate={recordsByDate}
                            selectedDate={selectedDate}
                            onSelectDate={setSelectedDate}
                        />
                        <SelectedDayPanel dateKey={selectedDate} record={selectedRecord} />
                    </div>

                    {/* 최근 기록 */}
                    <div className={`fu ${getDelayClass(0.22)}`}>
                        <div className="flex items-center justify-between mb-5">
                            <span className="inline-flex items-center gap-[6px] text-[12px] font-bold text-[#FF6B5E] uppercase tracking-[0.06em]">
                                <Ic d={I.sparkles} size={13} color="#FF6B5E" />
                                Recent
                            </span>
                        </div>
                        <h2 className="text-[19px] font-extrabold text-[#211C26] tracking-[-0.015em] mb-5">
                            최근 기록
                        </h2>

                        {sortedRecords.length === 0 ? (
                            <div className="bg-white border border-[#E5DFD3] rounded-3xl p-10 text-center">
                                <p className="text-[14px] font-semibold text-[#211C26] mb-1">
                                    아직 기록된 감정이 없어요
                                </p>
                                <p className="text-[13px] text-[#6E6678]">감정을 기록하면 여기에 차곡차곡 쌓여요.</p>
                            </div>
                        ) : (
                            <div className={`grid gap-3 ${isMobile ? 'grid-cols-1' : 'grid-cols-2'}`}>
                                {sortedRecords.map((record) => (
                                    <RecentRecordItem
                                        key={record.date}
                                        record={record}
                                        isSelected={record.date === selectedDate}
                                        onClick={() => setSelectedDate(record.date)}
                                    />
                                ))}
                            </div>
                        )}
                    </div>
                </div>
            </main>

            <Footer />
        </div>
    );
}
