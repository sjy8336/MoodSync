import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

const LogoMark = ({ size = 24 }) => (
    <svg width={size} height={size} viewBox="0 0 48 48" fill="none" className="block shrink-0">
        <defs>
            <linearGradient id="footerLogoStroke" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#FF6B5E" />
                <stop offset="50%" stopColor="#7B7FF0" />
                <stop offset="100%" stopColor="#FFB648" />
            </linearGradient>
            <linearGradient id="footerLogoWave" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stopColor="#FF6B5E" />
                <stop offset="50%" stopColor="#7B7FF0" />
                <stop offset="100%" stopColor="#FFB648" />
            </linearGradient>
        </defs>
        <rect
            x="5"
            y="5"
            width="38"
            height="38"
            rx="13"
            stroke="url(#footerLogoStroke)"
            strokeWidth="2.2"
            fill="none"
        />
        <path
            d="M12 26 C14.5 19 17 19 18.5 24.5 C20 30 22.5 30 24 23 C25.5 16 28 16 29.5 21.5 C31 27 33.5 27 36 22"
            stroke="url(#footerLogoWave)"
            strokeWidth="2.6"
            strokeLinecap="round"
            strokeLinejoin="round"
            fill="none"
        />
    </svg>
);

const SpotifyMark = ({ size = 14 }) => (
    <svg width={size} height={size} viewBox="0 0 24 24" className="inline-block shrink-0">
        <circle cx="12" cy="12" r="12" fill="#1ED760" />
        <path
            d="M17.5 10.7c-3-1.8-7.9-2-10.7-1.1a.7.7 0 1 1-.4-1.4c3.2-1 8.7-.8 12.1 1.2a.7.7 0 0 1-.7 1.3h-.3zm-.1 2.9c-2.5-1.5-6.3-2-9.3-1.1a.6.6 0 1 1-.3-1.1c3.4-1 7.6-.5 10.5 1.2a.6.6 0 0 1-.6 1h-.3zm-.3 2.8c-2.2-1.3-4.9-1.6-8-.9a.5.5 0 1 1-.2-1c3.4-.8 6.4-.4 8.8 1a.5.5 0 0 1-.6.9z"
            fill="white"
        />
    </svg>
);

const normalizeWrap = (wrap) => {
    if (typeof wrap === 'string') return wrap;
    if (!wrap || typeof wrap !== 'object') return '';

    const parts = [];

    if (wrap.width === '100%') parts.push('w-full');

    if (wrap.maxWidth === 1240 || wrap.maxWidth === '1240px' || wrap.maxWidth === '1240') {
        parts.push('max-w-[1240px]');
    } else if (wrap.maxWidth === 1080 || wrap.maxWidth === '1080px' || wrap.maxWidth === '1080') {
        parts.push('max-w-[1080px]');
    } else if (wrap.maxWidth === 860 || wrap.maxWidth === '860px' || wrap.maxWidth === '860') {
        parts.push('max-w-[860px]');
    }

    if (wrap.margin === '0 auto') parts.push('mx-auto');

    if (wrap.padding === '0 20px') parts.push('px-5');
    else if (wrap.padding === '0 28px') parts.push('px-7');
    else if (wrap.padding === '0 40px') parts.push('px-10');
    else if (wrap.padding === '0 24px') parts.push('px-6');

    return parts.join(' ');
};

const FOOTER_NAV_GROUPS = [
    {
        title: '서비스',
        links: [
            { to: '/mood-input', label: '감정 기록' },
            { to: '/recommendations', label: '추천 음악' },
            { to: '/history', label: '히스토리' },
            { to: '/favorites', label: '좋아요한 곡' },
        ],
    },
    {
        title: '고객지원',
        links: [
            { to: '/my', label: '마이페이지' },
            { to: '/support', label: '문의하기' },
            { to: '/faq', label: '자주 묻는 질문' },
        ],
    },
    {
        title: '약관',
        links: [
            { to: '/terms', label: '이용약관' },
            { to: '/privacy', label: '개인정보처리방침' },
        ],
    },
];

export default function Footer({ wrap = '', isMobile }) {
    const [isNarrowViewport, setIsNarrowViewport] = useState(false);

    useEffect(() => {
        const updateViewport = () => setIsNarrowViewport(window.innerWidth < 768);
        updateViewport();
        window.addEventListener('resize', updateViewport);
        return () => window.removeEventListener('resize', updateViewport);
    }, []);

    const compactLayout = typeof isMobile === 'boolean' ? isMobile : isNarrowViewport;
    const wrapClassName =
        normalizeWrap(wrap) || 'max-w-[1240px] mx-auto px-5 min-[560px]:px-7 min-[900px]:px-10';
    const year = new Date().getFullYear();

    return (
        <footer className="border-t border-[#E5DFD3] bg-[#FAF8F4] pt-14 pb-8">
            <div className={`w-full ${wrapClassName}`}>

                <div className="flex flex-col gap-10 md:flex-row md:justify-between md:gap-6">

                    <div className="max-w-[280px]">
                        <Link
                            to="/"
                            className="flex items-center gap-2.5 text-[15px] font-extrabold tracking-[-0.02em] text-[#211C26] no-underline"
                        >
                            <LogoMark size={26} /> Mood Sync
                        </Link>
                        <p className="mt-3 text-[13px] leading-[1.7] text-[#6E6678]">
                            지금의 감정을 기록하고, 그 순간에 어울리는 음악을 Spotify에서 찾아드려요.
                        </p>
                        <span className="mt-4 inline-flex items-center gap-1.5 rounded-full bg-[#EAFBF0] px-2.5 py-1 text-[11px] font-semibold text-[#1a9e4c]">
                            <SpotifyMark size={12} />
                            Powered by Spotify
                        </span>
                    </div>


                    <div className="grid grid-cols-2 gap-8 sm:grid-cols-3 md:gap-12">
                        {FOOTER_NAV_GROUPS.map((group) => (
                            <div key={group.title}>
                                <p className="text-[12px] font-bold uppercase tracking-[0.06em] text-[#A39CAC]">
                                    {group.title}
                                </p>
                                <ul className="mt-3 flex flex-col gap-2.5">
                                    {group.links.map((link) => (
                                        <li key={link.to}>
                                            <Link
                                                to={link.to}
                                                className="text-[13.5px] text-[#6E6678] no-underline transition-colors duration-150 hover:text-[#211C26]"
                                            >
                                                {link.label}
                                            </Link>
                                        </li>
                                    ))}
                                </ul>
                            </div>
                        ))}
                    </div>
                </div>


                <div className="my-9 h-px w-full bg-[#E5DFD3]" />


                <div
                    className={`flex flex-col gap-4 ${
                        compactLayout ? 'items-start' : 'md:flex-row md:items-end md:justify-between'
                    }`}
                >
                    <p className="text-[11.5px] text-[#A39CAC]">© {year} Mood Sync. All rights reserved.</p>

                    <p
                        className={`max-w-[460px] text-[11px] leading-[1.7] text-[#A39CAC] ${
                            compactLayout ? 'text-left' : 'text-right'
                        }`}
                    >
                        Mood Sync는 Spotify와 제휴되거나 Spotify의 승인을 받은 서비스가 아닙니다.
                        <br />
                        모든 음악 데이터의 출처는 Spotify이며, 해당 저작권은 Spotify 및 각 권리자에게 있습니다.
                    </p>
                </div>
            </div>
        </footer>
    );
}
