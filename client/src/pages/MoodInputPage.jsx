import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { recommendMood } from '../services/apiClient';
import Header from '../components/Header';
import Footer from '../components/Footer';

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
        className={`inline-block flex-shrink-0 align-middle ${className}`}
    >
        {(Array.isArray(d) ? d : [d]).map((p, i) => (
            <path key={i} d={p} />
        ))}
    </svg>
);

const I = {
    arrowL: 'M19 12H5M12 5l-7 7 7 7',
    arrowR: 'M5 12h14M12 5l7 7-7 7',
    music: 'M9 18V5l12-2v13M9 18a3 3 0 1 1-6 0 3 3 0 0 1 6 0zm12-2a3 3 0 1 1-6 0 3 3 0 0 1 6 0z',
    sparkles:
        'M9.937 15.5A2 2 0 0 0 8.5 14.063l-6.135-1.582a.5.5 0 0 1 0-.962L8.5 9.936A2 2 0 0 0 9.937 8.5l1.582-6.135a.5.5 0 0 1 .963 0L14.063 8.5A2 2 0 0 0 15.5 9.937l6.135 1.581a.5.5 0 0 1 0 .964L15.5 14.063a2 2 0 0 0-1.437 1.437l-1.582 6.135a.5.5 0 0 1-.963 0z',
    check: 'M20 6 9 17l-5-5',
    alert: [
        'M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z',
        'M12 9v4M12 17h.01',
    ],
    shield: ['M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z', 'M9 12l2 2 4-4'],
    pen: 'M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z',
    smile: [
        'M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10z',
        'M8 14s1.5 2 4 2 4-2 4-2',
        'M9 9h.01M15 9h.01',
    ],
    frown: [
        'M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10z',
        'M16 16s-1.5-2-4-2-4 2-4 2',
        'M9 9h.01M15 9h.01',
    ],
    cloud: 'M17.5 19H9a7 7 0 1 1 6.71-9h1.79a4.5 4.5 0 1 1 0 9z',
    zap: 'M13 2 3 14h9l-1 8 10-12h-9l1-8z',
    meh: ['M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10z', 'M8 15h8', 'M9 9h.01M15 9h.01'],
    alertC: ['M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10z', 'M12 8v4M12 16h.01'],
    waves: 'M2 6c.6.5 1.2 1 2.5 1C7 7 7 5 9.5 5c2.6 0 2.4 2 5 2 2.5 0 2.5-2 5-2 1.3 0 1.9.5 2.5 1M2 12c.6.5 1.2 1 2.5 1 2.5 0 2.5-2 5-2 2.6 0 2.4 2 5 2 2.5 0 2.5-2 5-2 1.3 0 1.9.5 2.5 1M2 18c.6.5 1.2 1 2.5 1 2.5 0 2.5-2 5-2 2.6 0 2.4 2 5 2 2.5 0 2.5-2 5-2 1.3 0 1.9.5 2.5 1',
    sun: [
        'M12 17a5 5 0 1 0 0-10 5 5 0 0 0 0 10z',
        'M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42',
    ],
    moon: 'M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z',
    guitar: [
        'M19.59 3.59a2 2 0 0 0-2.83 0l-3.89 3.88a2 2 0 0 0 0 2.83l.16.15-2.38 2.38-.16-.16a2 2 0 0 0-2.83 0l-3.89 3.89a2 2 0 0 0 0 2.83l1.42 1.41a2 2 0 0 0 2.83 0l3.89-3.88a2 2 0 0 0 0-2.83l-.16-.15 2.38-2.38.16.16a2 2 0 0 0 2.83 0l3.88-3.89a2 2 0 0 0 0-2.83z',
    ],
    flame: 'M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 0 0 2.5 2.5z',
    target: [
        'M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10z',
        'M12 18a6 6 0 1 0 0-12 6 6 0 0 0 0 12z',
        'M12 14a2 2 0 1 0 0-4 2 2 0 0 0 0 4z',
    ],
    shuffle: ['M16 3h5v5', 'M4 20 21 3', 'M21 16v5h-5', 'M15 15l6 6', 'M4 4l5 5'],
    heart: 'M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z',
    coffee: 'M18 8h1a4 4 0 0 1 0 8h-1M2 8h16v9a4 4 0 0 1-4 4H6a4 4 0 0 1-4-4V8zM6 1v3M10 1v3M14 1v3',
    rain: ['M20 16.2A4.5 4.5 0 0 0 17.5 8H16.74A7 7 0 1 0 7 17.97', 'M16 20v2M8 20v2M12 20v2'],
    star: 'M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z',
    wind: 'M9.59 4.59A2 2 0 1 1 11 8H2m10.59 11.41A2 2 0 1 0 14 16H2m15.73-8.27A2.5 2.5 0 1 1 19.5 12H2',
    droplets: [
        'M7 16.3c2.2 0 4-1.83 4-4.05 0-1.16-.57-2.26-1.71-3.19S7.29 6.75 7 5.3c-.29 1.45-1.14 2.84-2.29 3.76S3 11.1 3 12.25c0 2.22 1.8 4.05 4 4.05z',
        'M12.56 6.6A10.97 10.97 0 0 0 14 3.02c.5 2.5 2 4.9 4 6.5s3 3.5 3 5.5a6.98 6.98 0 0 1-11.91 4.97',
    ],
    sofa: [
        'M20 9V6a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v3',
        'M2 11v5a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-5a2 2 0 0 0-4 0v2H6v-2a2 2 0 0 0-4 0z',
        'M4 18v2M20 18v2M12 4v9',
    ],
    activity: 'M22 12h-4l-3 9L9 3l-3 9H2',
};

/*
  ── 감정 옵션
  미선택: bg-[#F1ECE3] + text-[#6E6678] (색상 통일, 정돈된 느낌)
  선택:   bg-[#7B7FF0] + white 텍스트 (Lavender 강조 — 검정보다 시선을 덜 끌면서도 뚜렷한 선택 표시)
*/
const MOOD_OPTIONS = [
    { value: 'happy', label: '기쁨', icon: I.smile },
    { value: 'excited', label: '설렘', icon: I.star },
    { value: 'sad', label: '우울', icon: I.rain },
    { value: 'lonely', label: '외로움', icon: I.droplets },
    { value: 'tired', label: '피로', icon: I.sofa },
    { value: 'angry', label: '분노', icon: I.flame },
    { value: 'anxious', label: '불안', icon: I.alertC },
    { value: 'focused', label: '집중', icon: I.target },
];

const VIBE_OPTIONS = [
    { value: '잔잔한', icon: I.waves },
    { value: '신나는', icon: I.zap },
    { value: '따뜻한', icon: I.sun },
    { value: '몽환적인', icon: I.moon },
    { value: '감성적인', icon: I.heart },
    { value: '강렬한', icon: I.flame },
    { value: '차분한', icon: I.cloud },
    { value: '위로되는', icon: I.droplets },
    { value: '기분 전환되는', icon: I.shuffle },
    { value: '몰입되는', icon: I.target },
];

export default function MoodInputPage() {
    const [text, setText] = useState('');
    const [mood, setMood] = useState('');
    const [vibes, setVibes] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [isMobile, setIsMobile] = useState(false);
    const navigate = useNavigate();

    useEffect(() => {
        const check = () => setIsMobile(window.innerWidth < 560);
        check();
        window.addEventListener('resize', check);
        return () => window.removeEventListener('resize', check);
    }, []);

    const toggleVibe = (v) => setVibes((p) => (p.includes(v) ? p.filter((x) => x !== v) : [...p, v]));

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!mood) return;
        setLoading(true);
        setError('');
        try {
            const vibeText = vibes.length > 0 ? ` 원하는 분위기: ${vibes.join(', ')}.` : '';
            const combined = (text.trim() + vibeText).trim();
            const payload = { ...(combined && { text: combined }), ...(mood && { mood }) };
            const result = await recommendMood(payload);
            navigate('/recommendations', { state: { result, payload } });
        } catch (err) {
            setLoading(false);
            setError(err.message || '추천 요청 중 오류가 발생했습니다.');
        }
    };

    const canSubmit = !!mood;
    const selectedMood = MOOD_OPTIONS.find((m) => m.value === mood);
    const step2Active = mood;
    const step2Done = (text.trim() || vibes.length > 0) && mood;

    return (
        <>
            <div className="ms-page-shell">
                {/* ── 배경 orbs ── */}
                <div aria-hidden="true" className="fixed inset-0 pointer-events-none z-0 overflow-hidden">
                    <div
                        className="absolute -right-[8%] -top-[10%] h-[360px] w-[360px] rounded-full [animation:orb1_12s_ease-in-out_infinite] bg-[radial-gradient(circle,rgba(255,107,94,0.10)_0%,transparent_70%)]"
                    />
                    <div
                        className="absolute -left-[8%] bottom-[10%] h-[320px] w-[320px] rounded-full [animation:orb2_15s_ease-in-out_infinite] bg-[radial-gradient(circle,rgba(123,127,240,0.09)_0%,transparent_70%)]"
                    />
                </div>

                <Header />

                {/* ── MAIN ── */}
                <main className={`ms-page-main ${isMobile ? 'ms-page-main-mobile' : 'ms-page-main-desktop'}`}>
                    <form onSubmit={handleSubmit} noValidate className="w-full">
                        {/* 헤더 */}
                        <div className="text-center mb-11 opacity-0 [animation:ms-fadeUp_0.6s_ease_forwards] [animation-delay:0.05s]">
                            <span className="inline-flex items-center gap-1.5 text-[11px] font-bold tracking-[0.07em] uppercase bg-[#FFEAE6] text-[#9C3D33] px-3.5 py-1.5 rounded-full mb-5">
                                <Ic d={I.sparkles} size={12} color="#FF6B5E" sw={1.6} /> 감정 기반 음악 추천
                            </span>
                            <h1 className="text-[clamp(26px,4.5vw,42px)] font-extrabold tracking-[-0.035em] leading-[1.2] text-[#211C26] mb-3">
                                지금 기분이 어때요?
                            </h1>
                            <p className="text-[16.5px] text-[#6E6678] leading-[1.7]">
                                감정을 고르면 그 순간에 맞는 음악을 찾아드려요.
                            </p>
                        </div>

                        <div className="flex flex-col gap-4">
                            {/* ══ STEP 1 · 감정 선택 ══ */}
                            <div className="opacity-0 [animation:ms-fadeUp_0.6s_ease_forwards] [animation-delay:0.1s] bg-white rounded-3xl border border-[#E5DFD3] overflow-hidden shadow-[0_4px_24px_-8px_rgba(33,28,38,0.07)]">
                                <div className="px-6 pt-5 pb-4 border-b border-[#F1ECE3] flex items-center justify-between">
                                    <div className="flex items-center gap-2.5">
                                        <div
                                            className={`w-[22px] h-[22px] rounded-full flex items-center justify-center text-[10px] font-extrabold text-white flex-shrink-0 transition-all duration-300 ${
                                                mood ? 'bg-[#7B7FF0]' : 'bg-[#FF6B5E]'
                                            }`}
                                        >
                                            {mood ? <Ic d={I.check} size={11} color="#fff" sw={2.4} /> : '1'}
                                        </div>
                                        <span className="text-[15px] font-bold text-[#211C26] tracking-[-0.01em]">
                                            지금 감정을 골라주세요
                                        </span>
                                    </div>
                                    <span className="text-[11px] font-bold text-[#9C3D33] bg-[#FFEAE6] px-2.5 py-1 rounded-full">
                                        필수
                                    </span>
                                </div>

                                {/* 감정 pill 그리드 */}
                                <div className="px-6 py-5 flex flex-wrap gap-2">
                                    {MOOD_OPTIONS.map((m) => {
                                        const active = mood === m.value;
                                        return (
                                            <button
                                                key={m.value}
                                                type="button"
                                                onClick={() => setMood(active ? '' : m.value)}
                                                className={`inline-flex items-center gap-[7px] px-[18px] py-2.5 rounded-full text-sm font-bold font-inherit transition-all duration-200 border-[1.5px] ${
                                                    active
                                                        ? 'bg-[#7B7FF0] border-[#7B7FF0] text-white shadow-[0_4px_16px_rgba(123,127,240,0.35)] -translate-y-px'
                                                        : 'bg-white border-[#E5DFD3] text-[#6E6678] hover:bg-[#F1ECE3] hover:border-[#D6CFC1] hover:text-[#211C26]'
                                                }`}
                                            >
                                                <Ic d={m.icon} size={14} color={active ? '#fff' : '#A39CAC'} sw={1.8} />
                                                {m.label}
                                            </button>
                                        );
                                    })}
                                </div>
                            </div>

                            {/* ══ STEP 2 · 텍스트 + 분위기 ══ */}
                            <div
                                className={`opacity-0 [animation:ms-fadeUp_0.6s_ease_forwards] [animation-delay:0.16s] bg-white rounded-3xl border border-[#E5DFD3] overflow-hidden shadow-[0_4px_24px_-8px_rgba(33,28,38,0.07)] transition-opacity duration-300 ${
                                    step2Active ? 'opacity-100 pointer-events-auto' : 'opacity-45 pointer-events-none'
                                }`}
                            >
                                <div className="px-6 pt-5 pb-4 border-b border-[#F1ECE3] flex items-center justify-between">
                                    <div className="flex items-center gap-2.5">
                                        <div
                                            className={`w-[22px] h-[22px] rounded-full flex items-center justify-center text-[10px] font-extrabold text-white flex-shrink-0 transition-all duration-300 ${
                                                step2Done ? 'bg-[#7B7FF0]' : 'bg-[#A39CAC]'
                                            }`}
                                        >
                                            {step2Done ? <Ic d={I.check} size={11} color="#fff" sw={2.4} /> : '2'}
                                        </div>
                                        <span className="text-[15px] font-bold text-[#211C26] tracking-[-0.01em]">
                                            오늘 어떤 하루였나요?
                                        </span>
                                    </div>
                                    <span className="text-[11px] font-semibold text-[#A39CAC] bg-[#F1ECE3] px-2.5 py-1 rounded-full">
                                        선택
                                    </span>
                                </div>

                                <div className="px-6 py-5 flex flex-col gap-5">
                                    {/* 텍스트 입력 */}
                                    <div>
                                        <label className="block text-[12.5px] font-semibold text-[#6E6678] mb-2.5">
                                            지금 기분을 자유롭게 적어주세요
                                        </label>
                                        <div className="relative rounded-2xl bg-[#FAF8F4] border-[1.5px] border-[#E5DFD3] transition-all duration-200 focus-within:border-[#7B7FF0] focus-within:shadow-[0_0_0_3px_#ECEDFD]">
                                            <div className="absolute top-3.5 left-3.5 pointer-events-none">
                                                <Ic d={I.pen} size={14} color="#A39CAC" />
                                            </div>
                                            <textarea
                                                value={text}
                                                onChange={(e) => setText(e.target.value.slice(0, 200))}
                                                rows={3}
                                                placeholder="오늘 좀 지치고 조용한 노래가 듣고 싶어요..."
                                                className="w-full resize-none bg-transparent text-sm leading-[1.7] text-[#211C26] pl-10 pr-4 pt-3 pb-2 rounded-2xl border-none font-inherit outline-none"
                                            />
                                            <div className="flex justify-end px-3.5 pb-2.5">
                                                <span
                                                    className={`text-[11px] ${text.length > 180 ? 'text-[#FF6B5E]' : 'text-[#A39CAC]'}`}
                                                >
                                                    {text.length}/200
                                                </span>
                                            </div>
                                        </div>
                                        <p className="text-[11.5px] text-[#A39CAC] mt-[7px]">
                                            자세할수록 추천 정확도가 높아져요
                                        </p>
                                    </div>

                                    {/* 분위기 선택 */}
                                    <div>
                                        <p className="text-[12.5px] font-semibold text-[#6E6678] mb-2.5">
                                            원하는 분위기
                                            <span className="font-normal text-[#A39CAC] ml-1.5">복수 선택 가능</span>
                                        </p>
                                        <div className="flex flex-wrap gap-[7px]">
                                            {VIBE_OPTIONS.map((v) => {
                                                const active = vibes.includes(v.value);
                                                return (
                                                    <button
                                                        key={v.value}
                                                        type="button"
                                                        onClick={() => toggleVibe(v.value)}
                                                        className={`inline-flex items-center gap-1.5 px-[13px] py-[7px] rounded-full text-[13px] font-semibold font-inherit transition-all duration-[180ms] border-[1.5px] ${
                                                            active
                                                                ? 'bg-[#7B7FF0] border-[#7B7FF0] text-white shadow-[0_4px_14px_rgba(123,127,240,0.28)] -translate-y-px'
                                                                : 'bg-[#FAF8F4] border-[#E5DFD3] text-[#6E6678] hover:bg-[#F1ECE3] hover:border-[#D6CFC1]'
                                                        }`}
                                                    >
                                                        <Ic
                                                            d={v.icon}
                                                            size={12}
                                                            color={active ? '#fff' : '#A39CAC'}
                                                            sw={1.8}
                                                        />
                                                        {v.value}
                                                    </button>
                                                );
                                            })}
                                        </div>
                                    </div>
                                </div>
                            </div>

                            {/* ══ STEP 3 · 추천받기 ══ */}
                            <div
                                className={`opacity-0 [animation:ms-fadeUp_0.6s_ease_forwards] [animation-delay:0.22s] rounded-3xl overflow-hidden border transition-all duration-[400ms] ${
                                    mood
                                        ? 'border-[#D6CFC1] bg-gradient-to-br from-[#FFEAE6] to-[#ECEDFD]'
                                        : 'border-[#E5DFD3] bg-[#F1ECE3]'
                                }`}
                            >
                                <div className="p-6">
                                    {/* 선택 요약 */}
                                    {(mood || vibes.length > 0) && (
                                        <div className="flex flex-wrap gap-[7px] mb-[18px]">
                                            {selectedMood && (
                                                <span className="inline-flex items-center gap-1.5 text-[12.5px] font-bold px-[13px] py-1.5 rounded-full bg-[#7B7FF0] text-white">
                                                    <Ic d={selectedMood.icon} size={12} color="#fff" sw={1.8} />{' '}
                                                    {selectedMood.label}
                                                </span>
                                            )}
                                            {vibes.map((v) => (
                                                <span
                                                    key={v}
                                                    className="inline-flex items-center gap-[5px] text-xs font-semibold px-3 py-1.5 rounded-full bg-white/80 text-[#6E6678] border border-[#E5DFD3]"
                                                >
                                                    <Ic
                                                        d={VIBE_OPTIONS.find((o) => o.value === v)?.icon || I.music}
                                                        size={11}
                                                        color="#A39CAC"
                                                    />
                                                    {v}
                                                </span>
                                            ))}
                                        </div>
                                    )}

                                    {/* 제출 버튼 */}
                                    <button
                                        type="submit"
                                        disabled={!canSubmit || loading}
                                        className={`w-full flex items-center justify-center gap-2.5 font-extrabold rounded-[18px] text-base px-7 py-[18px] border-none font-inherit tracking-[-0.01em] transition-all duration-200 relative overflow-hidden ${
                                            canSubmit
                                                ? 'bg-[#211C26] text-white cursor-pointer'
                                                : 'bg-[#D6CFC1] text-[#A39CAC] cursor-not-allowed'
                                        } ${
                                            canSubmit && !loading
                                                ? 'shadow-[0_8px_28px_-8px_rgba(33,28,38,0.35)] hover:-translate-y-0.5 hover:shadow-[0_14px_36px_-8px_rgba(33,28,38,0.45)]'
                                                : ''
                                        }`}
                                    >
                                        {loading ? (
                                            <>
                                                {/* SVG 원형 스피너 */}
                                                <svg
                                                    width="20"
                                                    height="20"
                                                    viewBox="0 0 20 20"
                                                    className="flex-shrink-0 animate-spin [animation-duration:0.85s]"
                                                >
                                                    <circle
                                                        cx="10"
                                                        cy="10"
                                                        r="7.5"
                                                        fill="none"
                                                        stroke="rgba(255,255,255,0.25)"
                                                        strokeWidth="2.2"
                                                    />
                                                    <path
                                                        d="M10 2.5 A7.5 7.5 0 0 1 17.5 10"
                                                        fill="none"
                                                        stroke="#fff"
                                                        strokeWidth="2.2"
                                                        strokeLinecap="round"
                                                    />
                                                </svg>
                                                음악을 찾고 있어요
                                            </>
                                        ) : (
                                            <>
                                                <Ic d={I.music} size={18} color={canSubmit ? '#fff' : '#A39CAC'} />
                                                음악 추천받기
                                                <Ic
                                                    d={I.arrowR}
                                                    size={16}
                                                    color={canSubmit ? '#fff' : '#A39CAC'}
                                                    sw={2}
                                                />
                                            </>
                                        )}
                                    </button>

                                    {!mood && (
                                        <p className="text-center text-[12.5px] text-[#A39CAC] mt-3">
                                            위에서 지금 감정을 먼저 선택해주세요
                                        </p>
                                    )}

                                    {error && (
                                        <div className="flex items-start gap-2.5 mt-3.5 px-4 py-3.5 rounded-2xl bg-[#FFEAE6] border border-[#FF6B5E]/30">
                                            <Ic
                                                d={I.alert}
                                                size={15}
                                                color="#FF6B5E"
                                                className="mt-0.5 flex-shrink-0"
                                            />
                                            <p className="text-[13px] leading-[1.6] m-0 text-[#9C3D33]">{error}</p>
                                        </div>
                                    )}
                                </div>
                            </div>
                        </div>
                    </form>
                </main>

                <Footer isMobile={isMobile} />
            </div>
        </>
    );
}
