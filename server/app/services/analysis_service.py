from app.services.gemini_service import GeminiServiceError, analyze_mood_with_gemini


def analyze_mood_from_text(text: str) -> str:
    try:
        gemini_mood = analyze_mood_with_gemini(text)
        if gemini_mood:
            return gemini_mood
    except GeminiServiceError:
        pass

    lowered = text.lower()
    if any(word in lowered for word in ["happy", "great", "joy", "glad", "신나", "기쁘", "설렘", "들뜸"]):
        return "happy"
    if any(word in lowered for word in ["sad", "depressed", "down", "우울", "힘들", "슬프", "처지", "서럽"]):
        return "sad"
    if any(word in lowered for word in ["focus", "study", "work", "집중", "공부", "작업", "몰입", "버티", "과제"]):
        return "focused"
    if any(word in lowered for word in ["anxious", "불안", "걱정", "긴장", "초조", "떨려", "스트레스"]):
        return "anxious"
    if any(word in lowered for word in ["lonely", "alone", "외로", "혼자", "쓸쓸", "고독"]):
        return "lonely"
    if any(word in lowered for word in ["angry", "mad", "화나", "짜증", "열받", "분노", "빡침"]):
        return "angry"
    if any(word in lowered for word in ["tired", "sleepy", "피곤", "지침", "무기력", "번아웃"]):
        return "tired"
    if any(word in lowered for word in ["calm", "chill", "relax", "잔잔", "차분", "평온", "편안"]):
        return "calm"
    if any(word in lowered for word in ["nostalgia", "nostalgic", "그리워", "추억", "회상"]):
        return "calm"
    return "calm"
