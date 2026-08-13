from app.rag.base import KnowledgeChunk


MOOD_CHUNKS: tuple[KnowledgeChunk, ...] = (
    KnowledgeChunk(
        id="mood-history",
        title="최근 감정 기록 활용",
        content="최근 감정 기록이 같은 방향으로 반복되면 같은 무드만 강화하지 말고, 강도는 유지하되 질감이나 템포를 약간 달리해 추천한다.",
        keywords=("recent", "history", "mood", "감정", "기록", "반복", "흐름"),
    ),
    KnowledgeChunk(
        id="mood-variation",
        title="무드 변주 규칙",
        content="같은 무드가 반복되어도 곡마다 에너지와 질감은 조금씩 달라야 한다. 첫 곡은 현재 감정에 맞추고, 다음 곡은 보완하거나 확장하는 역할을 둔다.",
        keywords=("variation", "무드", "반복", "에너지", "질감"),
    ),
    KnowledgeChunk(
        id="vibe-to-sound",
        title="감정-사운드 매핑",
        content="잔잔함은 얇고 부드러운 질감, 몽환은 넓은 공간감, 몰입은 일정한 리듬과 낮은 변동성, 위로는 따뜻한 보컬과 완만한 전개에 가깝다.",
        keywords=("잔잔", "몽환", "몰입", "위로", "질감", "공간감", "리듬"),
    ),
    KnowledgeChunk(
        id="comfort-mode",
        title="위로 모드 추천",
        content="외로움, 슬픔, 피곤함이 보이면 감정을 너무 끌어올리지 않고 따뜻한 질감과 부드러운 전개를 우선한다.",
        keywords=("sad", "lonely", "tired", "외로움", "슬픔", "피곤", "위로"),
    ),
    KnowledgeChunk(
        id="energy-mode",
        title="에너지 모드 추천",
        content="기쁨, 설렘, 신남이 있으면 밝은 발렌스와 선명한 리듬을 우선하고, 사용자가 너무 산만해지지 않게 곡 간 대비를 조절한다.",
        keywords=("happy", "excited", "신남", "기쁨", "설렘", "에너지"),
    ),
    KnowledgeChunk(
        id="focus-flow",
        title="집중 흐름 최적화",
        content="집중용 추천은 처음부터 끝까지 강하게 밀기보다 일정한 텐션을 유지하고, 산만한 전환이나 과한 브레이크를 피한다.",
        keywords=("집중", "focus", "흐름", "텐션", "산만", "전환"),
    ),
    KnowledgeChunk(
        id="comfort-breathing",
        title="위로와 호흡",
        content="위로가 필요한 순간엔 너무 밝게 뒤집기보다 숨을 고르게 해주는 호흡과 부드러운 회복감을 남긴다.",
        keywords=("위로", "호흡", "회복", "부드러운", "calm"),
    ),
)

