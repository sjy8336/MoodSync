from app.rag.base import KnowledgeChunk


GENRE_CHUNKS: tuple[KnowledgeChunk, ...] = (
    KnowledgeChunk(
        id="genre-preservation",
        title="장르 보존 규칙",
        content="사용자가 특정 장르를 직접 말하면 무드보다 장르 정체성을 먼저 살린다. 장르가 없는 경우에만 감정과 작업 맥락을 더 강하게 반영한다.",
        keywords=("genre", "장르", "rnb", "jpop", "jazz", "rock", "punk"),
    ),
    KnowledgeChunk(
        id="korean-rnb",
        title="한국 R&B 해석",
        content="한국 감성 R&B는 지나치게 강한 후렴보다 여백, 미세한 그루브, 낮은 온도의 보컬 톤을 우선한다.",
        keywords=("rnb", "알앤비", "한국", "여백", "그루브", "보컬"),
    ),
    KnowledgeChunk(
        id="neo-soul",
        title="네오소울 해석",
        content="네오소울은 매끈한 그루브와 따뜻한 코드 진행, 여유 있는 보컬 질감이 중요하다.",
        keywords=("neo-soul", "네오소울", "soul", "groove", "warm"),
    ),
    KnowledgeChunk(
        id="funk-disco",
        title="펑키/디스코 해석",
        content="펑키와 디스코는 리듬의 탄력, 베이스 라인, 몸을 바로 움직이게 하는 드라이브감이 핵심이다.",
        keywords=("funk", "disco", "펑키", "디스코", "groove", "dance"),
    ),
    KnowledgeChunk(
        id="jpop-anime",
        title="제이팝/애니 OST 해석",
        content="제이팝이나 애니 OST는 멜로디 선명도와 장면 전환 같은 드라마틱한 전개가 핵심이다. 감정선이 빨리 열리고 분명하게 닫히는 곡이 잘 맞는다.",
        keywords=("jpop", "제이팝", "anime", "애니", "멜로디", "전개"),
    ),
    KnowledgeChunk(
        id="city-pop",
        title="시티팝 해석",
        content="시티팝은 세련된 도시감, 반짝이는 신스, 너무 무겁지 않은 드라이브가 잘 어울린다.",
        keywords=("city-pop", "시티팝", "retro", "synth", "city"),
    ),
    KnowledgeChunk(
        id="swing-jazz",
        title="스윙 재즈 해석",
        content="스윙 재즈는 빅밴드의 풍성한 편성, 탄력 있는 스윙 리듬, 밝고 즉흥적인 에너지가 핵심이다.",
        keywords=("swing", "big band", "스윙", "빅밴드", "jazz standard", "standard"),
    ),
    KnowledgeChunk(
        id="bebop-hardbop",
        title="비밥/하드밥 해석",
        content="비밥과 하드밥은 빠른 어법, 촘촘한 솔로 전개, 강한 연주 감각이 중요하다.",
        keywords=("bebop", "bop", "hard bop", "post-bop", "비밥", "하드밥"),
    ),
    KnowledgeChunk(
        id="cool-modal-jazz",
        title="쿨/모달 재즈 해석",
        content="쿨 재즈와 모달 재즈는 여백이 넓고 코드의 압박이 덜한, 차분하고 세련된 재즈 결을 살린다.",
        keywords=("cool jazz", "modal jazz", "쿨재즈", "모달재즈", "piano", "space"),
    ),
    KnowledgeChunk(
        id="jazz-fusion",
        title="퓨전 재즈 해석",
        content="퓨전 재즈는 전자 악기, 록과 펑크의 추진력, 재즈 즉흥의 자유도가 함께 살아 있어야 한다.",
        keywords=("jazz fusion", "fusion", "퓨전재즈", "weather report", "chick corea"),
    ),
    KnowledgeChunk(
        id="bossa-nova",
        title="보사노바 해석",
        content="보사노바는 부드러운 브라질 리듬, 건조하지 않은 어쿠스틱 질감, 과하지 않은 보컬이 어울린다.",
        keywords=("bossa nova", "bossanova", "보사노바", "latin", "acoustic"),
    ),
    KnowledgeChunk(
        id="synthwave",
        title="신스웨이브 해석",
        content="신스웨이브와 베이퍼웨이브는 복고적인 신스 질감과 밤공기 같은 넓은 공간감이 포인트다.",
        keywords=("synthwave", "vaporwave", "신스웨이브", "베이퍼웨이브", "retro"),
    ),
    KnowledgeChunk(
        id="opera",
        title="오페라 해석",
        content="오페라는 큰 호흡의 성악, 서사적인 전개, 극적인 고조가 핵심이다.",
        keywords=("opera", "오페라", "classical", "vocal"),
    ),
    KnowledgeChunk(
        id="latin-afro",
        title="라틴/아프로비트 해석",
        content="라틴과 아프로비트는 리듬의 추진력, 타악기 질감, 즉각적인 체온 상승이 중요하다.",
        keywords=("latin", "reggaeton", "afrobeats", "afrobeat", "라틴", "아프로비트"),
    ),
    KnowledgeChunk(
        id="folk-country",
        title="포크/컨트리 해석",
        content="포크와 컨트리는 담백한 서사, 어쿠스틱 톤, 자연스러운 호흡이 중심이다.",
        keywords=("folk", "country", "americana", "포크", "컨트리"),
    ),
    KnowledgeChunk(
        id="trip-hop",
        title="트립합 해석",
        content="트립합과 다운템포는 느린 박자 위에 묵직한 공기감과 밤의 무드를 쌓는 데 강하다.",
        keywords=("trip-hop", "downtempo", "트립합", "다운템포", "chill"),
    ),
    KnowledgeChunk(
        id="ambient-postrock",
        title="앰비언트/포스트록 해석",
        content="앰비언트와 포스트록은 장면이 천천히 열리고, 공간감과 여운이 길게 남는 편이 잘 맞는다.",
        keywords=("ambient", "post-rock", "앰비언트", "포스트록", "space"),
    ),
    KnowledgeChunk(
        id="metalcore",
        title="메탈코어 해석",
        content="메탈코어는 거친 리프와 폭발적인 에너지, 강한 전환이 필요할 때 잘 맞는다.",
        keywords=("metalcore", "메탈코어", "hardcore", "metal"),
    ),
    KnowledgeChunk(
        id="blues",
        title="블루스 해석",
        content="블루스는 감정을 직선적으로 드러내되, 리듬과 보컬의 느슨한 탄력이 있어야 한다.",
        keywords=("blues", "블루스", "soul", "guitar"),
    ),
    KnowledgeChunk(
        id="punk-rock-release",
        title="펑크락 해석",
        content="펑크락은 답답함을 해소하는 직진감이 중요하다. 리듬은 빠르고 기타는 거칠게, 보컬은 감정이 앞으로 튀는 곡을 우선한다.",
        keywords=("punk", "펑크", "rock", "기타", "직진감", "빠름"),
    ),
    KnowledgeChunk(
        id="favorite-diversity",
        title="좋아요 다양성 유지",
        content="좋아요한 아티스트와 결이 비슷하더라도 한 번에 같은 색만 몰아주지 말고, 비슷한 정서 안에서 지역, 장르, 시대가 조금 다른 곡을 섞는다.",
        keywords=("좋아요", "diversity", "아티스트", "비슷", "정서", "장르"),
    ),
)
