import { useEffect, useState } from 'react';
import { Link, useLocation, useNavigate, useSearchParams } from 'react-router-dom';
import { getSpotifyCallback, getSpotifyLoginUrl, startDemoSession } from '../services/apiClient';
import { useAuth } from '../contexts/AuthContext';
import { normalizeAuthUser } from '../utils/authStorage';


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
    arrowR: 'M5 12h14M12 5l7 7-7 7',
    shield: ['M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z', 'M9 12l2 2 4-4'],
    smile: [
        'M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10z',
        'M8 14s1.5 2 4 2 4-2 4-2',
        'M9 9h.01M15 9h.01',
    ],
    calHeart: [
        'M8 2v4M16 2v4M3 10h18M3 6a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h18a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2H3z',
        'M12 17a2 2 0 0 0 2-2c0-1-1-2-2-3-1 1-2 2-2 3a2 2 0 0 0 2 2z',
    ],
    waveform: 'M2 12h2M6 8v8M10 5v14M14 9v6M18 6v12M22 12h2',
    alertCircle: ['M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10z', 'M12 8v4M12 16h.01'],
    arrowLeft: 'M19 12H5M12 19l-7-7 7-7',
    check: 'M20 6 9 17l-5-5',
    lock: ['M19 11H5a2 2 0 0 0-2 2v7a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7a2 2 0 0 0-2-2z', 'M7 11V7a5 5 0 0 1 10 0v4'],
};


const SpotifyMark = ({ size = 20 }) => (
    <svg width={size} height={size} viewBox="0 0 24 24" className="inline-block shrink-0">
        <circle cx="12" cy="12" r="12" fill="#1ED760" />
        <path
            d="M17.5 10.7c-3-1.8-7.9-2-10.7-1.1a.7.7 0 1 1-.4-1.4c3.2-1 8.7-.8 12.1 1.2a.7.7 0 0 1-.7 1.3h-.3zm-.1 2.9c-2.5-1.5-6.3-2-9.3-1.1a.6.6 0 1 1-.3-1.1c3.4-1 7.6-.5 10.5 1.2a.6.6 0 0 1-.6 1h-.3zm-.3 2.8c-2.2-1.3-4.9-1.6-8-.9a.5.5 0 1 1-.2-1c3.4-.8 6.4-.4 8.8 1a.5.5 0 0 1-.6.9z"
            fill="white"
        />
    </svg>
);

const OAUTH_STATE_KEY = 'mood-sync-spotify-state';

const DEMO_PRESETS = [
    {
        id: 'focus',
        label: '집중 테스트',
        description: '공부, 작업, 마감 전에 어울리는 차분한 추천 흐름을 확인해요.',
        badge: '집중 / 몰입',
        delayClass: '[animation-delay:0.42s]',
    },
    {
        id: 'jazz',
        label: '재즈 테스트',
        description: '스윙, 비밥, 보사노바처럼 재즈 서브장르 반응을 확인해요.',
        badge: '재즈 / 서브장르',
        delayClass: '[animation-delay:0.45s]',
    },
    {
        id: 'calm',
        label: '밤공기 테스트',
        description: '잔잔함, 외로움, 새벽 감성처럼 부드러운 추천을 확인해요.',
        badge: '잔잔 / 새벽',
        delayClass: '[animation-delay:0.48s]',
    },
    {
        id: 'emotional',
        label: '감성 테스트',
        description: '감정 분석이 추천 결과와 어떻게 연결되는지 살펴봐요.',
        badge: '감성 / 서사',
        delayClass: '[animation-delay:0.51s]',
    },
];

const createOauthState = () => {
    if (window.crypto?.randomUUID) {
        return window.crypto.randomUUID().replaceAll('-', '');
    }
    return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
};


const MiniWave = () => {
    const bars = [
        { h: 'h-[28%]', opacity: 'opacity-[0.45]', delayClass: '[animation-delay:0s]', color: 'bg-[#FF6B5E]' },
        { h: 'h-[48%]', opacity: 'opacity-[0.55]', delayClass: '[animation-delay:0.12s]', color: 'bg-[#7B7FF0]' },
        { h: 'h-[36%]', opacity: 'opacity-[0.65]', delayClass: '[animation-delay:0.24s]', color: 'bg-[#FFB648]' },
        { h: 'h-[62%]', opacity: 'opacity-[0.75]', delayClass: '[animation-delay:0.36s]', color: 'bg-[#FF6B5E]' },
        { h: 'h-[44%]', opacity: 'opacity-[0.45]', delayClass: '[animation-delay:0.48s]', color: 'bg-[#7B7FF0]' },
        { h: 'h-[72%]', opacity: 'opacity-[0.55]', delayClass: '[animation-delay:0.6s]', color: 'bg-[#FFB648]' },
        { h: 'h-[52%]', opacity: 'opacity-[0.65]', delayClass: '[animation-delay:0.72s]', color: 'bg-[#FF6B5E]' },
        { h: 'h-[40%]', opacity: 'opacity-[0.75]', delayClass: '[animation-delay:0.84s]', color: 'bg-[#7B7FF0]' },
        { h: 'h-[80%]', opacity: 'opacity-[0.45]', delayClass: '[animation-delay:0.96s]', color: 'bg-[#FFB648]' },
        { h: 'h-[58%]', opacity: 'opacity-[0.55]', delayClass: '[animation-delay:1.08s]', color: 'bg-[#FF6B5E]' },
        { h: 'h-[68%]', opacity: 'opacity-[0.65]', delayClass: '[animation-delay:1.2s]', color: 'bg-[#7B7FF0]' },
        { h: 'h-[46%]', opacity: 'opacity-[0.75]', delayClass: '[animation-delay:1.32s]', color: 'bg-[#FFB648]' },
    ];
    return (
        <div className="flex items-end gap-[5px] h-16 mb-10">
            {bars.map((bar, i) => (
                <div
                    key={i}
                    className={`flex-1 rounded-t-[4px] ${bar.h} ${bar.opacity} ${bar.color} [animation:ms-float_2.2s_ease-in-out_infinite] ${bar.delayClass}`}
                />
            ))}
        </div>
    );
};


export default function LoginPage() {
    const [searchParams] = useSearchParams();
    const navigate = useNavigate();
    const location = useLocation();
    const { login, isAuthenticated } = useAuth();
    const [loading, setLoading] = useState(false);
    const [demoLoading, setDemoLoading] = useState(false);
    const [error, setError] = useState('');
    const [message, setMessage] = useState('');
    const [selectedPreset, setSelectedPreset] = useState(DEMO_PRESETS[0]);
    const fromPath = location.state?.from || '/home';

    useEffect(() => {
        if (isAuthenticated) {
            navigate(fromPath, { replace: true });
        }
    }, [fromPath, isAuthenticated, navigate]);

    useEffect(() => {
        const code = searchParams.get('code');
        const state = searchParams.get('state');
        const oauthError = searchParams.get('error');
        if (oauthError) {
            setError(`Spotify 로그인 실패: ${oauthError}`);
            return;
        }
        if (!code || !state) return;
        const expectedState = window.sessionStorage.getItem(OAUTH_STATE_KEY);
        if (!expectedState || expectedState !== state) {
            setError('Spotify 로그인 상태가 맞지 않아요. 다시 시도해 주세요.');
            window.sessionStorage.removeItem(OAUTH_STATE_KEY);
            return;
        }
        window.sessionStorage.removeItem(OAUTH_STATE_KEY);
        setLoading(true);
        getSpotifyCallback(code, state)
            .then((data) => {
                const nextUser = normalizeAuthUser(
                    data?.user || {
                        id: 'spotify-user',
                        email: 'spotify-user@example.com',
                        provider_user_id: 'Spotify 사용자',
                        authType: 'spotify',
                    },
                );
                login(nextUser);
                setMessage(data?.message || 'Spotify login success');
                setTimeout(() => navigate(fromPath, { replace: true }), 600);
            })
            .catch((err) => setError(err.message || '로그인 콜백 처리 중 오류가 발생했습니다.'))
            .finally(() => setLoading(false));
    }, [fromPath, login, navigate, searchParams]);

    const handleSpotifyLogin = () => {
        const state = createOauthState();
        window.sessionStorage.setItem(OAUTH_STATE_KEY, state);
        window.location.href = getSpotifyLoginUrl(state);
    };

    const handleDemoLogin = async () => {
        setError('');
        setMessage('');
        setDemoLoading(true);
        try {
            const data = await startDemoSession({ preset: selectedPreset.id });
            const nextUser = normalizeAuthUser(
                data?.user || {
                    id: 'demo-user',
                    display_name: 'Demo User',
                    auth_provider: 'demo',
                },
            );
            login(nextUser);
            setMessage(data?.message || `${selectedPreset.label}로 데모를 시작했어요.`);
            setTimeout(() => navigate(fromPath, { replace: true }), 500);
        } catch (err) {
            setError(err.message || '데모 세션을 시작하지 못했어요.');
        } finally {
            setDemoLoading(false);
        }
    };


    if (loading || demoLoading) {
        return (
            <div className="min-h-screen flex flex-col items-center justify-center gap-4 bg-[#FAF8F4] font-[Pretendard,system-ui,sans-serif]">
                <div
                    className="w-11 h-11 rounded-full border-[3px] border-[#E5DFD3] [border-top-color:#1ED760] [animation:ms-spin_0.9s_linear_infinite]"
                />
                <p className="text-[15px] font-semibold text-[#6E6678]">
                    {demoLoading ? '데모 시나리오를 준비하는 중이에요…' : 'Spotify 계정을 확인하는 중이에요…'}
                </p>
                {message && <p className="text-[13px] text-[#A39CAC]">{message}</p>}
            </div>
        );
    }


    return (
        <div className="min-h-screen bg-[#FAF8F4] font-[Pretendard,system-ui,sans-serif] antialiased overflow-x-hidden">

            <div className="grid grid-cols-1 md:grid-cols-2 min-h-screen">

                <aside className="hidden md:flex flex-col justify-between bg-[#211C26] px-12 py-11 relative overflow-hidden">

                    <div
                        className="absolute inset-0 pointer-events-none bg-[radial-gradient(60%_60%_at_20%_80%,rgba(123,127,240,0.22)_0%,transparent_70%),radial-gradient(40%_50%_at_80%_10%,rgba(255,107,94,0.15)_0%,transparent_70%)]"
                    />


                    <Link to="/" className="relative z-10 flex items-center gap-[9px] no-underline w-fit">
                        <div
                            className="w-[34px] h-[34px] rounded-[10px] flex items-center justify-center shrink-0 bg-[linear-gradient(135deg,#FF6B5E_0%,#7B7FF0_100%)]"
                        >
                            <Ic d={I.waveform} size={17} color="#fff" sw={2} />
                        </div>
                        <span className="text-[18px] font-extrabold tracking-[-0.03em] text-[#FAF8F4]">Mood Sync</span>
                    </Link>


                    <div className="relative z-10">
                        <MiniWave />

                        <h2 className="text-[clamp(26px,2.6vw,36px)] font-extrabold tracking-[-0.035em] leading-[1.22] text-[#FAF8F4] mb-[18px]">
                            지금 기분을 고르면,
                            <br />
                            <span
                                className="bg-[linear-gradient(100deg,#FF6B5E_0%,#FFB648_55%,#7B7FF0_100%)] bg-clip-text text-transparent"
                            >
                                그 순간에 맞는 음악이 와요
                            </span>
                        </h2>

                        <p className="text-[15px] leading-[1.72] text-[rgba(250,248,244,0.55)] mb-10 max-w-[360px]">
                            감정을 선택하면 지금 이 기분에 맞는 곡을 찾아드려요.
                            <br />
                            Spotify 계정을 연결하면 바로 들을 수 있어요.
                        </p>


                        <div className="flex flex-col gap-5">
                            {[
                                {
                                    d: I.smile,
                                    bgClass: 'bg-[rgba(255,107,94,0.16)]',
                                    color: '#FF6B5E',
                                    t: '감정 기반 추천',
                                    s: '기쁨, 평온, 우울, 설렘 — 지금 감정에 딱 맞는 곡을 찾아드려요.',
                                },
                                {
                                    d: I.calHeart,
                                    bgClass: 'bg-[rgba(255,182,72,0.16)]',
                                    color: '#FFB648',
                                    t: '감정 다이어리',
                                    s: '매일의 감정과 음악이 쌓여 나만의 기록이 돼요.',
                                },
                                {
                                    d: I.shield,
                                    bgClass: 'bg-[rgba(123,127,240,0.16)]',
                                    color: '#7B7FF0',
                                    t: '안전한 연결',
                                    s: 'Spotify 공식 OAuth만 사용해요. 비밀번호를 입력하지 않아도 돼요.',
                                },
                            ].map((item) => (
                                <div key={item.t} className="flex items-start gap-[14px]">
                                    <div
                                        className={`w-[38px] h-[38px] rounded-[11px] flex items-center justify-center shrink-0 ${item.bgClass}`}
                                    >
                                        <Ic d={item.d} size={17} color={item.color} />
                                    </div>
                                    <div>
                                        <p className="text-[14px] font-bold text-[#FAF8F4] mb-[3px]">{item.t}</p>
                                        <p className="text-[13px] leading-[1.65] text-[rgba(250,248,244,0.5)] m-0">
                                            {item.s}
                                        </p>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>


                    <p className="relative z-10 text-[11.5px] leading-[1.6] text-[rgba(250,248,244,0.28)]">
                        Mood Sync는 Spotify와 제휴 관계가 아니에요.
                        <br />곡 정보의 출처는 Spotify이며, 권리는 각 권리자에게 있어요.
                    </p>
                </aside>


                <main className="relative flex flex-col items-center justify-center overflow-hidden px-6 py-14 sm:px-12 md:px-14 min-h-screen">

                    <div aria-hidden="true" className="absolute inset-0 pointer-events-none overflow-hidden">

                        <div
                            className="absolute -top-[8%] -right-[12%] w-[420px] h-[420px] rounded-full bg-[radial-gradient(circle,rgba(255,107,94,0.16)_0%,transparent_70%)] [animation:ms-orb_9s_ease-in-out_infinite]"
                        />

                        <div
                            className="absolute -bottom-[10%] -left-[14%] w-[460px] h-[460px] rounded-full bg-[radial-gradient(circle,rgba(123,127,240,0.13)_0%,transparent_70%)] [animation:ms-orb_12s_ease-in-out_infinite_reverse] [animation-delay:-3s]"
                        />

                        <div
                            className="absolute top-[40%] left-[30%] w-[300px] h-[300px] rounded-full bg-[radial-gradient(circle,rgba(255,182,72,0.09)_0%,transparent_70%)] [animation:ms-orb_15s_ease-in-out_infinite] [animation-delay:-6s]"
                        />

                        <svg className="absolute inset-0 w-full h-full opacity-[0.022]">
                            <filter id="ms-noise">
                                <feTurbulence type="fractalNoise" baseFrequency="0.65" numOctaves="3" />
                                <feColorMatrix type="saturate" values="0" />
                            </filter>
                            <rect width="100%" height="100%" filter="url(#ms-noise)" />
                        </svg>
                    </div>


                    <div className="md:hidden absolute top-0 left-0 right-0 flex items-center justify-between px-6 py-5 z-10">
                        <Link to="/" className="flex items-center gap-2 no-underline">
                            <div
                                className="w-[30px] h-[30px] rounded-[9px] flex items-center justify-center shrink-0 bg-[linear-gradient(135deg,#FF6B5E_0%,#7B7FF0_100%)]"
                            >
                                <Ic d={I.waveform} size={14} color="#fff" sw={2} />
                            </div>
                            <span className="text-[16px] font-extrabold tracking-[-0.03em] text-[#211C26]">
                                Mood Sync
                            </span>
                        </Link>
                        <Link
                            to="/"
                            className="flex items-center gap-[5px] text-[13px] font-semibold text-[#6E6678] no-underline hover:text-[#211C26] transition-colors duration-150"
                        >
                            <Ic d={I.arrowLeft} size={13} color="currentColor" />
                            홈으로
                        </Link>
                    </div>


                    <div className="relative z-10 w-full max-w-[400px]">

                        <div className="ms-fu inline-flex items-center gap-[7px] text-[12px] font-bold text-[#6E6678] bg-white border border-[#E5DFD3] rounded-full px-[14px] py-[6px] pl-[10px] mb-8 shadow-[0_2px_8px_rgba(33,28,38,0.06)] [animation-delay:0.05s]">
                            <Ic d={I.sparkles} size={13} color="#FF6B5E" />
                            감정 기반 음악 추천
                        </div>


                        <h1 className="ms-fu text-[clamp(28px,3.2vw,38px)] font-extrabold tracking-[-0.035em] leading-[1.18] text-[#211C26] mb-[14px] [animation-delay:0.12s]">
                            오늘 기분,
                            <br />
                            <span className="bg-[linear-gradient(110deg,#FF6B5E_0%,#FFB648_50%,#7B7FF0_100%)] bg-clip-text text-transparent">
                                음악으로 연결해요
                            </span>
                        </h1>


                        <p className="ms-fu text-[15.5px] text-[#6E6678] leading-[1.7] mb-10 max-w-[340px] [animation-delay:0.2s]">
                            Spotify 계정 하나로 시작해요.
                            <br />
                            기분을 고르면 그에 맞는 곡을 바로 들을 수 있어요.
                        </p>


                        {error && (
                            <div className="ms-fu flex items-start gap-[10px] bg-[#FFEAE6] border border-[rgba(255,107,94,0.22)] rounded-2xl px-4 py-[13px] mb-6">
                                <Ic d={I.alertCircle} size={15} color="#FF6B5E" className="mt-[1px] shrink-0" />
                                <p className="text-[13.5px] text-[#8B2218] leading-[1.6] m-0">{error}</p>
                            </div>
                        )}


                        <div className="ms-fu [animation-delay:0.28s]">
                            <button
                                type="button"
                                onClick={handleSpotifyLogin}
                                disabled={loading}
                                className={[
                                    'group relative w-full flex items-center justify-center gap-3',
                                    'bg-[#191414] text-white text-[16px] font-extrabold tracking-[-0.01em]',
                                    'px-7 py-[18px] rounded-[18px] border-none overflow-hidden',
                                    'shadow-[0_4px_16px_rgba(25,20,20,0.14)]',
                                    'transition-all duration-[220ms] [transition-timing-function:cubic-bezier(0.34,1.56,0.64,1)]',
                                    loading
                                        ? 'opacity-60 cursor-not-allowed'
                                        : 'cursor-pointer hover:-translate-y-[3px] hover:shadow-[0_20px_48px_-12px_rgba(25,20,20,0.38),0_0_0_1px_rgba(30,215,96,0.35)]',
                                ].join(' ')}
                            >

                                <div className="absolute bottom-0 left-[20%] right-[20%] h-[2px] rounded-full bg-[#1ED760] opacity-50 group-hover:opacity-90 transition-opacity duration-200" />
                                <SpotifyMark size={22} />
                                Spotify로 계속하기
                                <Ic d={I.arrowR} size={16} color="#fff" sw={2.2} />
                            </button>
                        </div>

                        <div className="ms-fu mt-4 [animation-delay:0.34s]">
                            <button
                                type="button"
                                onClick={handleDemoLogin}
                                disabled={demoLoading}
                                className={[
                                    'group relative w-full flex items-center justify-center gap-3',
                                    'bg-white text-[#211C26] text-[16px] font-extrabold tracking-[-0.01em]',
                                    'px-7 py-[18px] rounded-[18px] border border-[#D7D0C3] overflow-hidden',
                                    'shadow-[0_4px_16px_rgba(33,28,38,0.07)]',
                                    'transition-all duration-[220ms] [transition-timing-function:cubic-bezier(0.34,1.56,0.64,1)]',
                                    demoLoading
                                        ? 'opacity-60 cursor-not-allowed'
                                        : 'cursor-pointer hover:-translate-y-[3px] hover:shadow-[0_20px_48px_-12px_rgba(33,28,38,0.18),0_0_0_1px_rgba(123,127,240,0.18)]',
                                ].join(' ')}
                            >
                                <div className="absolute inset-x-[18%] bottom-0 h-[2px] rounded-full bg-gradient-to-r from-[#FF6B5E] via-[#FFB648] to-[#7B7FF0] opacity-70 group-hover:opacity-100 transition-opacity duration-200" />
                                <Ic d={I.playCirc} size={22} color="#7B7FF0" sw={2} />
                                Demo로 시작하기
                                <Ic d={I.arrowR} size={16} color="#7B7FF0" sw={2.2} />
                            </button>
                        </div>

                        <div className="ms-fu mt-5 [animation-delay:0.4s]">
                            <div className="flex items-center justify-between gap-3 mb-3">
                                <p className="text-[12px] font-bold tracking-[0.12em] uppercase text-[#A39CAC]">
                                    데모 시나리오
                                </p>
                                <span className="text-[12px] text-[#A39CAC]">테스트하고 싶은 상황을 골라보세요</span>
                            </div>
                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                                {DEMO_PRESETS.map((preset) => {
                                    const active = selectedPreset.id === preset.id;
                                    return (
                                        <button
                                            key={preset.id}
                                            type="button"
                                            onClick={() => setSelectedPreset(preset)}
                                            className={[
                                                'text-left rounded-[18px] border px-4 py-4 transition-all duration-200',
                                                active
                                                    ? 'border-[#7B7FF0] bg-[#F2F3FF] shadow-[0_14px_30px_-18px_rgba(123,127,240,0.7)]'
                                                    : 'border-[#E5DFD3] bg-white hover:border-[#CFC7B7] hover:-translate-y-[1px]',
                                                preset.delayClass,
                                            ].join(' ')}
                                        >
                                            <div className="flex items-start justify-between gap-3 mb-3">
                                                <div>
                                                    <p className="text-[14px] font-extrabold text-[#211C26] mb-1">{preset.label}</p>
                                                    <p className="text-[12px] font-semibold text-[#7B7FF0]">{preset.badge}</p>
                                                </div>
                                                <div
                                                    className={`w-2.5 h-2.5 rounded-full mt-1.5 ${
                                                        active ? 'bg-[#7B7FF0]' : 'bg-[#E5DFD3]'
                                                    }`}
                                                />
                                            </div>
                                            <p className="text-[12.5px] leading-[1.6] text-[#6E6678] m-0">{preset.description}</p>
                                        </button>
                                    );
                                })}
                            </div>
                            <p className="text-[12px] leading-[1.6] text-[#A39CAC] mt-3">
                                선택한 시나리오는 데모 계정 생성과 추천 흐름에 반영돼요.
                            </p>
                        </div>


                        <div className="ms-fu flex flex-wrap gap-2 mt-5 [animation-delay:0.52s]">
                            {['프로필 읽기', '재생 제어', '목록 생성'].map((label) => (
                                <span
                                    key={label}
                                    className="inline-flex items-center gap-[5px] text-[12px] font-semibold text-[#A39CAC] bg-white border border-[#E5DFD3] rounded-full px-[11px] py-[5px]"
                                >
                                    <Ic d={I.check} size={10} color="#7B7FF0" sw={2.5} />
                                    {label}
                                </span>
                            ))}
                        </div>


                        <div className="ms-fu flex items-center gap-[10px] my-7 [animation-delay:0.58s]">
                            <div className="flex-1 h-px bg-[#E5DFD3]" />
                            <div className="flex items-center gap-[6px]">
                                <Ic d={I.lock} size={12} color="#A39CAC" sw={1.6} />
                                <span className="text-[12px] text-[#A39CAC] whitespace-nowrap">
                                    비밀번호를 직접 입력하지 않아요
                                </span>
                            </div>
                            <div className="flex-1 h-px bg-[#E5DFD3]" />
                        </div>


                        <div className="ms-fu flex items-center justify-between flex-wrap gap-3 [animation-delay:0.64s]">
                            <div className="flex items-center gap-[6px]">
                                <SpotifyMark size={14} />
                                <span className="text-[12px] text-[#A39CAC]">
                                    음악 데이터 제공&nbsp;<strong className="text-[#6E6678] font-bold">Spotify</strong>
                                </span>
                            </div>
                            <Link
                                to="/"
                                className="inline-flex items-center gap-[5px] text-[13px] font-semibold text-[#6E6678] no-underline hover:text-[#211C26] transition-colors duration-150"
                            >
                                <Ic d={I.arrowLeft} size={12} color="currentColor" />
                                서비스 소개 보기
                            </Link>
                        </div>
                    </div>
                </main>
            </div>
        </div>
    );
}
