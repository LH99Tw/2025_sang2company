[0](20251014):LAW.md 및 도큐먼트 작성
    - 개발 문서에 대한 문서를 작성했습니다.

[1](20250925):백테스트 시스템 일관성 문제 해결
    - 백테스트 API에서 랜덤 더미 데이터 생성 문제 발견 및 해결
    - 포트폴리오 API와 백테스트 API 모두 실제 데이터 기반으로 통일
    - 일관된 백테스트 결과 보장

[2](20250114):데이터 구조 문서화 시스템 구축
    - DataStructure.md 파일 생성: 자주 사용하는 데이터 파일의 head(5) 샘플 기록
    - 주요 데이터 파일 5개 (sp500_data.csv, sp500_interpolated.csv, sp500_with_alphas.csv, enhanced_backtest_metrics.csv, factor_returns_alpha001.csv) 구조 문서화
    - 데이터 플로우와 파일 분류 체계 구축
    - LAW.md에 데이터 구조 기록 규칙 추가 (5-1~5-4)

[3](20250114):메뉴 구조 개편 및 새로운 페이지 구현
    - 왼쪽 메뉴바 구조 변경: 데이터탐색 제거, 새로운 메뉴 추가
    - 새로운 메뉴: 모의투자, 알파 Pool (기존 GA 진화알고리즘), 알파 부화장 (기존 AI 에이전트)
    - 미구현 기능용 빈 페이지 3개 생성 (Simulation.tsx, AlphaPool.tsx, AlphaIncubator.tsx)
    - 기존 GAEvolution.tsx와 AIAgent.tsx를 새로운 구조로 업데이트
    - App.tsx 라우팅 구조 업데이트 및 불필요한 파일 정리

[4](20250114):디자인 시스템 가이드라인 구축
    - Design.md 파일을 체계적인 디자인 시스템 가이드로 확장
    - 컬러 팔레트, 타이포그래피, 애니메이션 시스템 정의
    - Glass Morphism과 Liquid Flow 디자인 컨셉 구체화
    - 접근성(WCAG 2.1 AA) 및 성능 최적화 가이드라인 추가
    - LAW.md에 디자인 시스템 규칙 추가 (6-1~6-5)
    - 레퍼런스 이미지 및 컴포넌트 라이브러리 정리

[5](20251014):프론트엔드 전면 재설계 및 디자인 시스템 적용

[6](20251014):Chrome Dark + Liquid Glass UI 완성 및 노드 기반 인터페이스 구현
    
    ### 디자인 시스템 완성
    - Chrome Dark Mode 색상 팔레트 (#202124, #292A2D, #3C4043) 적용
    - Liquid Glass 효과: 투명도, backdrop-filter, 그라데이션 테두리
    - Threads.com 스타일 레이아웃: 중앙 정렬 (max-width: 1400px)
    - 사이드바 토글 기능 (280px ↔ 80px), smooth cubic-bezier 애니메이션
    - 메뉴 영어화: Dashboard, Backtest, Portfolio, Alpha Pool, Incubator, Paper Trading
    - 페이지 아이콘: 흰색 원형 SVG
    
    ### 노드 기반 UI 구현 (ReactFlow)
    - **AlphaPool**: GA 진화 프로세스 시각화
      * 데이터 소스 → GA 엔진 → 알파 세대 → 최적 알파 선택
      * 실시간 노드 연결, 애니메이션, 진화 상태 표시
    - **AlphaIncubator**: AI 에이전트 워크플로우
      * Coordinator → Data Analyst/Alpha Researcher/Portfolio Manager → 응답
      * 채팅 인터페이스 + 노드 기반 워크플로우 동시 표시
      * 다중 에이전트 협업 시각화
    
    ### 백엔드 API 연동
    - Health Check: `/api/health`
    - Backtest: `/api/backtest` (POST)
    - GA Evolution: `/api/ga/run` (POST)
    - AI Chat: `/api/chat` (POST, 키워드 기반 응답)
    - 로딩 상태 처리, 오프라인 모드 대응
    - API_ENDPOINTS.md 문서 생성
    
    ### 기술 스택 추가
    - reactflow: 노드 기반 UI 구현
    - @reactflow/core, @reactflow/background, @reactflow/controls
    - TypeScript 타입 안정성 강화
    
    - 기존 frontend/src 폴더 삭제 후 처음부터 재구축
    - Design.md 대폭 보완: 구체적인 컴포넌트 스타일 가이드 추가
      * 카드, 버튼, 입력 필드, 테이블, 차트 등 컴포넌트별 상세 스타일
      * Glow Effect, Shimmer Loading, Liquid Flow 등 특수 효과 정의
      * 페이지별 레이아웃 가이드 및 반응형 브레이크포인트 구체화
    - styled-components 기반 Glass Morphism UI 구현
      * theme.ts: 컬러, 타이포그래피, 간격, 그림자 등 테마 시스템
      * animations.ts: 재사용 가능한 애니메이션 정의
      * GlassCard, GlassButton, GlassInput, LiquidBackground 공통 컴포넌트
    - 새로운 디렉토리 구조
      * components/common: 재사용 가능한 공통 컴포넌트
      * components/Layout: 레이아웃 및 네비게이션
      * components/Auth: 인증 컴포넌트
      * pages: 6개 페이지 (Dashboard, Backtest, Portfolio, AlphaPool, AlphaIncubator, Simulation)
      * contexts: React Context (AuthContext)
      * services: API 클라이언트 통합 관리
      * styles: 테마 및 애니메이션
      * types: TypeScript 타입 정의
    - 페이지 구현
      * Dashboard: 시스템 상태 및 핵심 메트릭 표시
      * Backtest: 백테스트 파라미터 설정 및 결과 시각화
      * Portfolio, AlphaPool, AlphaIncubator, Simulation: Coming Soon 페이지
    - 문서 업데이트
      * README.md: 프로젝트 전체 구조 및 사용법 재작성
      * Structure.md: 상세한 프론트엔드 구조 추가
      * LAW.md: 프론트엔드 구조 규칙 추가 (7-1~7-5)
    - package.json에 styled-components 의존성 추가

[7](20250115):사이드바 UI/UX 대폭 개선 및 Dynamic Island 스타일 구현
    ### 사이드바 크기 및 레이아웃 최적화
    - 사이드바 너비 축소: 280px → 240px (더 컴팩트한 레이아웃)
    - 본문 콘텐츠 최대 너비 조정: 1400px → 1200px (적절한 여백 확보)
    - 로고 텍스트 단축: "QUANT LAB" → "LAB" (토글 상태에서 잘림 방지)
    
    ### Dynamic Island 스타일 토글 애니메이션 구현
    - **단계별 애니메이션**: 좌우 축소 → 상하 모아짐 → Dynamic Island 형태
    - **역방향 애니메이션**: 열 때는 상하 펼쳐짐 → 좌우 확장
    - **고급 이징**: cubic-bezier(0.23, 1, 0.32, 1) 적용으로 자연스러운 움직임
    - **지연 애니메이션**: width(0.3s) → height/border-radius/backdrop-filter(0.1s 지연)
    
    ### Context 기반 상태 관리 시스템 구축
    - **SidebarContext**: Layout과 Sidebar 간 상태 동기화
    - **자동 애니메이션**: 사이드바 토글 시 본문 콘텐츠 자동 좌우 이동
    - **반응형 레이아웃**: 열림(240px 여백) ↔ 닫힘(80px 여백) 자연스러운 전환
    
    ### 메뉴 정렬 및 아이콘 최적화
    - **완벽한 좌측 정렬**: 로고, 섹션 제목, 메뉴 아이템 모두 동일한 기준선
    - **아이콘 중앙 정렬**: 닫힘 상태에서 아이콘 완벽한 중앙 배치
    - **패딩 통일**: 모든 요소 16px 좌우 패딩으로 일관성 확보
    - **아이콘 크기 고정**: 20px × 20px 고정 크기로 정확한 정렬
    
    ### 토글 상태 UI 개선
    - **아이템 완전 붙임**: 토글 시 모든 메뉴 아이템 gap: 0으로 완전히 붙어있음
    - **조건부 렌더링**: 토글/오픈 상태에 따라 완전히 다른 레이아웃 구조
    - **Dynamic Island 효과**: 둥근 모서리, 블러 효과, 그림자로 iOS 스타일 구현
    - **수직 위치 조정**: 토글 상태에서 드래그로 상하 위치 조정 가능
    
    ### 애니메이션 성능 최적화
    - **부드러운 전환**: 0.5초 duration으로 자연스러운 움직임
    - **버벅거림 제거**: 고급 이징 함수로 부드러운 애니메이션
    - **단계별 처리**: width → height → position 순서로 자연스러운 변화

[8](20250115):사이드바 세부 조정 및 마우스 추적 최적화
    ### 양방향 애니메이션 시스템 완성
    - **닫히는 애니메이션**: 좌우 축소 → 상하 모아짐 → Dynamic Island 형태
    - **열리는 애니메이션**: 상하 펼쳐짐 → 좌우 확장 (완전히 반대 순서)
    - **현업 수준 이징**: cubic-bezier(0.16, 1, 0.3, 1) 적용
    - **미세한 지연**: 각 속성별 0.05s~0.15s 지연으로 자연스러운 흐름
    
    ### 마우스 추적 반응성 완전 개선
    - **즉시 반응**: requestAnimationFrame 제거로 지연 없는 업데이트
    - **실시간 동기화**: 마우스 움직임과 사이드바가 100% 동시에 움직임
    - **완벽한 추적**: 드래그 시 버벅거림 없는 부드러운 움직임
    
    ### 로고 아이콘 정렬 최적화
    - **패딩 조정**: 상하 8px, 좌우 12px로 비율 최적화
    - **높이 통일**: 36px로 다른 아이콘들과 동일한 높이
    - **완벽한 정렬**: 모든 방향이 일관되게 정렬된 균형잡힌 디자인
    
    ### 토글 버튼 공간 확장
    - **마진 증가**: 4px → 12px (3배 증가)
    - **적절한 간격**: 마지막 메뉴 아이템과 토글 버튼 사이 충분한 여백
    - **사용성 개선**: 토글 버튼을 더 쉽게 클릭할 수 있는 공간 확보

[9](20250115):텍스트 색상 및 투명 문제 해결
    ### 텍스트 색상 시스템 개선
    - **선택된 텍스트**: `#FFFFFF` (흰색)으로 명확한 대비
    - **호버 텍스트**: `#FFFFFF` (흰색)으로 일관성 유지
    - **일반 텍스트**: `#9AA0A6` (보조 텍스트 색상) 유지
    - **투명 문제 해결**: `background-clip: text` 및 `transparent` 색상 제거

    ### 리퀴드 글래스 금색 시스템 완성
    - **3단계 그라데이션**: 더 부드럽고 자연스러운 금색 효과
    - **투명도 조정**: `rgba(255, 215, 0, 0.12)` → `rgba(255, 140, 0, 0.05)`
    - **배경과 텍스트 분리**: 충돌 없이 각각 독립적인 효과
    - **GlassButton 업데이트**: 흰색 텍스트 + 리퀴드 글래스 배경

    ### 문서 업데이트
    - **Design.md**: 새로운 텍스트 색상 가이드라인 추가
    - **컴포넌트 스타일**: 네비게이션 메뉴 및 버튼 스타일 업데이트
    - **색상 팔레트**: 빛나는 텍스트 효과 및 부드러운 그라데이션 추가

[10](20250115):푸터 및 로그인 화면 현대화
    ### 푸터 완전 리뉴얼
    - **브랜드명 변경**: "QUANT LAB" → "Smart Analytics"
    - **설명 업데이트**: "알고리즘 트레이딩 플랫폼을 제공합니다"
    - **소셜 링크**: GitHub, Instagram만 유지 (실제 링크 연결)
    - **메뉴 구조**: "빠른 링크" → "Document"로 변경
    - **메뉴 항목**: 회사 소개, 자주 묻는 질문, 구성원, 연락
    - **레이아웃**: 3열 그리드 (브랜드 + Document + 빈 공간)
    - **카피라이트**: "2024" 제거, 동일 색상 적용

    ### 헤더 최적화
    - **높이 축소**: 패딩 `md` → `sm`으로 더 얇게
    - **배경 진하게**: `backgroundDark` 적용
    - **시각적 개선**: 더 컴팩트하고 모던한 느낌

    ### 로그인 화면 현대화
    - **브랜드 통일**: "Smart Analytics" + 흰색 동그라미 아이콘
    - **색상 일관성**: 금색 → 흰색 계열로 통일
    - **카드 개선**: 더 큰 패딩, 향상된 글래스 효과
    - **타이포그래피**: 더 읽기 쉬운 폰트 크기와 색상
    - **레이아웃**: 넓은 간격으로 깔끔한 구조

    ### 전체 디자인 통일성
    - **색상 팔레트**: 흰색/검은색/회색 계열로 완전 통일
    - **브랜드 일관성**: 모든 화면에서 "Smart Analytics" 사용
    - **현대적 디자인**: 깔끔하고 세련된 UI/UX

---

[11](20250115):알파 풀 노드 시스템 구현 (페이지 이름 수정)
    ### 노드별 상세 설정 모달
    - **NodeConfigModal 컴포넌트**: 5가지 노드 타입별 설정 UI
    - **데이터 소스**: S&P 500 선택, 날짜 범위 설정
    - **백테스트 조건**: 리밸런싱 주기, 거래비용, Quantile 설정

[12](20250115):Alpha Incubator 안정화 및 후보 패널 재구성
    - 대화 기록 복원 시 시스템 롤 제거 및 중복 사용자 입력 필터링으로 채팅 버블 2중 출력 해결
    - IME 조합 중 Enter 가로채기 및 로딩 상태 재진입 차단으로 메시지 전송 안정화
    - LangChain + MCTS 진행 시 상태 배지, 보류 메시지를 “탐색 중”으로 표기해 대기 상황 가시화
    - 후보 패널 헤더/카드 레이아웃을 고정 높이 + 내부 스크롤 구조로 재배치하고 점수·경로 배지를 추가
    - 백엔드에서 허용된 함수만 사용하도록 LLM 프로프트 강화, AST 기반 필터로 미지원 식별자 감지·차단
    - MCTS 트레이스에 필터링 사유를 기록하고 프런트엔드 경고/로그로 노출해 디버깅 편의성 향상
    - **GA 엔진**: 개체수, 세대, 최종 생존 수 파라미터 입력
    - **진화 과정**: 진행률 Progress Bar, 실시간 상태 표시
    - **최종 결과**: 생성된 알파 요약 정보, 상위 3개 알파 미리보기

[13](20250116):Qlib 레퍼런스 알파팩터 공유 레지스트리 연동
    - papers/Qlib 알파들.py의 Alpha360·Alpha158 스펙을 파싱해 Qlib 제공 알파를 재구성
    - Ref/Mean/Std/Quantile/IdxMax 등 qlib 연산자를 파이썬에서 재현하는 유틸리티 계층 작성
    - Qlib 전용 provider 추가(QLIB360/QLIB158 prefix) 후 WorldQuant 101 alongside 자동 등록
    - Registry bootstrap에 Qlib 등록 플로우 연결해 공유 알파 목록 확장
    - numpy.polyfit 경고 캡처 등 안전장치 포함, Transpiler와 호환되는 Series 반환 보장

    ### GA 실행 워크플로우
    - **GA 실행 버튼**: 조건 검증 후 백엔드 API 호출
    - **상태 폴링 시스템**: 1초마다 GA 진행 상태 확인
    - **실시간 노드 업데이트**: 각 단계별 상태(대기/실행/완료/실패) 표시
    - **엣지 동적 스타일**: 완료된 노드 간 링크 회색 → 흰색 변경
    - **애니메이션**: 실행 중인 단계 엣지 animated 효과

    ### 최종 알파 리스트 관리
    - **AlphaListPanel 컴포넌트**: 생성된 알파 목록 표시
    - **체크박스**: 저장할 알파 선택/전체 선택 기능
    - **인라인 편집**: 알파 이름 클릭하여 수정 가능
    - **알파 정보**: 이름, 수식, 적합도(fitness) 표시
    - **저장 버튼**: 선택한 알파를 UserAlpha.json에 저장

    ### UserAlpha 백엔드 API
    - **POST /api/user-alpha/save**: 사용자별 알파 저장
      - 세션 기반 사용자 인증
      - 고유 ID 자동 생성
      - database/userdata/user_alphas.json 파일 관리
    - **GET /api/user-alpha/list**: 내 알파 목록 조회
    - **DELETE /api/user-alpha/delete/<alpha_id>**: 알파 삭제

    ### AlphaPool 페이지 완전 재구성
    - **5개 노드 구조**: 데이터 → 백테스트 → GA → 진화 → 결과
    - **노드 더블클릭**: 각 노드별 설정 모달 열기
    - **시각적 피드백**: 완료된 노드 금색 그라데이션 강조
    - **전체 워크플로우**: 데이터 설정 → GA 실행 → 알파 저장 전체 연동
    - **레이아웃 개선**: 상단 타이틀 + GA 실행 버튼, 중앙 노드 그래프, 하단 알파 리스트
    
    ### 페이지 이름 변경
    - **AlphaPool** (기존 AI 채팅) → **AlphaIncubator** (알파 부화장)
    - **AlphaIncubator** (새 노드 시스템) → **AlphaPool** (알파 풀)
    
    ### AlphaPool 노드 시스템 리팩토링
    - **커스텀 노드 제거**: CustomNode 컴포넌트 삭제, ReactFlow 기본 노드 사용
    - **노드 타입 간소화**: `type: 'custom'` → `type: 'input'` / `type: 'output'` 또는 기본
    - **엣지 스타일 정리**: 
      - 애니메이션 조건 단순화 (실행 중일 때만)
      - 완료 시 금색 점선 엣지로 변경
      - 불필요한 dash 애니메이션 제거
    - **이벤트 핸들러 단순화**: 
      - 커스텀 노드의 onDoubleClick 제거
      - ReactFlow의 onNodeDoubleClick만 사용
    - **불필요한 핸들 제거**: sourceHandle, targetHandle 파라미터 제거
    - **useEffect 의존성 최적화**: nodes, edges를 의존성 배열에서 제거
    
    ### 완료 엣지 시각 효과 추가
    - **금색 점선**: 설정 완료된 노드 간 링크를 금색 점선으로 표시
    - **흐르는 애니메이션**: `@keyframes dashFlow`로 점선이 흐르는 효과
    - **빛나는 효과**: `drop-shadow`로 금색 글로우 효과
    - **인라인 스타일 + CSS 클래스**: 두 가지 방식으로 스타일 적용
      - `style` prop: `stroke`, `strokeWidth`, `strokeDasharray`, `filter`
      - CSS 클래스: `.react-flow__edge.completed` 셀렉터로 애니메이션

### [8] 2025.01.15 - 사이드바 토글 기능 개선
    ### 사이드바 토글 시 아이콘 간격 조정
    - **아이콘 간격 축소**: 토글 상태에서 아이콘들이 더 가까이 붙도록 조정
    - **프로그램 아이콘 변경**: Flask 아이콘을 흰 동그라미 아이콘으로 대체
    - **사이드바 크기 최적화**: 토글 시 공간 효율성 개선

### [9] 2025.01.15 - Dashboard 메인 페이지 Tab 기능 완전 구현 (Chrome 스타일)
    
    ### 백엔드 API 구현
    - **유저별 자산 데이터 관리**: `/api/dashboard/{user_id}` GET/POST 엔드포인트
    - **JSON 데이터 저장**: `Database/userdata/{user_id}_dashboard.json`
    - **기본 데이터 제공**: 파일이 없을 경우 샘플 데이터 반환
    
    ### 프론트엔드 탭 UI 구조 (Chrome 스타일)
    - **TabsContainer**: Chrome 스타일의 탭 네비게이션
    - **3개 탭 구현**:
      1. 내 자산 한눈에 보기
      2. 자산 관리
      3. 보유 주식 관리
    
    ### Chrome 스타일 탭 UI 개선 (2차 수정)
    - **색상 팔레트 단순화**: 흰색과 금색 계열만 사용 (Design.md 준수)
    - **불필요한 자산 제거**: 보험, 예적금 제거, 주식과 현금만 표시
    - **탭 위치 조정**: 헤더 바로 아래 배치, 상단 여백 제거
    - **박스와 글자 크기 최적화**: 가독성 개선을 위한 폰트 사이즈 조정
    - **Chrome 탭 스타일 완벽 구현**: 
      - 둥근 모서리, 상단 금색 강조선
      - 활성 탭과 비활성 탭의 명확한 구분
      - 부드러운 호버 효과
    
    ### 탭 1: 내 자산 한눈에 보기
    - **2개 자산 카드**:
      - 현금 자산 (흰색 글래스 효과)
      - 주식 자산 (금색 그라데이션)
      - 각 카드: 금액, 변동금액, 변동률(%) 표시
    
    - **도넛 차트**: Chart.js를 사용한 자산 비율 시각화
      - 주식 57.2%, 현금 42.8%
      - 금색과 흰색 계열만 사용
      - 중앙에 총 자산 합계 표시
      - 반응형 레전드
    
    - **적층형 바 차트**: 월별 자산 성장 추이
      - 2개 레이어: 주식(금색), 현금(흰색 계열)
      - 13개월 데이터 (24-02 ~ 25-02)
      - Y축: 0 ~ 60M 범위, M 단위 표시
      - 금색과 흰색 팔레트만 사용
    
    - **기간 선택 기능**:
      - 1년/30일 토글 버튼
      - Ant Design Slider 컴포넌트
      - 동적 기간 조정
    
    ### 탭 2: 자산 관리
    - **보유 현금 상세**: 보유 현금 총액 (글래스 카드)
    - **보유 주식 상세**: 평가금액, 평가손익(금색 강조), 수익률
    - **최근 거래 내역**: 날짜별 거래 내역 (입금/출금/배당)
      - 입금은 금색, 출금은 회색으로 표시
    
    ### 탭 3: 보유 주식 관리
    - **보유 주식 리스트**: 종목명, 수량, 평균 매수가, 평가금액, 수익률 표시
      - 수익률 양수는 금색, 음수는 회색
    - **섹터별 보유 현황**: 도넛 차트로 기술/금융/헬스케어/에너지 비율
      - 금색 계열 그라데이션 사용
    - **최근 매매 내역**: 매수/매도 내역 타임라인
      - 매도는 금색, 매수는 회색 강조
    
    ### 기술 스택
    - **Chart.js + react-chartjs-2**: 도넛/바 차트 렌더링
    - **Ant Design Slider**: 기간 선택 슬라이더
    - **styled-components**: 컴포넌트 스타일링
    - **TypeScript**: 타입 안정성
    
    ### 디자인 시스템 적용
    - **Chrome 스타일 탭**: 둥근 모서리, 금색 상단 강조선, 명확한 활성/비활성 구분
    - **색상 팔레트 준수**: Design.md에 명시된 흰색-금색 팔레트만 사용
    - **Liquid Glass 효과**: 모든 카드에 일관된 글래스모피즘
    - **금색 강조 색상**: 중요 정보에 liquidGoldGradient 적용
    - **반응형 그리드**: 화면 크기에 따라 레이아웃 조정
    - **일관된 타이포그래피**: theme.typography 사용
    - **헤더 바로 아래 탭 배치**: 상단 여백 제거, ContentWrapper 높이 100vh 설정
    
    ### 색상 팔레트 개선 (2차 수정)
    - **쨍한 노란색 제거**: `#FFD700`, `#FFA500`, `#FF8C00` 등 눈에 아픈 색상 완전 제거
    - **부드러운 금색 적용**: `#D4AF37` (부드러운 골드), `#B8860B` (다크 골든로드) 사용
    - **전체 색상 통일**: theme.ts, Dashboard.tsx, GlassButton.tsx, Sidebar.tsx, LiquidBackground.tsx 모든 파일 수정
    - **좌우 패딩 복원**: ContentWrapper에 `padding: 0 ${theme.spacing.xl}` 추가
    
    ### 탭 UI 개선 (3차 수정)
    - **탭 내 스크롤 제거**: `overflow-y: auto` → `overflow: visible`로 변경하여 모든 내용이 펼쳐지도록 수정
    - **탭 좌측 여백 제거**: ChromeTabsContainer의 `padding: 0 ${theme.spacing.lg}` → `padding: 0`으로 변경
    - **컨테이너 높이 조정**: DashboardContainer의 `height: 100%` → `min-height: 100vh`로 변경하여 내용에 따라 자동 확장
    
    ### 푸터 잘림 문제 해결 (4차 수정)
    - **Dashboard 높이 조정**: `min-height: 100vh` → `min-height: calc(100vh - 200px)`로 변경하여 푸터 공간 확보
    - **Layout 높이 조정**: ContentWrapper의 `height: 100vh` → `min-height: calc(100vh - 200px)`로 변경
    - **푸터 공간 확보**: 200px 여백을 두어 푸터가 잘리지 않도록 수정
    
    ### Chrome 스타일 탭 완전 구현 (5차 수정)
    - **위쪽 여백 추가**: ChromeTabsContainer에 `padding: 8px 0 0 0` 추가하여 위쪽에 살짝 여백 생성
    - **둥글게 픽된 효과**: `border-top-left-radius: 12px`, `border-top-right-radius: 12px`로 더 둥글게 처리
    - **자연스러운 연결**: `::before` 가상 요소로 위쪽에 8px 높이의 배경을 추가하여 아래와 자연스럽게 연결
    - **금색 강조선**: `::after` 가상 요소로 활성 탭 상단에 3px 높이의 금색 강조선 추가
    - **z-index 레이어링**: 활성 탭이 위로 올라오도록 z-index 설정
    - **부드러운 전환**: `transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1)`로 자연스러운 애니메이션
    
    ### Chrome 브라우저와 완전 동일한 탭 구현 (6차 수정)
    - **활성 탭 보더 제거**: 활성 탭의 `border: none`으로 하단 보더 완전 제거
    - **비활성 탭 보더 유지**: 비활성 탭은 `border: 1px solid ${theme.colors.border}` 유지
    - **탭 간격 제거**: `gap: 0`으로 탭들이 완전히 붙도록 설정
    - **콘텐츠 영역 연결**: TabContent에 `border-top: none`, `margin-top: -1px` 추가
    - **완전한 연결**: 활성 탭이 콘텐츠 영역과 시각적으로 하나의 단위로 보이도록 구현
    - **둥근 모서리**: TabContent에 `border-bottom-left-radius: 12px`, `border-bottom-right-radius: 12px` 추가
    
    ### 다이나믹 아일랜드 스타일 네비게이션 구현 (7차 수정)
    - **Chrome 스타일 탭 제거**: 복잡한 Chrome 스타일 탭을 완전히 제거
    - **다이나믹 아일랜드 네비게이션**: Apple의 다이나믹 아일랜드를 참고한 슬림한 네비게이션 바 구현
    - **글래스모피즘 효과**: `backdrop-filter: blur(20px)`, `liquidGlass` 배경으로 투명 유리 효과
    - **둥근 모서리**: `border-radius: 28px`로 다이나믹 아일랜드와 동일한 둥글기
    - **중앙 정렬**: `justify-content: center`, `max-width: fit-content`로 중앙에 배치
    - **활성 버튼 강조**: 활성 버튼에 `liquidGoldGradient` 배경과 그림자 효과
    - **호버 애니메이션**: `transform: scale(1.02)`로 부드러운 확대 효과
    - **콘텐츠 영역 분리**: TabContent를 독립적인 카드로 분리하여 더 깔끔한 레이아웃

    ### 다이나믹 아일랜드 스타일 개선 (8차 수정)
    - **테마 에러 수정**: `liquidGlassGradient` → `liquidGlass`로 수정하여 TypeScript 에러 해결
    - **좌측 정렬**: `justify-content: center` → `justify-content: flex-start`로 변경하여 좌측 정렬
    - **좌측 패딩 추가**: `margin: auto` → `margin: ${theme.spacing.lg} ${theme.spacing.lg}`로 좌측 여백 추가
    - **선택된 버튼 글자색**: `color: '#000000'` → `color: theme.colors.textPrimary`로 변경하여 하얀색 적용
    - **호버 시 글자색 통일**: 모든 호버 상태에서 `color: theme.colors.textPrimary` 적용하여 일관성 확보

### [12] 2025.01.15 - '내 투자' 페이지 및 사용자 데이터베이스 시스템 구현

#### '내 투자' 페이지 구현
- **페이지 생성**: `MyInvestment.tsx` 컴포넌트 생성
- **자산 현황 섹션**: 총 자산, 현금/투자 비중을 도넛 차트로 시각화
- **계정 설정 섹션**: 이름, 이메일, 비밀번호 변경 기능
- **자산 변화 차트**: 월별 자산 변화를 바 차트로 표시
- **반응형 디자인**: 모바일/데스크톱 대응 그리드 레이아웃

#### 사이드바 메뉴 추가
- **메뉴 아이템 추가**: '내 투자' 메뉴를 대시보드 바로 아래에 배치
- **아이콘 추가**: `UserOutlined` 아이콘 사용
- **라우팅 연결**: `/my-investment` 경로로 연결

#### 사용자 데이터베이스 모듈 설계
- **UserDatabase 클래스**: 사용자 계정, 투자 데이터, 설정 통합 관리
- **데이터 구조**: JSON 파일 기반 (users.json, user_investments.json, user_settings.json)
- **보안**: 비밀번호 SHA256 해시화, 세션 기반 인증
- **기능**: 사용자 생성/인증/수정/삭제, 투자 데이터 관리, 설정 관리

#### 백엔드 API 엔드포인트 구현
- **사용자 등록**: `POST /api/user/register`
- **사용자 로그인**: `POST /api/user/login`
- **사용자 정보**: `GET /api/user/info`, `PUT /api/user/update`
- **비밀번호 변경**: `POST /api/user/change-password`
- **투자 데이터**: `GET /api/user/investment`, `PUT /api/user/investment`
- **사용자 설정**: `GET /api/user/settings`, `PUT /api/user/settings`
- **로그아웃**: `POST /api/user/logout`

#### 데이터 흐름 설계
```
사용자 등록 → 초기 투자 데이터 생성 → 자산 현황 표시
     ↓
계정 설정 → 사용자 정보 수정 → 투자 데이터 업데이트
     ↓
자산 변화 추적 → 히스토리 저장 → 차트 시각화
```

    ### 데이터 흐름 완성
    ```
    사용자 노드 설정 → GA 파라미터 입력 → "GA 실행" 클릭
      ↓
    백엔드 /api/ga/run 호출 (개체수, 세대 전달)
      ↓
    task_id 받아 1초마다 /api/ga/status/<task_id> 폴링
      ↓
    진행률 노드에 실시간 반영 (0% → 100%)
      ↓
    완료 시 결과 노드에 알파 리스트 표시
      ↓
    하단 AlphaListPanel에 체크박스 + 이름 편집 UI
      ↓
    "저장" 버튼 클릭 → /api/user-alpha/save 호출
      ↓
    UserAlpha.json에 유저별로 저장 완료
    ```

    ### 기술 스택
    - **프론트엔드**: ReactFlow, Ant Design (Modal, Progress, DatePicker 등)
    - **상태 관리**: useState, useEffect, useCallback
    - **스타일링**: styled-components, Apple-style UI 원칙 적용
    - **백엔드**: Flask, JSON 파일 기반 저장소

### [13] 2025.01.15 - CSV 기반 회원 관리 시스템 구축

#### CSV 데이터 구조 설계
- **6개 CSV 파일**: users, investments, portfolios, user_alphas, transactions, asset_history
- **관계형 설계**: user_id를 Foreign Key로 모든 테이블 연결
- **데이터 무결성**: 애플리케이션 레벨에서 제약 관리
- **인코딩**: UTF-8 with BOM (utf-8-sig) 사용

#### 백엔드 모듈 구현
- **CSVManager 클래스**: 모든 CSV 데이터 CRUD 작업 통합 관리
- **사용자 관리**: 생성, 인증, 정보 조회/수정, 비밀번호 변경
- **투자 관리**: 자산 현황 조회/업데이트, 자산 이력 자동 기록
- **포트폴리오 관리**: 종목 추가/제거, 평균 매수가 계산
- **거래 내역**: 모든 금융 거래 기록 (매수/매도/입출금)
- **알파 관리**: 사용자별 알파 저장/조회/삭제

#### REST API 엔드포인트 추가
- **사용자 API**: `/api/csv/user/register`, `/api/csv/user/login`, `/api/csv/user/info`
- **투자 API**: `/api/csv/user/investment` (자산 현황 + 이력)
- **포트폴리오 API**: `/api/csv/user/portfolio` (보유 주식 목록)
- **거래 API**: `/api/csv/user/transactions` (거래 내역)
- **알파 API**: `/api/csv/user/alphas`, `/api/csv/user/alpha/save`

#### 테스트 데이터 생성
- **Admin 계정**: admin / admin123 (5천만원 자산)
- **포트폴리오**: 5개 종목 (AAPL, MSFT, GOOGL, AMZN, TSLA)
- **자산 구성**: 현금 2천만원, 주식 3천만원
- **데이터 위치**: `database/csv_data/` 디렉토리

#### 문서화 완료
- **DataStructure.md**: 상세한 CSV 구조 명세서 작성
- **ERD 다이어그램**: 테이블 간 관계 시각화
- **JOIN 예시**: 실제 활용 방법 제공
- **Request.md**: 완료된 과업으로 이동

#### 시스템 특징
- **확장성**: 새로운 사용자 데이터 필드 추가 용이
- **성능**: pandas DataFrame으로 대량 데이터 처리
- **보안**: 비밀번호 SHA256 해시화
- **백업**: CSV 파일 기반으로 간단한 백업/복구
- **개발**: 관계형 DB 없이도 JOIN 기능 구현

#### 데이터 흐름
```
사용자 등록 → 초기 투자 데이터 생성 → 포트폴리오 관리
     ↓
거래 실행 → 자산 이력 기록 → 알파 생성/저장
     ↓
대시보드 조회 → CSV JOIN → 통합 데이터 표시
```

---

## [14] 2025.01.15 - 프로필 설정 페이지 및 사용자 인터페이스 개선

### 개요
Request.md의 회원 기능 구현 요청사항에 따라 프로필 설정 페이지를 생성하고, 사용자 인터페이스를 개선했습니다.

### 1. 프로필 설정 페이지 생성
- **파일**: `frontend/src/pages/Profile.tsx` (신규 생성)
- **기능**:
  - 프로필 이모티콘 선택 (16가지 이모지)
  - 닉네임, 이름, 이메일 수정
  - 비밀번호 변경
  - 실시간 CSV 데이터 연동
- **UI**:
  - 2단 그리드 레이아웃 (프로필 사이드바 + 정보 카드)
  - 원형 프로필 이미지 (이모티콘)
  - 이모지 선택 그리드 (8x2)
  - Liquid Glass 스타일 일관성 유지

### 2. '내 투자' 페이지 리팩토링
- **파일**: `frontend/src/pages/MyInvestment.tsx`
- **변경사항**:
  - 계정 설정 섹션 제거
  - 자산 현황에만 집중 (1단 레이아웃)
  - CSV API 연동으로 실시간 투자 데이터 로드
  - 미사용 컴포넌트 및 import 정리

### 3. 사이드바 개선
- **파일**: `frontend/src/components/Layout/Sidebar.tsx`
- **기능**:
  - 토글되지 않은 상태에서 프로필 아이콘 버튼 추가
  - 프로필 아이콘 클릭 시 `/profile` 페이지로 이동
  - 토글 상태에서는 프로필 아이콘 숨김
- **스타일**:
  - `BottomButtonContainer`: 프로필 버튼과 토글 버튼을 담는 컨테이너
  - `ProfileButton`: 프로필 페이지로 이동하는 버튼

### 4. 헤더 개선
- **파일**: `frontend/src/components/Layout/Layout.tsx`
- **변경사항**:
  - (닉네임)(원형 프로필 이모티콘) 형태로 표시
  - CSV에서 실시간 프로필 정보 로드
  - 클릭 시 프로필 페이지로 이동
  - "Logout" → "로그아웃" 한글화
- **스타일**:
  - `UserNickname`: 닉네임 표시 텍스트
  - `ProfileEmoji`: 원형 이모티콘 컨테이너 (32px, 금색 테두리)
  - 버튼 형태로 변경하여 클릭 가능

### 5. 백엔드 API 추가
- **파일**: `backend/app.py`
- **신규 엔드포인트**:
  - `PUT /api/csv/user/profile/update`: 프로필 정보 업데이트
  - `POST /api/csv/user/password/change`: 비밀번호 변경
- **기능**:
  - 닉네임, 이름, 이메일, 프로필 이모티콘 업데이트
  - 현재 비밀번호 확인 후 새 비밀번호로 변경

### 6. CSV 데이터 구조 개선
- **파일**: `backend/csv_manager.py`
- **변경사항**:
  - `users.csv`에 `profile_emoji` 컬럼 추가
  - 기존 사용자에게 기본 이모지('😀') 자동 할당
  - `create_user()` 함수에 `profile_emoji` 파라미터 추가 (기본값: '😀')
  - 초기화 시 컬럼 마이그레이션 자동 처리

### 7. 프론트엔드-백엔드 연동
- **프로필 페이지**:
  - `GET /api/csv/user/info`: 사용자 정보 로드
  - `PUT /api/csv/user/profile/update`: 프로필 업데이트
  - `POST /api/csv/user/password/change`: 비밀번호 변경
- **내 투자 페이지**:
  - `GET /api/csv/user/investment`: 투자 데이터 로드
- **헤더**:
  - `GET /api/csv/user/info`: 프로필 정보 로드 및 표시

### 8. 라우팅 추가
- **파일**: `frontend/src/App.tsx`
- **라우트**: `/profile` → `<Profile />` 컴포넌트

### 구현 완료 내용
✅ 프로필/계정 설정 페이지 생성  
✅ '내 투자' 페이지에서 계정 정보 기능 제거  
✅ 토글 버튼 오른편에 프로필 아이콘 추가 (토글 상태에서만 표시)  
✅ 우측 상단 로그인 표시를 (닉네임)(원형 프로필 이모티콘)으로 변경  
✅ CSV 기반 회원 데이터와 프론트엔드 연동  

### 디자인 일관성
- Liquid Glass UI 유지
- 애플 HIG 디자인 원칙 준수
- Soft Gold 색상 팔레트 사용
- 부드러운 애니메이션 및 트랜지션

---

## [15] 2025.01.15 - 인증 시스템 개선 및 UI 마이너 수정

### 개요
사용자 피드백에 따라 인증 시스템을 실제 CSV 백엔드와 완전히 연동하고, UI 세부 사항을 개선했습니다.

### 1. 사이드바 하단 아이콘 간격 조정
- **파일**: `frontend/src/components/Layout/Sidebar.tsx`
- **변경사항**:
  - `BottomButtonContainer`에 `justify-content: space-between` 적용
  - 프로필 아이콘과 토글 버튼을 양 끝으로 배치
  - `gap` 제거하고 `space-between`으로 자연스러운 간격 확보

### 2. 로그아웃 버튼 아이콘화
- **파일**: `frontend/src/components/Layout/Layout.tsx`
- **변경사항**:
  - 로그아웃 버튼을 원형 아이콘 버튼으로 변경 (32px)
  - 텍스트 제거, 아이콘만 표시
  - `title` 속성으로 툴팁 제공 ("로그아웃")
  - 호버 시 `transform: scale(1.05)` 효과

### 3. 회원가입/로그인 실제 CSV 연동
#### 3.1. AuthContext 개선
- **파일**: `frontend/src/contexts/AuthContext.tsx`
- **기능**:
  - `register` 함수 추가
  - 로컬 스토리지 대신 세션 기반 인증으로 전환
  - `POST /api/csv/user/login` - 실제 로그인 API 호출
  - `POST /api/csv/user/register` - 회원가입 API 호출
  - `POST /api/csv/user/logout` - 로그아웃 API 호출
  - `GET /api/csv/user/info` - 세션 확인 및 사용자 정보 로드
  - 에러 메시지를 백엔드에서 받아서 표시

#### 3.2. Auth 컴포넌트 개선
- **파일**: `frontend/src/components/Auth/Auth.tsx`
- **기능**:
  - 로그인/회원가입 탭 추가
  - 회원가입 폼: 아이디, 이메일, 이름, 비밀번호 입력
  - 로그인 폼: 아이디, 비밀번호 입력
  - 탭 전환 시 폼 내용 동적 변경
  - 실제 백엔드 API와 연동
  - 에러 메시지 표시 개선
- **스타일**:
  - `TabContainer`: 탭 컨테이너
  - `Tab`: 개별 탭 버튼 (활성화 시 금색 그라데이션)

#### 3.3. 백엔드 로그아웃 API 추가
- **파일**: `backend/app.py`
- **엔드포인트**: `POST /api/csv/user/logout`
- **기능**:
  - 세션 완전 삭제 (`session.clear()`)
  - 성공 메시지 반환

#### 3.4. User 타입 확장
- **파일**: `frontend/src/types/index.ts`
- **변경사항**:
  - `User` 인터페이스에 `name?: string` 필드 추가
  - 백엔드 데이터 구조와 일치

### 4. App.tsx 연동
- **파일**: `frontend/src/App.tsx`
- **변경사항**:
  - `useAuth`에서 `register` 함수 가져오기
  - `Auth` 컴포넌트에 `onRegisterSuccess={register}` prop 전달

### 구현 완료 내용
✅ 사이드바 하단 아이콘 양 끝 배치  
✅ 로그아웃 버튼 아이콘화 (원형, 32px)  
✅ 회원가입 기능 추가 (탭 전환)  
✅ 실제 CSV 백엔드와 인증 시스템 완전 연동  
✅ 세션 기반 인증으로 전환  
✅ 에러 핸들링 개선  

### 보안 개선
- 로컬 스토리지 대신 서버 세션 사용
- 비밀번호는 SHA256 해시로 저장
- 인증 실패 시 명확한 에러 메시지 제공
- 세션 만료 시 자동 로그아웃

### 사용자 경험 개선
- 로그인/회원가입을 한 화면에서 전환 가능
- 실시간 에러 피드백
- 로딩 상태 표시
- 매끄러운 탭 전환 애니메이션

---

## [16] 2025.01.15 - Troubleshooting.md 문서 생성 및 LAW 규칙 추가

### 개요
개발 중 발생한 문제와 해결 과정을 체계적으로 기록하기 위한 트러블슈팅 문서를 생성하고, LAW.md에 관련 규칙을 추가했습니다.

### 1. Troubleshooting.md 생성
- **파일**: `Document/Troubleshooting.md` (신규 생성)
- **목적**: 문제 해결 과정을 체계적으로 문서화하여 향후 유사한 문제 발생 시 빠른 해결
- **구조**:
  - 문제 번호별 상세 기록
  - 템플릿 제공
  - FAQ 섹션
  - 디버깅 체크리스트
  - 로그 수집 방법

### 2. 첫 번째 트러블슈팅 사례 기록
**문제**: Proxy Error & CSV 인증 시스템 연동 실패

#### 원인
1. **포트 불일치**: 백엔드 5000 / 프론트엔드 proxy 5002
2. **CSV 스키마 불일치**: profile_emoji 필드 누락

#### 해결
1. `frontend/package.json` - proxy를 5000으로 수정
2. `backend/create_admin.py` - profile_emoji 필드 추가
3. CSV 파일 재생성
4. 백엔드 재시작

#### 교훈
- 포트 변경 시 모든 설정 파일 동기화 필요
- CSV 스키마 변경 시 초기화 스크립트도 함께 업데이트
- 데이터 파일 생성 후 스키마 검증 필요

### 3. LAW.md 규칙 추가
- **파일**: `Document/LAW.md`
- **추가 섹션**: `8. 트러블슈팅 기록 규칙`
- **핵심 규칙**:
  - 모든 문제는 번호와 날짜로 체계적 관리
  - 문제 상황, 원인, 해결 과정, 검증 결과 완전 문서화
  - 에러 메시지와 코드 예시 명확히 기재
  - 교훈 및 예방책 기록
  - 관련 파일과 문서 링크 추가
  - FAQ와 디버깅 체크리스트 활용

### 4. 문서 구조 개선
```
Document/
├── Log.md                    # 개발 이력 (성공적인 구현)
├── Troubleshooting.md        # 문제 해결 이력 (트러블슈팅)
├── Request.md                # 요청사항 관리
├── LAW.md                    # 개발 규칙
├── Design.md                 # 디자인 가이드
├── DataStructure.md          # 데이터 구조
├── Structure.md              # 프로젝트 구조
└── API_ENDPOINTS.md          # API 문서
```

### 5. 트러블슈팅 문서 특징
- **구조화된 템플릿**: 일관된 형식으로 문제 기록
- **코드 예시**: 변경 전/후 비교로 명확한 이해
- **검증 결과**: 체크리스트로 해결 확인
- **예방 방법**: 재발 방지를 위한 구체적 가이드
- **FAQ**: 자주 발생하는 문제 빠른 참조
- **디버깅 체크리스트**: 체계적인 문제 진단

### 6. 활용 방법
#### 문제 발생 시
1. Troubleshooting.md 열기
2. 템플릿 복사
3. 문제 상황 기록
4. 해결 과정 단계별 기록
5. 검증 및 교훈 정리

#### 문제 해결 후
1. Log.md에 성공 사례로 기록
2. 관련 문서 링크 업데이트
3. FAQ 업데이트 (재발 가능성 높은 경우)

### 구현 완료 내용
✅ Troubleshooting.md 문서 생성  
✅ 첫 트러블슈팅 사례 완전 기록  
✅ 문제 해결 템플릿 제공  
✅ FAQ 섹션 구성  
✅ 디버깅 체크리스트 작성  
✅ LAW.md에 트러블슈팅 규칙 추가  
✅ 문서 간 연계 구조 확립  

### 기대 효과
- 문제 해결 시간 단축 (유사 문제 빠른 검색)
- 지식 축적 및 공유
- 체계적인 디버깅 프로세스
- 재발 방지
- 팀원 온보딩 시 참고 자료

---

## [17] 2025.01.15 - 프로필 기능 버그 수정

### 개요
프로필 페이지의 이모티콘 변경, 정보 수정 기능이 작동하지 않는 문제를 수정했습니다.

### 1. 문제점
- ❌ 이모티콘 변경이 저장되지 않음
- ❌ 정보 수정(닉네임, 이름, 이메일)이 백엔드에 반영되지 않음
- ❌ 프론트엔드와 백엔드 간 필드명 불일치 (nickname vs username)

### 2. 해결 방법

#### 2.1. 프론트엔드 수정
- **파일**: `frontend/src/pages/Profile.tsx`
- **변경사항**:
  - API 요청 시 `nickname` → `username`으로 변경
  - 프로필 업데이트 성공 시 페이지 새로고침하여 헤더 정보도 즉시 반영
  - 성공 메시지 표시 추가

```typescript
// 변경 전
body: JSON.stringify({
  nickname: editData.nickname,  // ❌ 백엔드가 인식 못함
  ...
})

// 변경 후
body: JSON.stringify({
  username: editData.nickname,  // ✅ 백엔드 필드명과 일치
  name: editData.name,
  email: editData.email,
  profile_emoji: editData.profileEmoji
})
```

#### 2.2. 백엔드 수정
- **파일**: `backend/app.py`
- **변경사항**:
  - `username`과 `nickname` 둘 다 처리 가능하도록 하위 호환성 추가

```python
# 업데이트할 필드 처리
update_fields = {}
if 'username' in data:
    update_fields['username'] = data['username']
elif 'nickname' in data:  # 하위 호환성
    update_fields['username'] = data['nickname']
if 'profile_emoji' in data:
    update_fields['profile_emoji'] = data['profile_emoji']
```

### 3. 동작 흐름

```
사용자가 프로필 수정
    ↓
1. 이모티콘 선택 (EmojiOption 클릭)
    ↓
2. editData.profileEmoji 업데이트
    ↓
3. "저장" 버튼 클릭
    ↓
4. PUT /api/csv/user/profile/update
    ↓
5. CSV 파일 업데이트 (users.csv의 profile_emoji 컬럼)
    ↓
6. 성공 응답
    ↓
7. 페이지 새로고침
    ↓
8. 헤더의 프로필 이모티콘 즉시 반영 ✅
```

### 4. 테스트 결과

✅ **이모티콘 변경**: 16가지 이모지 선택 및 저장 정상 작동  
✅ **정보 수정**: 닉네임(username), 이름, 이메일 수정 정상 작동  
✅ **즉시 반영**: 수정 후 헤더의 프로필 정보 즉시 업데이트  
✅ **CSV 저장**: profile_emoji 필드가 올바르게 CSV에 저장됨  
✅ **비밀번호 변경**: 현재 비밀번호 확인 후 변경 정상 작동  

### 5. 변경된 파일

- `frontend/src/pages/Profile.tsx` - API 요청 필드명 수정
- `backend/app.py` - username/nickname 하위 호환성 추가

### 6. 확인 방법

1. 프로필 페이지 (`/profile`) 접속
2. "이모티콘 변경" 버튼 클릭
3. 원하는 이모티콘 선택 (예: 🤓)
4. "정보 수정" 클릭 → 이름, 이메일 수정 (아이디는 변경 불가)
5. "저장" 버튼 클릭
6. 페이지 새로고침 후 헤더 우측 상단의 프로필 이모티콘 확인
7. 변경사항이 즉시 반영됨 ✅

### 7. 버그 수정 및 보안 강화

#### 문제 발견
- 프로필 수정 시 username과 profile_emoji 필드가 업데이트되지 않음
- CSV 매니저의 `allowed_fields`에 누락된 필드 존재
- **보안 문제**: 로그인 아이디가 변경 가능하여 보안상 위험

#### 해결
1. **백엔드 보안 강화**
   - `backend/csv_manager.py`의 `allowed_fields`에서 `'username'` 제거
   - 이제 로그인 아이디는 변경 불가능하도록 제한
   - `profile_emoji`는 업데이트 가능하도록 유지

2. **프론트엔드 UX 개선**
   - `frontend/src/pages/Profile.tsx`에서 아이디 필드를 읽기 전용으로 변경
   - "(변경 불가)" 표시 추가로 사용자가 혼동하지 않도록 개선
   - 이제 로그인 아이디는 수정할 수 없음

3. **백엔드 API 개선**
   - 프로필 업데이트 API에서 username 필드 제거
   - name, email, profile_emoji만 업데이트 가능하도록 제한

#### 변경 전후 비교
```typescript
// 변경 전 (수정 가능)
<GlassInput
  value={editData.nickname}
  onChange={(e) => setEditData({ ...editData, nickname: e.target.value })}
/>

// 변경 후 (읽기 전용)
<div>
  {editData.nickname} (변경 불가)
</div>
```

```python
# 변경 전 (username 포함)
allowed_fields = ['name', 'email', 'username', 'profile_emoji']

# 변경 후 (username 제외)
allowed_fields = ['name', 'email', 'profile_emoji']
```

#### 테스트 결과
✅ **아이디 (username)**: 변경 불가능 (읽기 전용)
✅ **이름 (name)**: 정상 수정 가능
✅ **이메일 (email)**: 정상 수정 가능
✅ **이모티콘 (profile_emoji)**: 정상 수정 가능
✅ **보안 강화**: 로그인 아이디 변경으로 인한 보안 위험 제거
✅ **UX 개선**: "(변경 불가)" 표시로 사용자 혼동 방지

---

## [18] 2025.01.15 - 헤더 스타일 개선

### 개요
헤더 부분의 사용자 정보 표시 방식을 개선하여 더 깔끔하고 모던한 디자인을 구현했습니다.

### 1. UserInfo 컴포넌트 스타일 개선
- **파일**: `frontend/src/components/Layout/Layout.tsx`
- **변경사항**:
  - 배경색과 테두리 제거 (상자 형태 → 투명 버튼)
  - 패딩 제거로 더 자연스러운 배치
  - 호버 효과를 `scale(1.02)`로 변경하여 부드러운 상호작용

```typescript
// 변경 전 (상자 형태)
<UserInfo>
  <UserNickname>{userProfile.username}</UserNickname>
  <ProfileEmoji>{userProfile.emoji}</ProfileEmoji>
</UserInfo>

// 변경 후 (투명 버튼)
<UserInfo>
  <UserNickname>{userProfile.username}</UserNickname>
  <ProfileEmoji>{userProfile.emoji}</ProfileEmoji>
</UserInfo>
```

### 2. 헤더 레이아웃 개선
- **간격 통일**: 모든 요소(이름, 이모티콘, 로그아웃 버튼)의 간격을 `md`(16px)로 통일
- **시각적 균형**: 균일한 간격으로 더 깔끔하고 일관된 디자인 구현

### 3. 변수명 통일
- **변경사항**: `userProfile.nickname` → `userProfile.username`으로 수정
- **이유**: 실제로는 username 필드를 사용하므로 변수명 통일

### 구현 완료 내용
✅ **상자 제거**: 이름과 이모티콘을 감싸던 배경색과 테두리 제거
✅ **간격 조정**: 로그아웃 버튼과의 간격을 적절하게 확대
✅ **변수명 통일**: 코드의 일관성 개선
✅ **디자인 개선**: 더 모던하고 깔끔한 헤더 디자인 구현

### 결과
- 헤더가 더 깔끔하고 전문적인 느낌으로 개선됨
- 사용자 정보가 자연스럽게 배치되어 시각적 일관성 향상
- 로그아웃 버튼과의 간격이 적절하게 조정되어 사용성 개선

### 9. TypeScript 타입 에러 해결

#### 문제 발견
- Layout 컴포넌트에서 `userProfile.username` 참조 시 타입 에러 발생
- `userProfile` 상태의 타입 정의가 `nickname`으로 되어 있음

#### 해결
1. **상태 초기값 수정**
   ```typescript
   // 변경 전
   const [userProfile, setUserProfile] = useState({
     nickname: user?.username || '사용자',
     emoji: '😀'
   });

   // 변경 후
   const [userProfile, setUserProfile] = useState({
     username: user?.username || '사용자',
     emoji: '😀'
   });
   ```

2. **setUserProfile 호출 수정**
   ```typescript
   // 변경 전
   setUserProfile({
     nickname: userInfo.username || '사용자',
     emoji: userInfo.profile_emoji || '😀'
   });

   // 변경 후
   setUserProfile({
     username: userInfo.username || '사용자',
     emoji: userInfo.profile_emoji || '😀'
   });
   ```

#### 테스트 결과
✅ **타입 에러 해결**: `userProfile.username` 참조가 정상 작동
✅ **컴파일 성공**: TypeScript 빌드에서 에러 없이 통과
✅ **런타임 정상**: 사용자 정보가 올바르게 표시됨

---

## [19] 2025.01.15 - 헤더 간격 균일화

### 개요
헤더 부분의 모든 요소들(이름, 이모티콘, 로그아웃 버튼)의 간격을 동일하게 조정하여 시각적 일관성을 개선했습니다.

### 1. 간격 통일 문제 해결
- **파일**: `frontend/src/components/Layout/Layout.tsx`
- **변경사항**:
  - HeaderRight의 gap을 `lg`(24px)에서 `md`(16px)로 조정
  - UserInfo 내부의 gap을 `sm`(8px)에서 `md`(16px)로 조정
  - 이제 모든 요소의 간격이 16px로 통일됨

### 변경 전후 비교
```typescript
// 변경 전 (간격 불균일)
<HeaderRight>
  gap: ${theme.spacing.lg};  // 24px (로그아웃 버튼과의 간격)
</HeaderRight>

<UserInfo>
  gap: ${theme.spacing.sm};  // 8px (이름과 이모티콘 간격)
</UserInfo>

// 변경 후 (간격 통일)
<HeaderRight>
  gap: ${theme.spacing.md};  // 16px (로그아웃 버튼과의 간격)
</HeaderRight>

<UserInfo>
  gap: ${theme.spacing.md};  // 16px (이름과 이모티콘 간격)
</UserInfo>
```

### 2. 시각적 개선 효과
- **균일한 간격**: 모든 요소가 동일한 16px 간격으로 배치되어 깔끔한 디자인 구현
- **시각적 일관성**: 요소들 간의 관계가 명확하고 균형 잡힌 레이아웃
- **사용성 향상**: 일관된 간격으로 직관적인 사용자 경험 제공

### 구현 완료 내용
✅ **간격 통일**: 모든 헤더 요소의 간격을 16px로 표준화
✅ **시각적 균형**: 이름 ↔ 이모티콘 ↔ 로그아웃 버튼의 균형 잡힌 배치
✅ **디자인 개선**: 더 깔끔하고 전문적인 헤더 디자인 구현

### 결과
- 헤더 요소들이 균일한 간격으로 배치되어 시각적 일관성 대폭 향상
- 사용자가 요소들 간의 관계를 직관적으로 이해할 수 있음
- 전체적인 디자인 완성도가 높아짐

[20](20250115):리팩토링 1차 - 포트폴리오 실데이터 연동 및 UI 정비
    - `frontend/src/pages/Portfolio.tsx`를 CSV 기반 API 연동 구조로 전면 수정하고 매수·매도 모달 및 실시간 지표 계산을 추가했습니다.
    - `backend/app.py`, `backend/csv_manager.py`에 포트폴리오 추가/매도 엔드포인트와 평가액 재계산 로직을 도입하여 투자 요약·거래 내역을 자동 동기화했습니다.
    - Dashboard·Backtest·AlphaIncubator 페이지의 한글화와 거래 타입 표기, 사이드바 로고/간격, 테마 컬러 일관성을 보완했습니다.
    - `Document/ImplementationSummary.md`, `Document/Design.md`, `Document/Structure.md`에 리팩토링 범위와 구조 점검 결과를 반영했습니다.

[21](20250115):리팩토링 2차 - GA 연동 안정화 및 투자 화면 개선
    - AlphaPool에서 GA 실행·상태 조회·알파 저장을 `services/api.ts`로 통합하고 폴링 로직을 `useRef` 기반으로 안정화했습니다.
    - Footer 접근성 경고를 제거하고 내부 링크를 버튼화하여 ESLint 빌드 경고를 해소했습니다.
    - 포트폴리오 매수 시 보유 현금 검증과 매도 후 잔여 수량 안내를 추가하고, 백엔드에서 음수 현금 발생을 차단했습니다.
    - MyInvestment 자산 그래프를 실제 이력 데이터 기반으로만 표시하고, 이력 부재 시 안내 문구를 노출하도록 개선했습니다.

[22](20250116):AutoAlpha GA 다중 지표 적합도 및 연령층 전략 도입
    - `GA_algorithm/autoalpha_ga.py`에 다중 기간 IC, 정보비율, 회전율, 커버리지, PCA 기반 신규성을 결합한 `FitnessMetrics` 체계를 구축했습니다.
    - 평가 지표 가중치를 설정 파일 없이 조정할 수 있도록 `DEFAULT_METRIC_WEIGHTS`와 사용자 입력 병합 로직을 추가했습니다.
    - 토너먼트 선택, 신규성 아카이브, 세대 기반 연령층 재시작으로 탐색 다양성과 수렴 속도를 강화했습니다.
    - 초기화·진화 로그에 기간별 IC와 회전율 요약을 출력해 `/api/ga/run` 백엔드 로그가 즉시 해석 가능하도록 개선했습니다.

[23](20250117):알파 레지스트리/스토어 리팩토링 및 도큐먼트 반영
    - `alphas/` 패키지를 신설해 `AlphaDataset`, `AlphaRegistry`, `AlphaStore`, `compile_expression` 등 공용 모듈을 구축하고 WorldQuant 101 알파를 자동 등록했습니다.
    - 개인 알파 저장소를 `database/alpha_store/` 구조(공용 shared.json + private/<username>.json)로 이전하고, 레거시 `user_alphas.json`을 자동 마이그레이션하도록 했습니다.
    - `backend/app.py`와 `backend_module/4_ComputeAlphas.py`를 새로운 레지스트리 기반으로 통합해 공유/개인 알파를 일관된 파이프라인에서 계산·노출합니다.
    - ImplementationSummary, SystemReview, DataStructure 문서를 최신 아키텍처와 응답 스펙에 맞게 업데이트했습니다.

[24](20250117):알파 관리 UX/스토어 안정화 및 세션 연동 수정
    - CSV/JSON 로그인 흐름에서 `session['username']`이 유지되도록 보완하여 알파 저장 API가 “로그인이 필요합니다”를 잘못 띄우지 않도록 했습니다. (`backend/app.py`)
    - `AlphaStore.add_private`를 중복 감지 가능하도록 확장하고 메타데이터/태그 정규화, 생성·수정 시각 보존 로직을 추가했습니다. (`alphas/store.py`)
    - `/api/user-alpha/save|list|delete`가 단일 응답 스키마(`shared_alphas`, `private_alphas`, `summary`)를 반환하도록 리팩터링하고, Dashboard/AlphaPool에서 즉시 반영되도록 API 연동을 일원화했습니다. (`backend/app.py`, `frontend/src/services/api.ts`)
    - Dashboard 알파 탭 UI를 디자인 문서 기준으로 재정비하고, 개인/공용 알파 분리·카드 카운트·편집/삭제 흐름을 정상화했습니다. (`frontend/src/pages/Dashboard.tsx`)
    - AlphaPool 저장 패널은 선택 상태 초기화·피드백 문구 정교화로 UX를 개선하고 Null fitness도 안전하게 처리합니다. (`frontend/src/pages/AlphaPool.tsx`, `frontend/src/components/AlphaFactory/AlphaListPanel.tsx`)

[25](20250117):GA 적합도 안정화 및 AlphaPool 개인화 현황 연동
    - AutoAlphaGA 초기 워밍스타트 후보 수 제한 버그를 수정하고, 안전한 나눗셈·입력 정렬·자산축 PCA 벡터·정보비율 클램핑으로 수만 단위 적합도 폭주 문제를 차단했습니다. (`GA_algorithm/autoalpha_ga.py`)
    - `correlation` 연산은 인덱스/컬럼 교집합 정렬 후 계산하며, `FitnessMetrics` 정보비율은 변동성 바닥값(0.02) 적용과 ±10 범위로 제한해 수치 안정성을 확보했습니다. (`GA_algorithm/autoalpha_ga.py`)
    - AlphaPool 상단에 공유/개인 알파 현황 카드와 최근 개인 알파 목록을 추가하고, 저장 직후 AlphaStore 집계가 자동 새로고침되도록 연동했습니다. (`frontend/src/pages/AlphaPool.tsx`)

[26](20250117):백테스트 파이프라인 실시간 연동 및 상태 모니터링 강화
    - `/api/backtest`가 세션 사용자의 레지스트리에서 공용·개인 알파를 불러와 직접 팩터를 계산하도록 개선해 CSV에 없는 개인 알파도 즉시 백테스트할 수 있습니다. (`backend/app.py`, `alphas/base.py`, `alphas/transpiler.py`)
    - 백테스트 진행률·로그를 API 상태 객체에 누적하고, 작업 ID를 보존해 페이지 이동 후에도 폴링을 재개할 수 있게 했습니다. (`backend/app.py`)
    - 프론트의 Backtest 페이지는 알파 목록을 그룹화하여 표시하고, 진행 카드에 실시간 로그·작업 ID·진행률 바를 추가했습니다. 레이아웃도 수정해 푸터가 가려지지 않고 좌우 패널이 정렬됩니다. (`frontend/src/pages/Backtest.tsx`, `frontend/src/components/common/GlassInput.tsx`, `frontend/src/types/index.ts`)

[27](20251019):GA 결과 백테스트 실데이터 연동 및 누적 수익률 정합성 보완
    - `calculate_factor_performance` 유틸을 추가해 리밸런싱 주기·보유일수 기반 지표 계산을 공통화하고, 포트폴리오 성과 API가 동일 로직을 사용하도록 리팩토링했습니다. (`backend/app.py`)
    - `/api/ga/backtest/<task_id>`가 GA가 생성한 표현식을 트랜스파일해 실제 시세 데이터로 백테스트하도록 비동기 처리와 상태 저장을 구현하여, 랜덤 더미 결과 없이 완료 후에도 `/api/backtest/status/<id>`로 재확인할 수 있게 했습니다. (`backend/app.py`)
    - Backtest 페이지 누적 수익률 그래프가 롤링 CAGR 대신 `cumulative_returns`를 사용해 첫 지점을 항상 0%로 표시하도록 수정했습니다. (`frontend/src/pages/Backtest.tsx`)

[28](20251019):LangChain+MCTS AlphaIncubator 통합 및 대시보드 알파 검색 UX 개선
    - Ollama korean-qwen 모델을 이용한 LangChain+MCTS 파이프라인을 `/api/incubator/chat`/`session/<id>` 엔드포인트로 구현하고, 오프라인 시 규칙 기반 답변으로 폴백하도록 했습니다. (`backend/app.py`)
    - GA 결과 백테스트가 실데이터 성과를 반환하도록 공용 `calculate_factor_performance` 로직을 도입하고, Incubator 세션 보관/경로 추적 기능을 추가했습니다. (`backend/app.py`)
    - AlphaIncubator 페이지를 챗 패널 + 후보 알파 저장 패널 구조로 재작성하여 생성된 알파를 즉시 저장하고 MCTS 탐색 로그를 조회할 수 있게 했습니다. (`frontend/src/pages/AlphaIncubator.tsx`, `frontend/src/components/AlphaFactory/AlphaCandidatePanel.tsx`, `frontend/src/services/api.ts`, `frontend/src/types/index.ts`)
    - 대시보드 공용 알파 영역을 요약 카드만 남기고, 하단 알파 목록은 검색·페이지네이션(10개 단위) 박스로 개편했습니다. 개인/공용 알파를 통합 정렬 후 검색할 수 있습니다. (`frontend/src/pages/Dashboard.tsx`)

[29](20251019):Ollama 호출 안정화 및 AlphaIncubator 스크롤 개선
    - `call_local_llm`에 `num_ctx`, `num_predict`, `top_p`를 지정하고 MCTS 탐색 횟수를 2회로 축소해 Ollama 응답 타임아웃을 줄였습니다. (`backend/app.py`)
    - AlphaIncubator 채팅 패널의 자동 스크롤을 제거해 메시지 입력 시 화면이 임의로 내려가지 않도록 조정했습니다. (`frontend/src/pages/AlphaIncubator.tsx`)

[30](20251026):대시보드 종목 성과 분석 패널 및 API 확장
    - `/api/data/ticker-performance` 엔드포인트를 추가해 다중 종목의 누적 수익률·CAGR·Sharpe·MDD 등 핵심 지표를 계산하고 누락 종목 정보를 함께 반환합니다. (`backend/app.py`)
    - Dashboard 자산 탭을 Recharts 기반 멀티 라인 차트+지표 테이블 구조로 재작성하고, 우측 설정 패널에서 기간/종목을 선택해 분석을 실행하도록 UX를 개편했습니다. (`frontend/src/pages/Dashboard.tsx`)
    - 프론트 타입/서비스 정의에 티커 성과 스키마를 추가하고, 문서·API 사양을 최신 상태로 동기화했습니다. (`frontend/src/types/index.ts`, `frontend/src/services/api.ts`, `Document/API.md`, `Document/Structure.md`)

[31](20251026):백테스트 체결 시점 보정 및 동시성 제거
    - `calculate_factor_performance`를 리팩터링해 시그널 계산(t) → t+1 거래일 시가 체결 → 다음 리밸런싱 시가 청산의 Open-to-Open 수익률로 일관되게 계산합니다. (`backend/app.py`)
    - 백테스트/GA/포트폴리오 API가 가격 데이터를 불러올 때 Open 컬럼을 포함하고, 종가 기반 `NextDayReturn` 의존 로직을 제거했습니다. (`backend/app.py`)
    - 백엔드 전역에서 결과 요약/로그는 새 체결 모델의 지표를 사용하도록 갱신했습니다. (`backend/app.py`)
