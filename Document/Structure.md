# 📁 프로젝트 구조 문서

## 1. 계층별 구조 (Layered Structure)
프로젝트의 파일 역할을 기준으로 한 계층 구조입니다.

```
📦 2025_sang2company/
├── 🖥️ Backend Layer
│   ├── backend/
│   │   ├── app.py              # Flask 메인 서버 (통합 API)
│   │   ├── simple_app.py       # 간소화된 Flask 서버
│   │   └── requirements.txt     # Python 의존성
│   ├── backend_module/         # 백엔드 모듈들
│   │   ├── 1_SP500DataLoad.py  # S&P 500 데이터 로드
│   │   ├── 2_SECEdgarData.py   # SEC 데이터 처리
│   │   ├── 3_Interpolation.py  # 데이터 보간
│   │   ├── 4_ComputeAlphas.py  # 알파 팩터 계산
│   │   └── 5_results.py        # 결과 분석
│   └── database/               # 데이터베이스 관련
│       ├── backtest_system.py  # 백테스트 시스템
│       ├── optimized_backtest.py # 최적화된 백테스트
│       └── simple_backtest.py  # 간단한 백테스트
│
├── 🧠 Alpha Core Layer
│   └── alphas/
│       ├── __init__.py        # 패키지 초기화, 공용 export
│       ├── base.py            # AlphaDataset, AlphaDefinition 등 기본 모델
│       ├── registry.py        # 공유/개인 알파 레지스트리
│       ├── store.py           # 파일 기반 알파 저장소 및 마이그레이션
│       ├── transpiler.py      # 수식 → 파이썬 함수 트랜스파일러
│       ├── providers/         # 공용 알파 공급자(WorldQuant 101 등)
│       └── bootstrap.py       # 레지스트리 초기화 엔트리포인트
│
├── 🎨 Frontend Layer
│   └── frontend/
│       ├── src/
│       │   ├── App.tsx             # 메인 앱 컴포넌트
│       │   ├── App.css             # 글로벌 스타일
│       │   ├── index.tsx           # 엔트리 포인트
│       │   ├── components/         # 컴포넌트
│       │   │   ├── common/         # 공통 컴포넌트
│       │   │   │   ├── GlassCard.tsx      # 글래스 카드
│       │   │   │   ├── GlassButton.tsx    # 글래스 버튼
│       │   │   │   ├── GlassInput.tsx     # 글래스 입력
│       │   │   │   └── LiquidBackground.tsx # 리퀴드 배경
│       │   │   ├── Layout/         # 레이아웃
│       │   │   │   ├── Layout.tsx         # 메인 레이아웃
│       │   │   │   └── Navigation.tsx     # 네비게이션
│       │   │   └── Auth/           # 인증
│       │   │       └── Auth.tsx           # 로그인
│       │   ├── pages/             # 페이지
│       │   │   ├── Dashboard.tsx          # 대시보드 (자산/알파/보유주식 탭)
│       │   │   ├── Backtest.tsx           # 백테스트
│       │   │   ├── Portfolio.tsx          # 포트폴리오
│       │   │   ├── AlphaPool.tsx          # 알파 풀 (GA)
│       │   │   ├── AlphaIncubator.tsx     # 알파 부화장 (AI)
│       │   │   └── Simulation.tsx         # 모의투자
│       │   ├── contexts/          # React 컨텍스트
│       │   │   └── AuthContext.tsx        # 인증 컨텍스트
│       │   ├── services/          # API 서비스
│       │   │   └── api.ts                 # API 클라이언트
│       │   ├── styles/            # 스타일
│       │   │   ├── theme.ts               # 테마 정의
│       │   │   └── animations.ts          # 애니메이션
│       │   └── types/             # 타입 정의
│       │       └── index.ts               # 공통 타입
│       └── package.json           # 의존성 관리
│
├── 🤖 AI Layer
│   └── Langchain/
│       ├── Langchain.py        # 멀티 에이전트 시스템
│       ├── simple_agent.py     # 간단한 에이전트
│       └── start_system.py     # 시스템 시작
│
├── 🧬 Algorithm Layer
│   └── GA_algorithm/
│       ├── autoalpha_ga.py    # 자동 알파 GA
│       ├── run_ga.py          # GA 실행
│       └── test_ga_with_real_data.py # 실제 데이터 테스트
│
└── 📊 Data Layer
    ├── database/              # 데이터베이스 파일들
    ├── parquet_cache/         # Parquet 캐시
    └── calculated_alphas/     # 계산된 알파들
```

## 2. 기능별 구조 (Feature-Sliced Design)
기능, 페이지, 레이어 단위로 구성된 구조입니다.

### 🎯 핵심 기능별 구조

#### 📊 데이터 관리 (Data Management)
- **데이터 수집**: `backend_module/1_SP500DataLoad.py`, `2_SECEdgarData.py`
- **데이터 처리**: `backend_module/3_Interpolation.py`
- **데이터 저장**: `database/` 폴더의 CSV 파일들

#### 🧬 알파 팩터 생성 (Alpha Generation)
- **수동 알파**: `backend_module/4_ComputeAlphas.py`
- **알파 레지스트리/스토어**: `alphas/` 패키지 (WorldQuant 101 + 사용자 정의)
- **AI 알파**: `Langchain/Langchain.py` (멀티 에이전트)
- **진화 알고리즘**: `GA_algorithm/autoalpha_ga.py`

#### 📈 백테스트 (Backtesting)
- **백테스트 시스템**: `database/backtest_system.py`
- **최적화 백테스트**: `database/optimized_backtest.py`
- **간단 백테스트**: `database/simple_backtest.py`
- **체결 시점 모델**: 신호 계산일(t)의 데이터를 사용해 t+1 거래일 시가에 진입하고, 다음 리밸런싱 시점 시가(Open-to-Open)에서 청산하여 동시성 오류를 방지.

#### 💼 포트폴리오 관리 (Portfolio Management)
- **포트폴리오 구성**: `frontend/src/pages/Portfolio.tsx`
- **실제 데이터 연동**: `/api/csv/user/portfolio`, `/api/csv/user/investment`, `/api/csv/user/transactions`
- **성과 분석**: 백엔드 API 통합

#### 📊 대시보드 자산 분석 (Dashboard Asset Insight)
- **내 자산 한눈에 보기**: 다중 종목을 선택해 기간별 누적 수익률을 비교하는 차트와 종목별 핵심 지표(CAGR, Sharpe, Sortino, MDD, Win Rate, Volatility)를 제공.
- **설정 패널**: 우측 세로 패널에서 기간(기본값 `2000-01-01 ~ latest`)을 지정하고 `/api/data/ticker-list`로 종목을 검색·다중 선택한 뒤 `/api/data/ticker-performance` 호출로 분석 실행.
- **시각화**: 좌측 GlassCard 영역에 Recharts 기반 멀티 라인 차트를 배치하고, 범례/라인 클릭 시 해당 종목만 강조되며 툴팁은 날짜·종목·수익률·색상을 동시에 노출.

#### 🤖 AI 에이전트 (AI Agents)
- **멀티 에이전트**: `Langchain/Langchain.py`
- **대화형 인터페이스**: `frontend/src/pages/AlphaIncubator.tsx`

### 🔄 워크플로우별 구조

#### 데이터 파이프라인
```
데이터 수집 → 보간 → 알파 계산 → 백테스트 → 결과 저장
```

#### AI 워크플로우
```
사용자 질문 → Coordinator → 전문 에이전트 → 결과 통합 → 답변
```

#### 백테스트 워크플로우
```
알파 선택 → 파라미터 설정 → 백테스트 실행 → 결과 분석 → 시각화
```

## 3. 리팩토링 우선 조치
- **문서 일관성**: Design.md, Request.md의 규칙을 기준으로 모든 페이지 텍스트를 한글 표준으로 정리.
- **데이터 연동 점검**: Portfolio, Dashboard, MyInvestment 페이지는 CSV 기반 API 응답을 사용하도록 통일.
- **사이드바 튜닝**: 축소 모드에서 아이콘 간격을 4px 이하로 조정하고 로고는 흰색 원형 아이콘을 유지.
