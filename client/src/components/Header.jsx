import { useEffect, useRef, useState } from 'react';
import { Link, NavLink, useLocation, useNavigate } from 'react-router-dom';
import { logoutAccount } from '../services/apiClient';
import { useAuth } from '../contexts/AuthContext';

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
    arrowL: 'M19 12H5M12 19l-7-7 7-7',
    user: ['M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2', 'M12 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8z'],
    headset: [
        'M3 18v-6a9 9 0 1 1 18 0v6',
        'M21 19a2 2 0 0 1-2 2h-1a2 2 0 0 1-2-2v-3a2 2 0 0 1 2-2h3zM3 19a2 2 0 0 0 2 2h1a2 2 0 0 0 2-2v-3a2 2 0 0 0-2-2H3z',
    ],
    logout: ['M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4', 'M16 17l5-5-5-5', 'M21 12H9'],
    chevDown: 'M6 9l6 6 6-6',
    waveform: 'M2 12h2M6 8v8M10 5v14M14 9v6M18 6v12M22 12h2',
};

const logoSizeClassMap = {
    24: 'h-6 w-6',
    27: 'h-[27px] w-[27px]',
    30: 'h-[30px] w-[30px]',
    36: 'h-[36px] w-[36px]',
    38: 'h-[38px] w-[38px]',
};

const LogoMark = ({ size = 30 }) => (
    <div
        className={`flex shrink-0 items-center justify-center rounded-[30%] bg-[linear-gradient(135deg,#FF6B5E_0%,#7B7FF0_100%)] ${
            logoSizeClassMap[size] || logoSizeClassMap[30]
        }`}
    >
        <Ic d={I.waveform} size={size * 0.47} color="#fff" sw={2} />
    </div>
);

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

const ROUTE_CONFIG = {
    '/': {
        type: 'landing',
        title: 'Mood Sync',
        showBack: false,
        showLogo: true,
        showProfileButton: false,
        showLoginButton: true,
    },
    '/login': {
        type: 'minimal',
        title: 'Mood Sync',
        showBack: true,
        showLogo: true,
        showProfileButton: false,
        showLoginButton: false,
    },
    '/home': {
        type: 'home',
        title: 'Mood Sync',
        showBack: false,
        showLogo: true,
        showProfileButton: true,
        showLoginButton: false,
    },
    '/mood-input': {
        type: 'sub',
        title: '오늘의 감정 기록',
        showBack: true,
        showLogo: false,
        showProfileButton: false,
        showLoginButton: false,
    },
    '/recommendations': {
        type: 'sub',
        title: '추천 음악',
        showBack: true,
        showLogo: false,
        showProfileButton: false,
        showLoginButton: false,
    },
    '/history': {
        type: 'tab',
        title: '감정 기록',
        showBack: false,
        showLogo: false,
        showProfileButton: false,
        showLoginButton: false,
    },
    '/favorites': {
        type: 'tab',
        title: '좋아요한 음악',
        showBack: false,
        showLogo: false,
        showProfileButton: false,
        showLoginButton: false,
    },
    '/my': {
        type: 'tab',
        title: '마이페이지',
        showBack: false,
        showLogo: false,
        showProfileButton: false,
        showLoginButton: false,
    },
};

const PC_NAV_MENUS = [
    { to: '/mood-input', label: '감정 기록' },
    { to: '/recommendations', label: '추천 음악' },
    { to: '/history', label: '히스토리' },
    { to: '/favorites', label: '좋아요' },
];

const navLinkClassName = ({ isActive }) =>
    `rounded-full px-[14px] py-[9px] text-[14px] transition-all duration-200 ${
        isActive
            ? 'bg-[#F1ECE3] font-semibold text-[#211C26]'
            : 'bg-transparent font-medium text-[#6E6678] hover:bg-[#F1ECE3] hover:text-[#211C26]'
    }`;

const PROFILE_MENU_ITEMS = [
    { to: '/my', label: '마이페이지', icon: I.user },
    { to: '/history', label: '기록 보기', icon: I.headset },
];

function ProfileMenu({ size = 38, iconSize = 18 }) {
    const [open, setOpen] = useState(false);
    const rootRef = useRef(null);
    const navigate = useNavigate();
    const { logout } = useAuth();

    useEffect(() => {
        if (!open) return;

        const onPointerDown = (e) => {
            if (rootRef.current && !rootRef.current.contains(e.target)) setOpen(false);
        };
        const onKeyDown = (e) => {
            if (e.key === 'Escape') setOpen(false);
        };

        document.addEventListener('mousedown', onPointerDown);
        document.addEventListener('keydown', onKeyDown);
        return () => {
            document.removeEventListener('mousedown', onPointerDown);
            document.removeEventListener('keydown', onKeyDown);
        };
    }, [open]);

    const handleLogout = async () => {
        setOpen(false);
        try {
            await logoutAccount();
        } catch {
            void 0;
        } finally {
            logout();
            navigate('/login', { replace: true });
        }
    };

    const buttonSizeClass = size === 36 ? 'h-[36px] w-[36px]' : 'h-[38px] w-[38px]';

    return (
        <div ref={rootRef} className="relative">
            <button
                onClick={() => navigate('/my')}
                aria-label="프로필 메뉴 열기"
                aria-expanded={open}
                className={`flex items-center justify-center rounded-full border-[1.5px] bg-[#F1ECE3] text-[#211C26] transition-all duration-150 ${
                    open ? 'scale-95 border-[#211C26]' : 'border-[#E5DFD3] hover:border-[#211C26]'
                } ${buttonSizeClass}`}
            >
                <Ic d={I.user} size={iconSize} color="#211C26" />
            </button>

            {open && (
                <div
                    role="menu"
                    className="absolute right-0 top-full mt-2.5 min-w-[196px] origin-top-right rounded-2xl border border-[#E5DFD3] bg-white p-1.5 shadow-[0_16px_40px_-12px_rgba(33,28,38,0.18),0_4px_12px_-4px_rgba(33,28,38,0.08)]"
                >
                    {PROFILE_MENU_ITEMS.map(({ to, label, icon }) => (
                        <Link
                            key={to}
                            to={to}
                            role="menuitem"
                            onClick={() => setOpen(false)}
                            className="flex items-center gap-2.5 rounded-[11px] px-3 py-2.5 text-[14px] font-semibold text-[#211C26] no-underline transition-colors hover:bg-[#F1ECE3]"
                        >
                            <Ic d={icon} size={16} color="#6E6678" />
                            {label}
                        </Link>
                    ))}

                    <div className="mx-1 my-1 h-px bg-[#E5DFD3]" />

                    <button
                        role="menuitem"
                        onClick={handleLogout}
                        className="flex w-full items-center gap-2.5 rounded-[11px] px-3 py-2.5 text-left text-[14px] font-semibold text-[#E0473E] transition-colors hover:bg-[#FDEDEC]"
                    >
                        <Ic d={I.logout} size={16} color="#E0473E" />
                        로그아웃
                    </button>
                </div>
            )}
        </div>
    );
}

export default function Header() {
    const [scrolled, setScrolled] = useState(false);
    const bp = useBreakpoint();
    const isMobile = bp === 'mobile';
    const isTablet = bp === 'tablet';
    const isDesktop = bp === 'desktop';

    const location = useLocation();
    const navigate = useNavigate();

    const routeKey = Object.keys(ROUTE_CONFIG).find((k) => location.pathname === k) || '/home';
    const config = ROUTE_CONFIG[routeKey] || ROUTE_CONFIG['/home'];
    const isAppPage = !['/', '/login'].includes(location.pathname);

    useEffect(() => {
        const fn = () => setScrolled(window.scrollY > 8);
        window.addEventListener('scroll', fn);
        return () => window.removeEventListener('scroll', fn);
    }, []);

    const pillPaddingClass = isMobile || isTablet ? 'px-4 py-[10px]' : 'pl-[18px] pr-[10px] py-[10px]';


    const pillClassName = `relative isolate flex items-center justify-between overflow-hidden rounded-full transition-all duration-500 ease-out before:pointer-events-none before:absolute before:inset-x-6 before:top-0 before:h-px before:bg-gradient-to-r before:from-transparent before:via-white/80 before:to-transparent before:transition-opacity before:duration-500 ${
        scrolled
            ? 'border border-white/60 bg-white/55 shadow-[0_8px_32px_-10px_rgba(33,28,38,0.22),0_2px_10px_-4px_rgba(123,127,240,0.28)] backdrop-blur-xl backdrop-saturate-[180%] before:opacity-100'
            : 'border border-transparent bg-transparent shadow-none backdrop-blur-0 before:opacity-0'
    } ${pillPaddingClass} ${isMobile ? 'min-h-[56px]' : 'min-h-[60px]'}`;

    const renderLeft = () => {
        if (config.showBack && (isMobile || isTablet)) {
            return (
                <button
                    onClick={() => navigate(-1)}
                    aria-label="뒤로가기"
                    className="flex items-center gap-1.5 bg-transparent px-[2px] py-[4px] text-[15px] font-semibold text-[#211C26]"
                >
                    <Ic d={I.arrowL} size={20} color="#211C26" />
                </button>
            );
        }

        if (config.showLogo || isDesktop) {
            return (
                <Link
                    to="/home"
                    className={`flex items-center gap-[9px] font-extrabold tracking-[-0.03em] text-[#211C26] no-underline ${
                        isMobile ? 'text-[15px]' : 'text-[16px]'
                    }`}
                >
                    <LogoMark size={isMobile ? 27 : 30} />
                    Mood Sync
                </Link>
            );
        }

        return null;
    };

    const renderCenter = () => {
        if (isDesktop) {
            if (!isAppPage) return null;

            return (
                <div className="absolute left-1/2 flex -translate-x-1/2 items-center gap-1">
                    {PC_NAV_MENUS.map(({ to, label }) => (
                        <NavLink key={to} to={to} className={navLinkClassName}>
                            {label}
                        </NavLink>
                    ))}
                </div>
            );
        }

        const isSubOrTab = config.type === 'sub' || config.type === 'tab';
        if (!isSubOrTab) return null;

        return (
            <span
                className={`pointer-events-none absolute left-1/2 -translate-x-1/2 whitespace-nowrap font-bold tracking-[-0.01em] text-[#211C26] ${
                    isMobile ? 'text-[16px]' : 'text-[17px]'
                }`}
            >
                {config.title}
            </span>
        );
    };

    const renderRight = () => {
        if (isDesktop) {
            if (!isAppPage) {
                return config.showLoginButton ? (
                    <Link
                        to="/login"
                        className="flex items-center gap-1.5 rounded-full bg-[#211C26] px-5 py-[11px] text-[14px] font-bold text-white no-underline transition-all duration-200 hover:-translate-y-px hover:shadow-[0_12px_32px_-8px_rgba(33,28,38,0.4)]"
                    >
                        시작하기
                    </Link>
                ) : null;
            }

            return <ProfileMenu size={38} iconSize={18} />;
        }

        if (isTablet) {
            if (isAppPage) {
                return <ProfileMenu size={36} iconSize={17} />;
            }

            return config.showLoginButton ? (
                <Link
                    to="/login"
                    className="rounded-full bg-[#211C26] px-4 py-[9px] text-[13px] font-bold text-white no-underline"
                >
                    시작하기
                </Link>
            ) : null;
        }

        if (isMobile) {
            if (config.showProfileButton) {
                return <ProfileMenu size={36} iconSize={16} />;
            }

            if (config.showLoginButton) {
                return (
                    <Link
                        to="/login"
                        className="rounded-full bg-[#211C26] px-4 py-[9px] text-[13px] font-bold text-white no-underline"
                    >
                        시작하기
                    </Link>
                );
            }
        }

        return null;
    };

    return (
        <nav className={`fixed inset-x-0 top-0 z-[100] ${isMobile ? 'pt-[12px]' : 'pt-[18px]'}`}>
            <div
                className={`ms-header-inner ${
                    isDesktop ? 'ms-header-pad-desktop' : isTablet ? 'ms-header-pad-tablet' : 'ms-header-pad-mobile'
                }`}
            >
                <div className={pillClassName}>
                    <div className="z-[1] flex items-center">{renderLeft()}</div>
                    {renderCenter()}
                    <div className="z-[1] flex items-center gap-2">{renderRight()}</div>
                </div>
            </div>
        </nav>
    );
}
