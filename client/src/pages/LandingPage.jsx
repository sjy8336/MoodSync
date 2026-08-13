import { useState, useEffect } from 'react';
import Footer from '../components/Footer';
import Header from '../components/Header';

/* ───────────────────────────────────────────
   DESIGN TOKENS  (모든 색상·스타일 단일 출처)
─────────────────────────────────────────── */
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
   ICONS  (lucide SVG path 직접 삽입)
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
    sparkles:
        'M9.937 15.5A2 2 0 0 0 8.5 14.063l-6.135-1.582a.5.5 0 0 1 0-.962L8.5 9.936A2 2 0 0 0 9.937 8.5l1.582-6.135a.5.5 0 0 1 .963 0L14.063 8.5A2 2 0 0 0 15.5 9.937l6.135 1.581a.5.5 0 0 1 0 .964L15.5 14.063a2 2 0 0 0-1.437 1.437l-1.582 6.135a.5.5 0 0 1-.963 0z',
    music: 'M9 18V5l12-2v13M9 18a3 3 0 1 1-6 0 3 3 0 0 1 6 0zm12-2a3 3 0 1 1-6 0 3 3 0 0 1 6 0z',
    arrowR: 'M5 12h14M12 5l7 7-7 7',
    playCirc: ['M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10z', 'M10 8l6 4-6 4V8z'],
    layers: ['M12 2 2 7l10 5 10-5-10-5z', 'M2 17l10 5 10-5', 'M2 12l10 5 10-5'],
    smile: [
        'M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10z',
        'M8 14s1.5 2 4 2 4-2 4-2',
        'M9 9h.01M15 9h.01',
    ],
    cloud: 'M17.5 19H9a7 7 0 1 1 6.71-9h1.79a4.5 4.5 0 1 1 0 9z',
    rain: ['M20 16.2A4.5 4.5 0 0 0 17.5 8H16.74A7 7 0 1 0 7 17.97', 'M16 20v2M8 20v2M12 20v2'],
    sparkle: 'M12 3l1.9 5.87L20 10l-5.87 1.9L12 18l-1.9-5.87L4 10l5.87-1.9z',
    activity: 'M22 12h-4l-3 9L9 3l-3 9H2',
    msgCirc: 'M7.9 20A9 9 0 1 0 4 16.1L2 22z',
    calHeart: [
        'M8 2v4M16 2v4M3 10h18M3 6a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h18a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2H3z',
        'M12 17a2 2 0 0 0 2-2c0-1-1-2-2-3-1 1-2 2-2 3a2 2 0 0 0 2 2z',
    ],
    heart: 'M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z',
    eye: ['M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7z', 'M12 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0z'],
    bulb: [
        'M9 18h6M10 22h4M12 2a7 7 0 0 1 7 7c0 2.38-1.19 4.47-3 5.74V17a2 2 0 0 1-2 2h-4a2 2 0 0 1-2-2v-2.26C6.19 13.47 5 11.38 5 9a7 7 0 0 1 7-7z',
    ],
    play: 'M6 3l15 9-15 9V3z',
    check: 'M20 6 9 17l-5-5',
    link2: ['M9 17H7A5 5 0 0 1 7 7h2', 'M15 7h2a5 5 0 0 1 0 10h-2', 'M8 12h8'],
    shield: ['M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z', 'M9 12l2 2 4-4'],
    imgIcon: ['M21 15a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2h4l2 3h8a2 2 0 0 1 2 2z'],
    extLink: ['M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6', 'M15 3h6v6', 'M10 14 21 3'],
    badge: [
        'M3.85 8.62a4 4 0 0 1 4.78-4.77 4 4 0 0 1 6.74 0 4 4 0 0 1 4.78 4.78 4 4 0 0 1 0 6.74 4 4 0 0 1-4.77 4.78 4 4 0 0 1-6.75 0 4 4 0 0 1-4.78-4.77 4 4 0 0 1 0-6.76z',
        'm9 12 2 2 4-4',
    ],
    bar: ['M3 3v18h18', 'M7 16v-5', 'M11 16v-9', 'M15 16v-3'],
    msgSq: ['M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z'],
    book: [
        'M4 19.5A2.5 2.5 0 0 1 6.5 17H20',
        'M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z',
        'M12 10a2 2 0 0 0 2-2c0-.9-.8-1.8-2-2.7-1.2.9-2 1.8-2 2.7a2 2 0 0 0 2 2z',
    ],
    thumb: [
        'M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3H14z',
        'M7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3',
    ],
    gem: ['M6 3h12l4 6-10 13L2 9z', 'M11 3 8 9l4 13 4-13-3-6', 'M2 9h20'],
    waveform: 'M2 12h2M6 8v8M10 5v14M14 9v6M18 6v12M22 12h2',
};

/* ───────────────────────────────────────────
   SPOTIFY MARK
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
   RESPONSIVE HOOK
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
   HERO SPECTRUM VISUAL  (인터랙티브)
─────────────────────────────────────────── */
const MOODS = [
    {
        id: 0,
        label: '차분함',
        color: T.calm,
        panelClass: 'bg-[rgba(123,127,240,0.08)]',
        buttonClass:
            'bg-[#7B7FF0] text-white shadow-[0_4px_18px_rgba(123,127,240,0.27)] -translate-y-px',
        barClass: 'bg-[linear-gradient(to_top,#7B7FF0,#7B7FF099)]',
        textClass: 'text-[#7B7FF0]',
        wave: [
            { heightClass: 'h-[22%]', opacityClass: 'opacity-70' },
            { heightClass: 'h-[38%]', opacityClass: 'opacity-80' },
            { heightClass: 'h-[28%]', opacityClass: 'opacity-90' },
            { heightClass: 'h-[45%]', opacityClass: 'opacity-70' },
            { heightClass: 'h-[30%]', opacityClass: 'opacity-80' },
            { heightClass: 'h-[25%]', opacityClass: 'opacity-90' },
            { heightClass: 'h-[40%]', opacityClass: 'opacity-70' },
            { heightClass: 'h-[20%]', opacityClass: 'opacity-80' },
            { heightClass: 'h-[48%]', opacityClass: 'opacity-90' },
            { heightClass: 'h-[32%]', opacityClass: 'opacity-70' },
        ],
    },
    {
        id: 1,
        label: '평온',
        color: '#9B8FD4',
        panelClass: 'bg-[rgba(155,143,212,0.09)]',
        buttonClass:
            'bg-[#9B8FD4] text-white shadow-[0_4px_18px_rgba(155,143,212,0.27)] -translate-y-px',
        barClass: 'bg-[linear-gradient(to_top,#9B8FD4,#9B8FD499)]',
        textClass: 'text-[#9B8FD4]',
        wave: [
            { heightClass: 'h-[35%]', opacityClass: 'opacity-70' },
            { heightClass: 'h-[52%]', opacityClass: 'opacity-80' },
            { heightClass: 'h-[30%]', opacityClass: 'opacity-90' },
            { heightClass: 'h-[48%]', opacityClass: 'opacity-70' },
            { heightClass: 'h-[42%]', opacityClass: 'opacity-80' },
            { heightClass: 'h-[36%]', opacityClass: 'opacity-90' },
            { heightClass: 'h-[50%]', opacityClass: 'opacity-70' },
            { heightClass: 'h-[28%]', opacityClass: 'opacity-80' },
            { heightClass: 'h-[55%]', opacityClass: 'opacity-90' },
            { heightClass: 'h-[40%]', opacityClass: 'opacity-70' },
        ],
    },
    {
        id: 2,
        label: '설렘',
        color: T.warm,
        panelClass: 'bg-[rgba(255,182,72,0.09)]',
        buttonClass:
            'bg-[#FFB648] text-white shadow-[0_4px_18px_rgba(255,182,72,0.27)] -translate-y-px',
        barClass: 'bg-[linear-gradient(to_top,#FFB648,#FFB64899)]',
        textClass: 'text-[#FFB648]',
        wave: [
            { heightClass: 'h-[48%]', opacityClass: 'opacity-70' },
            { heightClass: 'h-[62%]', opacityClass: 'opacity-80' },
            { heightClass: 'h-[40%]', opacityClass: 'opacity-90' },
            { heightClass: 'h-[66%]', opacityClass: 'opacity-70' },
            { heightClass: 'h-[54%]', opacityClass: 'opacity-80' },
            { heightClass: 'h-[58%]', opacityClass: 'opacity-90' },
            { heightClass: 'h-[70%]', opacityClass: 'opacity-70' },
            { heightClass: 'h-[44%]', opacityClass: 'opacity-80' },
            { heightClass: 'h-[60%]', opacityClass: 'opacity-90' },
            { heightClass: 'h-[52%]', opacityClass: 'opacity-70' },
        ],
    },
    {
        id: 3,
        label: '기쁨',
        color: '#FF8C6B',
        panelClass: 'bg-[rgba(255,140,107,0.09)]',
        buttonClass:
            'bg-[#FF8C6B] text-white shadow-[0_4px_18px_rgba(255,140,107,0.27)] -translate-y-px',
        barClass: 'bg-[linear-gradient(to_top,#FF8C6B,#FF8C6B99)]',
        textClass: 'text-[#FF8C6B]',
        wave: [
            { heightClass: 'h-[62%]', opacityClass: 'opacity-70' },
            { heightClass: 'h-[78%]', opacityClass: 'opacity-80' },
            { heightClass: 'h-[58%]', opacityClass: 'opacity-90' },
            { heightClass: 'h-[82%]', opacityClass: 'opacity-70' },
            { heightClass: 'h-[70%]', opacityClass: 'opacity-80' },
            { heightClass: 'h-[72%]', opacityClass: 'opacity-90' },
            { heightClass: 'h-[65%]', opacityClass: 'opacity-70' },
            { heightClass: 'h-[80%]', opacityClass: 'opacity-80' },
            { heightClass: 'h-[68%]', opacityClass: 'opacity-90' },
            { heightClass: 'h-[75%]', opacityClass: 'opacity-70' },
        ],
    },
    {
        id: 4,
        label: '활기',
        color: T.joy,
        panelClass: 'bg-[rgba(255,107,94,0.10)]',
        buttonClass:
            'bg-[#FF6B5E] text-white shadow-[0_4px_18px_rgba(255,107,94,0.27)] -translate-y-px',
        barClass: 'bg-[linear-gradient(to_top,#FF6B5E,#FF6B5E99)]',
        textClass: 'text-[#FF6B5E]',
        wave: [
            { heightClass: 'h-[80%]', opacityClass: 'opacity-70' },
            { heightClass: 'h-[92%]', opacityClass: 'opacity-80' },
            { heightClass: 'h-[72%]', opacityClass: 'opacity-90' },
            { heightClass: 'h-[100%]', opacityClass: 'opacity-70' },
            { heightClass: 'h-[86%]', opacityClass: 'opacity-80' },
            { heightClass: 'h-[84%]', opacityClass: 'opacity-90' },
            { heightClass: 'h-[94%]', opacityClass: 'opacity-70' },
            { heightClass: 'h-[78%]', opacityClass: 'opacity-80' },
            { heightClass: 'h-[90%]', opacityClass: 'opacity-90' },
            { heightClass: 'h-[88%]', opacityClass: 'opacity-70' },
        ],
    },
];

const SpectrumVisual = () => {
    const [active, setActive] = useState(2);
    const mood = MOODS[active];

    return (
        <div className="rounded-[32px] border border-[#E5DFD3] bg-white p-2 shadow-[0_32px_80px_-20px_rgba(33,28,38,0.18)]">
            <div className={`relative overflow-hidden rounded-[24px] px-10 pt-9 ${mood.panelClass}`}>
                <div className="mb-7 flex flex-wrap gap-2">
                    {MOODS.map((m) => {
                        const isActive = m.id === active;
                        return (
                            <button
                                key={m.id}
                                onClick={() => setActive(m.id)}
                                className={`flex cursor-pointer items-center gap-1.5 rounded-full px-[18px] py-2 text-[13px] font-bold transition-all duration-200 font-[Pretendard,system-ui,sans-serif] ${isActive ? m.buttonClass : 'bg-white text-[#6E6678] shadow-[inset_0_0_0_1.5px_#E5DFD3]'}`}
                            >
                                {m.label}
                            </button>
                        );
                    })}
                </div>
                <div className="flex h-[130px] items-end gap-1.5 px-1">
                    {mood.wave.map((bar, i) => (
                        <div
                            key={i}
                            className={`flex-1 rounded-t-[6px] transition-[height] duration-500 ${bar.heightClass} ${bar.opacityClass} ${mood.barClass}`}
                        />
                    ))}
                </div>
                <div className="flex flex-wrap items-center justify-between gap-2 py-[14px] pb-[22px] text-[12.5px] text-[#6E6678]">
                    <span>감정을 탭해서 패턴을 바꿔보세요</span>
                    <span className={`font-bold ${mood.textClass}`}>
                        {mood.label} 구간의 음악 에너지
                    </span>
                </div>
            </div>
        </div>
    );
};

/* ───────────────────────────────────────────
   SECTION TAG
─────────────────────────────────────────── */
const Tag = ({ icon, children }) => (
    <div className="mb-4 inline-flex items-center gap-1.5 text-[12px] font-bold uppercase tracking-[0.07em] text-[#FF6B5E]">
        <Ic d={icon} size={13} color={T.joy} /> {children}
    </div>
);

/* ───────────────────────────────────────────
   SECTION HEAD
─────────────────────────────────────────── */
const SectionHead = ({ tag, tagIcon, title, desc, center }) => (
    <div className={`${center ? 'mx-auto text-center' : 'ml-0 text-left'} mb-14 max-w-[620px]`}>
        <Tag icon={tagIcon}>{tag}</Tag>
        <h2 className="mb-4 text-[clamp(28px,3.4vw,42px)] font-extrabold tracking-[-0.03em] leading-[1.25] text-[#211C26]">
            {title}
        </h2>
        <p className="m-0 text-[16.5px] leading-[1.7] text-[#6E6678]">{desc}</p>
    </div>
);

/* ───────────────────────────────────────────
   BENTO CARD
─────────────────────────────────────────── */
const BentoCard = ({ iconD, iconBg, iconColor, title, desc, children, className = '' }) => {
    const [hov, setHov] = useState(false);
    return (
        <div
            onMouseEnter={() => setHov(true)}
            onMouseLeave={() => setHov(false)}
            className={`relative overflow-hidden rounded-[24px] border bg-white p-[34px] transition-all duration-200 ${hov ? 'border-[#D6CFC1] shadow-[0_20px_48px_-16px_rgba(33,28,38,0.15)] -translate-y-1' : 'border-[#E5DFD3]'} ${className}`}
        >
            <div className={`mb-5 flex h-[46px] w-[46px] items-center justify-center rounded-[14px] ${iconBg}`}>
                <Ic d={iconD} size={22} color={iconColor} />
            </div>
            <h3 className="mb-2.5 text-[18px] font-bold tracking-[-0.015em] text-[#211C26]">
                {title}
            </h3>
            <p className="m-0 text-[14px] leading-[1.7] text-[#6E6678]">{desc}</p>
            {children}
        </div>
    );
};

/* ───────────────────────────────────────────
   MOOD CHIPS
─────────────────────────────────────────── */
const CHIPS = [
    { icon: I.smile, label: '기쁨', bgClass: 'bg-[#FFEAE6]', textClass: 'text-[#9C3D33]' },
    { icon: I.cloud, label: '평온', bgClass: 'bg-[#F1ECE3]', textClass: 'text-[#6E6678]' },
    { icon: I.rain, label: '우울', bgClass: 'bg-[#ECEDFD]', textClass: 'text-[#3D3D8F]' },
    { icon: I.sparkle, label: '설렘', bgClass: 'bg-[#FFF3DE]', textClass: 'text-[#B9791E]' },
];

const FeatureCard = ({ icon, bgClass, iconColor, title, desc }) => {
    const [hov, setHov] = useState(false);
    return (
        <div
            onMouseEnter={() => setHov(true)}
            onMouseLeave={() => setHov(false)}
            className={`rounded-[24px] border bg-white p-[30px] transition-all duration-200 ${hov ? 'border-[#D6CFC1] shadow-[0_20px_48px_-16px_rgba(33,28,38,0.14)] -translate-y-1' : 'border-[#E5DFD3]'}`}
        >
            <div className={`mb-[18px] flex h-[44px] w-[44px] items-center justify-center rounded-[13px] ${bgClass}`}>
                <Ic d={icon} size={21} color={iconColor} />
            </div>
            <h3 className="mb-2 text-[16px] font-bold tracking-[-0.01em] text-[#211C26]">{title}</h3>
            <p className="m-0 text-[13.5px] leading-[1.65] text-[#6E6678]">{desc}</p>
        </div>
    );
};

/* ───────────────────────────────────────────
   TRACK CARD  (Spotify 정책 준수)
   - 앨범 커버 원본 유지 (변형·오버레이 없음)
   - 곡명·아티스트명·앨범 커버에 Spotify 링크
   - "Provided by Spotify" + "Spotify에서 듣기" 명시
─────────────────────────────────────────── */
const TrackCard = ({ cover, title, artist, reason, spotifyUrl, index }) => {
    const [liked, setLiked] = useState(false);
    const [hov, setHov] = useState(false);
    const [btnHov, setBtnHov] = useState(false);

    return (
        <div
            onMouseEnter={() => setHov(true)}
            onMouseLeave={() => setHov(false)}
            className={`mb-3 overflow-hidden rounded-[20px] border bg-white transition-all duration-200 ${hov ? 'border-[#D6CFC1] shadow-[0_8px_28px_-10px_rgba(33,28,38,0.13)]' : 'border-[#E5DFD3]'}`}
        >
            {/* 메인 행: 앨범커버 + 정보 + 액션 */}
            <div className="flex items-stretch">
                {/* ✅ 앨범 커버 — 원본 그대로, 오버레이/필터 없음, Spotify 링크 */}
                <a
                    href={spotifyUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="block shrink-0 leading-none"
                >
                    <img src={cover} alt={`${title} 앨범 커버`} className="block h-[84px] w-[84px] object-cover" />
                </a>

                {/* 트랙 정보 */}
                <div className="flex min-w-0 flex-1 flex-col justify-center gap-1 px-[16px] py-[13px] pr-[14px]">
                    {/* ✅ 곡명 — Spotify 링크 */}
                    <a
                        href={spotifyUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="block truncate text-[15px] font-bold tracking-[-0.01em] text-[#211C26] no-underline"
                    >
                        {title}
                    </a>
                    {/* ✅ 아티스트명 — Spotify 링크 */}
                    <a
                        href={spotifyUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="block text-[13px] text-[#6E6678] no-underline"
                    >
                        {artist}
                    </a>
                    {/* ✅ Provided by Spotify */}
                    <span className="inline-flex items-center gap-1 text-[11px] text-[#A39CAC]">
                        <SpotifyMark size={11} /> Provided by Spotify
                    </span>
                </div>

                {/* 액션: 좋아요 + Spotify 재생 버튼 */}
                <div className="flex shrink-0 flex-col items-center justify-center gap-2 px-[14px]">
                    <button
                        onClick={() => setLiked((l) => !l)}
                        aria-label="좋아요"
                        className={`flex h-[34px] w-[34px] cursor-pointer items-center justify-center rounded-full border-[1.5px] transition-all duration-200 ${liked ? 'border-[#FF6B5E] bg-[#FFEAE6]' : 'border-[#E5DFD3] bg-transparent'}`}
                    >
                        <Ic d={I.heart} size={14} color={liked ? T.joy : T.inkFaint} fill={liked ? T.joy : 'none'} />
                    </button>

                    {/* ✅ Spotify에서 듣기 — 필수 링크 버튼 */}
                    <a
                        href={spotifyUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        aria-label="Spotify에서 듣기"
                        className="flex h-[34px] w-[34px] shrink-0 items-center justify-center rounded-full bg-[#1ED760] text-[#191414] no-underline transition-transform duration-150 hover:scale-105 hover:brightness-110"
                    >
                        <Ic d={I.play} size={13} color={T.spotBlack} fill={T.spotBlack} sw={0} />
                    </a>
                </div>
            </div>

            {/* 추천 이유 — Mood Sync 고유 요소 (Spotify 단순 나열 아님을 명확히) */}
            <div className="flex items-start gap-2 border-t border-[#E5DFD3] bg-[#F1ECE3] px-4 py-2.5">
                <Ic d={I.bulb} size={13} color={T.calm} className="mt-0.5 shrink-0" />
                <p className="m-0 text-[12.5px] leading-[1.65] text-[#6E6678]">{reason}</p>
            </div>
        </div>
    );
};

/* ───────────────────────────────────────────
   BTN HELPERS
─────────────────────────────────────────── */
const BtnPrimary = ({ href, children, className = '' }) => {
    const [hov, setHov] = useState(false);
    return (
        <a
            href={href}
            onMouseEnter={() => setHov(true)}
            onMouseLeave={() => setHov(false)}
            className={`inline-flex items-center gap-[9px] rounded-full bg-[#211C26] px-7 py-4 text-[15.5px] font-bold text-white no-underline transition-all duration-200 ${hov ? '-translate-y-0.5 shadow-[0_20px_48px_-16px_rgba(33,28,38,0.4)]' : ''} ${className}`}
        >
            {children}
        </a>
    );
};

const BtnGhost = ({ href, children, fullWidth = false }) => {
    const [hov, setHov] = useState(false);
    return (
        <a
            href={href}
            onMouseEnter={() => setHov(true)}
            onMouseLeave={() => setHov(false)}
            className={`inline-flex items-center justify-center gap-2 rounded-full border-[1.5px] px-[22px] py-[15px] text-[15px] font-semibold text-[#211C26] no-underline transition-all duration-200 ${fullWidth ? 'w-full' : 'w-auto'} ${hov ? 'border-[#211C26] bg-white shadow-[0_8px_24px_-8px_rgba(33,28,38,0.18)]' : 'border-[#D6CFC1] bg-transparent'}`}
        >
            {children}
        </a>
    );
};

const sectionPadClass = (mobile, desktop = '120') => `py-[${mobile}px] min-[900px]:py-[${desktop}px]`;

const gridColsClass = (isMobile, isTablet, desktopCount) =>
    isMobile ? 'grid-cols-1' : isTablet ? 'grid-cols-2' : `grid-cols-${desktopCount}`;

/* ═══════════════════════════════════════════
   PAGE
═══════════════════════════════════════════ */
export default function MoodSync() {
    const bp = useBreakpoint();
    const isMobile = bp === 'mobile';
    const isTablet = bp === 'tablet';
    const isNarrow = isMobile || isTablet;

    const wrap = `mx-auto max-w-[1240px] px-5 ${isTablet ? 'min-[900px]:px-10' : 'min-[900px]:px-10'} ${isMobile ? '' : isTablet ? 'min-[560px]:px-7' : 'min-[560px]:px-7'}`;

    return (
        <div className="overflow-x-hidden bg-[#FAF8F4] font-[Pretendard,system-ui,sans-serif] text-[#211C26] antialiased">
            <Header />

            {/* ── HERO ── */}
            <section className="relative overflow-hidden pt-[120px] min-[900px]:pt-[156px]">
                <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(50%_60%_at_50%_0%,rgba(255,107,94,0.10)_0%,transparent_70%),radial-gradient(40%_50%_at_85%_10%,rgba(123,127,240,0.10)_0%,transparent_70%)]" />

                <div className={wrap}>
                    <div className="relative z-10 mx-auto max-w-[880px] pb-9 text-center min-[900px]:pb-14">
                        <span className="fu mb-7 inline-flex items-center gap-2 rounded-full border border-[#E5DFD3] bg-white px-4 py-[7px] pl-3 text-[13px] font-semibold text-[#6E6678] [animation-delay:0.05s]">
                            <Ic d={I.sparkles} size={14} color={T.joy} /> 감정 기반 음악 추천
                        </span>

                        <h1
                            className={`fu mb-6 font-extrabold leading-[1.18] tracking-[-0.035em] text-[#211C26] ${isMobile ? 'text-[clamp(30px,8vw,40px)]' : 'text-[clamp(36px,5vw,64px)]'} [animation-delay:0.15s]`}
                        >
                            지금 기분을 고르면,
                            <br />
                            <span className="bg-[linear-gradient(100deg,#FF6B5E_10%,#FFB648_55%,#7B7FF0_100%)] bg-clip-text text-transparent">
                                그 순간에 맞는 음악이 와요
                            </span>
                        </h1>

                        <p className={`fu mx-auto mb-9 max-w-[540px] leading-[1.7] text-[#6E6678] ${isMobile ? 'text-[16px]' : 'text-[18px]'} [animation-delay:0.25s]`}>
                            Mood Sync는 오늘의 감정을 분석해서 지금 이 기분에 맞는 곡을 찾아주는 서비스예요. Spotify
                            계정을 연결하면 듣고 싶은 곡을 바로 재생할 수 있어요.
                        </p>

                        <div className={`fu mb-5 flex ${isMobile ? 'w-full flex-col' : 'flex-row'} items-stretch justify-center gap-3 [animation-delay:0.35s]`}>
                            <BtnPrimary href="#connect" className={isMobile ? 'w-full justify-center' : 'justify-center'}>
                                <Ic d={I.music} size={18} color="#fff" /> Spotify로 시작하기
                            </BtnPrimary>
                            <BtnGhost href="#concept" fullWidth={isMobile}>
                                <Ic d={I.playCirc} size={17} /> 어떻게 작동하는지 보기
                            </BtnGhost>
                        </div>

                        <p className="fu text-[12.5px] text-[#A39CAC] [animation-delay:0.42s]">
                            무료로 시작 · Spotify 계정만 있으면 바로 사용 가능
                        </p>
                    </div>

                    <div className="fu mx-auto max-w-[980px] [animation-delay:0.4s]">
                        <SpectrumVisual />
                    </div>
                </div>
            </section>

            {/* ── CONCEPT ── */}
            <section id="concept" className={isMobile ? 'py-[72px]' : 'py-[120px]'}>
                <div className={wrap}>
                    <SectionHead
                        center
                        tag="How Mood Sync Works"
                        tagIcon={I.layers}
                        title="감정을 고르면, 음악이 따라와요"
                        desc="곡 목록을 보여주는 게 아니라, 지금 기분을 이해하고 그에 맞는 음악을 찾아드려요."
                    />

                    <div className={`grid gap-5 ${isMobile ? 'grid-cols-1' : isTablet ? 'grid-cols-2' : 'grid-cols-6'}`}>
                        <BentoCard
                            className={isMobile ? 'col-span-1' : isTablet ? 'col-span-2' : 'col-span-3'}
                            iconD={I.smile}
                            iconBg="bg-[#FFEAE6]"
                            iconColor={T.joy}
                            title="오늘 기분을 선택해요"
                            desc="기쁨, 평온, 우울, 설렘처럼 지금 느끼는 감정을 직접 골라요. 복잡한 설문 없이 몇 번의 탭으로 충분해요."
                        >
                            <div className="mt-[22px] flex flex-wrap gap-2">
                                {CHIPS.map((c) => (
                                    <span
                                        key={c.label}
                                        className={`inline-flex items-center gap-1.5 rounded-full px-[14px] py-2 text-[13px] font-semibold ${c.bgClass} ${c.textClass}`}
                                    >
                                        <Ic d={c.icon} size={14} color={c.textClass.includes('9C3D33') ? '#9C3D33' : c.textClass.includes('3D3D8F') ? '#3D3D8F' : c.textClass.includes('B9791E') ? '#B9791E' : T.inkSoft} /> {c.label}
                                    </span>
                                ))}
                            </div>
                        </BentoCard>

                        <BentoCard
                            className={isMobile ? 'col-span-1' : isTablet ? 'col-span-2' : 'col-span-3'}
                            iconD={I.activity}
                            iconBg="bg-[#ECEDFD]"
                            iconColor={T.calm}
                            title="감정을 더 세밀하게 분석해요"
                            desc="선택한 감정 안에서도 결이 달라요. Mood Sync는 그 결을 더 자세히 풀어서 음악으로 옮길 준비를 해요."
                        >
                            <div className="mt-[22px] flex flex-col gap-2.5">
                                {[
                                    ['활기', 'w-[72%]', T.joy],
                                    ['편안함', 'w-[45%]', T.calm],
                                    ['설렘', 'w-[58%]', T.warm],
                                ].map(([label, widthClass, col]) => (
                                    <div key={label} className="flex items-center gap-2.5">
                                        <span className="w-[54px] shrink-0 text-[12.5px] text-[#6E6678]">
                                            {label}
                                        </span>
                                        <div className="h-2 flex-1 overflow-hidden rounded-full bg-[#F1ECE3]">
                                            <div className={`h-full rounded-full ${widthClass} ${col === T.joy ? 'bg-[#FF6B5E]' : col === T.calm ? 'bg-[#7B7FF0]' : 'bg-[#FFB648]'}`} />
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </BentoCard>

                        <BentoCard
                            className={isMobile ? 'col-span-1' : isTablet ? 'col-span-1' : 'col-span-2'}
                            iconD={I.msgCirc}
                            iconBg="bg-[#ECEDFD]"
                            iconColor={T.calm}
                            title="추천 이유를 알려줘요"
                            desc="왜 이 곡인지 항상 짧은 이유와 함께 보여줘요. 막연한 추천이 아니에요."
                        />

                        <BentoCard
                            className={isMobile ? 'col-span-1' : isTablet ? 'col-span-1' : 'col-span-2'}
                            iconD={I.calHeart}
                            iconBg="bg-[#FFF3DE]"
                            iconColor="#B9791E"
                            title="오늘의 감정을 기록해요"
                            desc="매일의 감정과 그날 들은 음악이 쌓여 나만의 감정 다이어리가 돼요."
                        />

                        <BentoCard
                            className={isMobile ? 'col-span-1' : isTablet ? 'col-span-2' : 'col-span-2'}
                            iconD={I.heart}
                            iconBg="bg-[#FFEAE6]"
                            iconColor={T.joy}
                            title="좋아요로 점점 더 맞아가요"
                            desc="좋아요를 누를수록 같은 감정일 때 더 잘 맞는 곡을 찾아드려요."
                        />
                    </div>
                </div>
            </section>

            {/* ── EXAMPLE RESULT ── */}
            <section id="example" className={isMobile ? 'pb-[72px]' : 'pb-[120px]'}>
                <div className={wrap}>
                    <SectionHead
                        center
                        tag="Preview"
                        tagIcon={I.eye}
                        title="추천 결과는 이런 모습이에요"
                        desc="실제 서비스에서 감정을 선택하면 이렇게 추천 이유와 곡이 함께 나타나요. (예시 화면)"
                    />

                    <div className="mx-auto max-w-[680px]">
                        <div className="overflow-hidden rounded-[28px] border border-[#E5DFD3] bg-white shadow-[0_20px_60px_-20px_rgba(33,28,38,0.16)]">
                            <div className={`flex flex-wrap items-center justify-between gap-2.5 border-b border-[#E5DFD3] bg-[#F1ECE3] ${isMobile ? 'px-5 py-[18px]' : 'px-6 py-5'}`}>
                                <div className="flex items-center gap-2.5">
                                    <div className="flex h-[38px] w-[38px] items-center justify-center rounded-[12px] border border-[rgba(255,107,94,0.2)] bg-[#FFEAE6]">
                                        <Ic d={I.smile} size={19} color={T.joy} />
                                    </div>
                                    <div>
                                        <p className="m-0 text-[11px] font-semibold uppercase tracking-[0.06em] text-[#A39CAC]">
                                            오늘의 감정
                                        </p>
                                        <p className="m-0 text-[15px] font-extrabold tracking-[-0.015em] text-[#211C26]">
                                            기쁨 · 활기참
                                        </p>
                                    </div>
                                </div>
                                <div className="flex items-center gap-1.5 rounded-full border border-[#E5DFD3] bg-white px-3 py-[6px] text-[12px] text-[#6E6678]">
                                    <Ic d={I.check} size={12} color={T.calm} />
                                    감정 기록 저장됨
                                </div>
                            </div>

                            <div className={isMobile ? 'px-4 py-[16px] pb-5' : 'px-5 py-5 pb-6'}>
                                <p className="mb-[14px] m-0 text-[12px] font-bold uppercase tracking-[0.07em] text-[#A39CAC]">
                                    추천 곡 · 2곡
                                </p>

                                <TrackCard
                                    index={0}
                                    cover="https://images.unsplash.com/photo-1493225457124-a3eb161ffa5f?w=200&q=80"
                                    title="Dynamite"
                                    artist="BTS"
                                    reason="밝고 리듬감 있는 곡으로, 지금 기분의 활기를 더 끌어올려줄 수 있어요."
                                    spotifyUrl="https://open.spotify.com"
                                />

                                <TrackCard
                                    index={1}
                                    cover="https://images.unsplash.com/photo-1514525253161-7a46d19cd819?w=200&q=80"
                                    title="Good Days"
                                    artist="SZA"
                                    reason="따뜻하고 밝은 멜로디가 오늘 기쁨의 감정과 잘 어울려요."
                                    spotifyUrl="https://open.spotify.com"
                                />

                                {/* ── 하단 출처 ── */}
                                <div className="mt-1 flex flex-wrap items-center justify-between gap-2 border-t border-[#E5DFD3] pt-4">
                                    <a
                                        href="https://open.spotify.com"
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="flex items-center gap-1.5 text-[12px] font-semibold text-[#6E6678] no-underline"
                                    >
                                        <SpotifyMark size={16} />곡 정보:{' '}
                                        <strong className="ml-0.5 font-bold text-[#211C26]">
                                            Provided by Spotify
                                        </strong>
                                    </a>
                                    <a
                                        href="https://open.spotify.com"
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="inline-flex items-center gap-1.5 rounded-full bg-[#1ED760] px-[14px] py-[7px] text-[12px] font-extrabold text-[#191414] no-underline"
                                    >
                                        <Ic d={I.play} size={11} color={T.spotBlack} fill={T.spotBlack} sw={0} />
                                        모두 Spotify에서 듣기
                                    </a>
                                </div>
                            </div>
                        </div>

                        <p className="mt-4 text-center text-[12.5px] text-[#A39CAC]">
                            ↑ 실제 앱에서 보이는 추천 화면이에요. 예시 데이터입니다.
                        </p>
                    </div>
                </div>
            </section>

            {/* ── SPOTIFY CONNECT ── */}
            <section id="connect" className={`relative overflow-hidden ${isMobile ? 'py-[72px]' : 'py-[120px]'} bg-[#211C26] text-[#FAF8F4]`}>
                <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(60%_80%_at_50%_0%,rgba(30,215,96,0.12)_0%,transparent_70%)]" />

                <div className={`relative z-10 grid items-center gap-10 ${wrap} ${isNarrow ? 'grid-cols-1' : 'grid-cols-[1.1fr_0.9fr]'} ${isMobile ? 'gap-10' : 'gap-16'}`}>
                    <div>
                        <div className="mb-[18px] inline-flex items-center gap-1.5 text-[12.5px] font-bold uppercase tracking-[0.07em] text-[#1ED760]">
                            <Ic d={I.link2} size={14} color={T.spotGreen} /> Connect Spotify
                        </div>
                        <h2 className="mb-[18px] text-[clamp(28px,3.2vw,38px)] font-extrabold leading-[1.3] tracking-[-0.03em] text-[#FAF8F4]">
                            Spotify 계정을 연결하면
                            <br />
                            바로 들을 수 있어요
                        </h2>
                        <p className="mb-8 max-w-[460px] text-[16px] leading-[1.75] text-[rgba(250,248,244,0.65)]">
                            Mood Sync는 Spotify의 음악 데이터를 활용해서 추천해요. 계정을 연결하면 추천받은 곡을 끊김
                            없이 Spotify에서 바로 재생할 수 있어요.
                        </p>
                        <a href="#" className={`inline-flex items-center justify-center gap-2.5 rounded-full bg-[#1ED760] px-[26px] py-4 text-[15.5px] font-extrabold text-[#191414] no-underline transition-transform duration-200 hover:-translate-y-0.5 hover:brightness-105 ${isMobile ? 'w-full' : 'w-auto'}`}>
                            <Ic d={I.music} size={19} color={T.spotBlack} /> Spotify로 계속하기
                        </a>

                        <div className="mt-[22px] flex max-w-[460px] items-start gap-2.5">
                            <Ic d={I.shield} size={15} color="rgba(250,248,244,0.45)" className="mt-px shrink-0" />
                            <span className="text-[12.5px] leading-[1.6] text-[rgba(250,248,244,0.45)]">
                                Mood Sync는 Spotify와 제휴되거나 Spotify의 승인을 받은 서비스가 아니에요. 표시되는 모든
                                곡 정보와 앨범 커버의 출처는 Spotify이며, 권리는 Spotify 및 각 권리자에게 있어요.
                            </span>
                        </div>
                    </div>

                    <div className={`rounded-[24px] border border-[rgba(250,248,244,0.12)] bg-[rgba(250,248,244,0.04)] ${isMobile ? 'p-[22px]' : 'p-8'}`}>
                        {[
                            [
                                I.imgIcon,
                                '원본 그대로의 앨범 커버',
                                '커버 이미지는 보정 없이 Spotify 원본을 그대로 보여줘요.',
                            ],
                            [
                                I.extLink,
                                '모든 곡에 연결된 링크',
                                '추천된 모든 곡은 해당 Spotify 페이지로 바로 이동할 수 있어요.',
                            ],
                            [I.badge, '명확한 출처 표시', '곡 정보가 보이는 곳마다 Spotify 제공 표시가 함께 나와요.'],
                        ].map(([icon, title, desc], idx) => (
                            <div key={idx} className={`flex items-start gap-[14px] ${idx < 2 ? 'border-b border-[rgba(250,248,244,0.10)]' : ''} ${idx === 0 ? 'pt-0 pb-4' : idx === 2 ? 'pt-4 pb-0' : 'py-4'}`}>
                                <div className="flex h-[34px] w-[34px] shrink-0 items-center justify-center rounded-[10px] bg-[rgba(30,215,96,0.14)]">
                                    <Ic d={icon} size={17} color={T.spotGreen} />
                                </div>
                                <div>
                                    <strong className="mb-[3px] block text-[14.5px] font-bold text-[#FAF8F4]">
                                        {title}
                                    </strong>
                                    <span className="text-[13px] leading-[1.6] text-[rgba(250,248,244,0.55)]">
                                        {desc}
                                    </span>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* ── DIFFERENTIATORS ── */}
            <section className={isMobile ? 'py-[72px]' : 'py-[120px]'}>
                <div className={wrap}>
                    <SectionHead
                        center
                        tag="Only on Mood Sync"
                        tagIcon={I.gem}
                        title="음악만 나열하지 않아요"
                        desc="Mood Sync는 곡 목록이 아니라 감정의 흐름을 보여주는 서비스예요."
                    />

                    <div className={`grid gap-5 ${isMobile ? 'grid-cols-1' : isTablet ? 'grid-cols-2' : 'grid-cols-4'}`}>
                        <FeatureCard icon={I.bar} bgClass="bg-[#FFEAE6]" iconColor={T.joy} title="감정 분석 결과" desc="선택한 감정을 더 세밀한 지표로 풀어서 보여줘요." />
                        <FeatureCard icon={I.msgSq} bgClass="bg-[#FFF3DE]" iconColor="#B9791E" title="추천 이유 설명" desc="왜 이 곡인지 항상 이유를 함께 알려드려요." />
                        <FeatureCard icon={I.book} bgClass="bg-[#ECEDFD]" iconColor={T.calm} title="오늘의 감정 기록" desc="매일의 감정과 음악이 쌓여 감정 다이어리가 돼요." />
                        <FeatureCard icon={I.thumb} bgClass="bg-[#F1ECE3]" iconColor={T.inkSoft} title="좋아요 기반 추천" desc="쓸수록 나에게 더 잘 맞는 곡을 찾아드려요." />
                    </div>
                </div>
            </section>

            {/* ── FINAL CTA ── */}
            <section className={isMobile ? 'pb-[72px]' : 'pb-[120px]'}>
                <div className={wrap}>
                    <div className={`rounded-[32px] border border-[#E5DFD3] bg-[linear-gradient(135deg,#FFEAE6_0%,#ECEDFD_100%)] ${isMobile ? 'px-6 py-[52px]' : 'px-10 py-20'} text-center`}>
                        <h2 className={`mx-auto mb-4 max-w-[600px] text-[clamp(26px,3.6vw,40px)] font-extrabold leading-[1.25] tracking-[-0.03em] text-[#211C26] ${isNarrow ? 'whitespace-normal' : 'whitespace-nowrap'}`}>
                            오늘 기분, Mood Sync에게 들려주세요
                        </h2>
                        <p className="mb-8 text-[16px] text-[#6E6678]">
                            감정 하나 고르는 데 걸리는 시간은 5초예요.
                        </p>
                        <BtnPrimary href="#connect">
                            <Ic d={I.music} size={18} color="#fff" /> 무료로 시작하기
                        </BtnPrimary>
                    </div>
                </div>
            </section>

            <Footer wrap={wrap} isMobile={isMobile} />
        </div>
    );
}
