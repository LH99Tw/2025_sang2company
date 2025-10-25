# 🔌 API 문서

**마지막 수정**: 2025.09.25

## 📋 개요
퀀트 금융 분석 시스템의 RESTful API 문서입니다.

## 🚀 기본 정보
- **Base URL**: `http://localhost:5002`
- **Content-Type**: `application/json`
- **인증**: JWT 토큰 기반 (향후 구현)

## 📊 주요 API 엔드포인트

### 🏥 시스템 상태
```http
GET /api/health
```
**응답 예시**:
```json
{
  "status": "healthy",
  "systems": {
    "backtest": true,
    "database": true,
    "ga": true,
    "langchain": true
  },
  "timestamp": "2025-09-25T22:00:53.061621"
}
```

### 📈 백테스트 API

#### 백테스트 실행 (비동기)
```http
POST /api/backtest
```
**요청 본문**:
```json
{
  "start_date": "2020-01-01",
  "end_date": "2024-12-31",
  "factors": ["alpha001"],
  "rebalancing_frequency": "weekly",
  "transaction_cost": 0.001,
  "quantile": 0.1
}
```

**응답**:
```json
{
  "success": true,
  "task_id": "backtest_1758805259",
  "status_url": "/api/backtest/status/backtest_1758805259",
  "message": "백테스트가 백그라운드에서 시작되었습니다"
}
```

#### 백테스트 상태 확인
```http
GET /api/backtest/status/{task_id}
```

**응답 (완료 시)**:
```json
{
  "status": "completed",
  "progress": 100,
  "results": {
    "alpha001": {
      "cagr": -0.5227127122188842,
      "sharpe_ratio": -3.944623330147816,
      "max_drawdown": -0.382728009541593,
      "ic_mean": -0.00927985766612655,
      "win_rate": 0.4,
      "volatility": 0.18303147611549248
    }
  }
}
```

### 💼 포트폴리오 API

#### 종목 선별
```http
POST /api/portfolio/stocks
```
**요청 본문**:
```json
{
  "alpha_factor": "alpha001",
  "top_count": 20,
  "selection_method": "count"
}
```

#### 성과 분석
```http
POST /api/portfolio/performance
```
**요청 본문**:
```json
{
  "alpha_factor": "alpha001",
  "top_count": 20,
  "start_date": "2020-01-01",
  "end_date": "2022-12-31",
  "transaction_cost": 0.001,
  "rebalancing_frequency": "weekly"
}
```

### 📊 데이터 API

#### 종목 성과 분석
```http
POST /api/data/ticker-performance
```
**요청 본문**:
```json
{
  "tickers": ["AAPL", "MSFT", "GOOGL"],
  "start_date": "2000-01-01",
  "end_date": "2024-12-31"
}
```

**응답 예시**:
```json
{
  "success": true,
  "series": [
    {"date": "2000-01-03", "AAPL": 0.0, "MSFT": 0.0, "GOOGL": 0.0},
    {"date": "2000-01-04", "AAPL": 0.012, "MSFT": -0.003, "GOOGL": 0.006}
  ],
  "metrics": [
    {
      "ticker": "AAPL",
      "cagr": 0.158,
      "sharpe_ratio": 1.42,
      "sortino_ratio": 2.11,
      "max_drawdown": -0.46,
      "win_rate": 0.55,
      "volatility": 0.27,
      "total_return": 5.42
    }
  ]
}
```
- **설명**: 기간 내 종목별 종가를 기반으로 누적 수익률을 0%에서 시작하도록 정규화하고, 백테스트 페이지와 동일한 핵심 지표(CAGR, Sharpe, Sortino, MDD, Win Rate, Volatility, Total Return)를 반환합니다.

### 🤖 AI 에이전트 API

#### 채팅
```http
POST /api/chat
```
**요청 본문**:
```json
{
  "message": "alpha001을 분석해줘",
  "user_id": "user123"
}
```

### 🧬 유전 알고리즘 API

#### GA 실행
```http
POST /api/ga/run
```
**요청 본문**:
```json
{
  "start_date": "2020-01-01",
  "end_date": "2024-12-31",
  "population_size": 50,
  "generations": 10,
  "max_alphas": 5,
  "rebalancing_frequency": "weekly",
  "transaction_cost": 0.001,
  "quantile": 0.1
}
```

### 📊 데이터 API

#### 알파 팩터 목록
```http
GET /api/data/factors
```

#### 데이터 통계
```http
GET /api/data/stats
```

## 🔧 파라미터 설명

### 리밸런싱 주기 (rebalancing_frequency)
- `daily`: 매일
- `weekly`: 매주 (월요일)
- `monthly`: 매월 (1일)
- `quarterly`: 분기별 (1, 4, 7, 10월 1일)

### 거래비용 (transaction_cost)
- **기본값**: 0.001 (0.1%)
- **범위**: 0.0 ~ 0.01 (0% ~ 1%)

### 분위수 (quantile)
- **기본값**: 0.1 (상위/하위 10%)
- **범위**: 0.01 ~ 0.5 (1% ~ 50%)

## ⚠️ 오류 처리

### 일반적인 오류 코드
- `400`: 잘못된 요청
- `404`: 리소스를 찾을 수 없음
- `500`: 서버 내부 오류

### 오류 응답 형식
```json
{
  "error": "오류 메시지",
  "code": "ERROR_CODE",
  "timestamp": "2025-09-25T22:00:53.061621"
}
```

## 📝 사용 예시

### Python 클라이언트 예시
```python
import requests

# 백테스트 실행
response = requests.post('http://localhost:5002/api/backtest', json={
    'start_date': '2020-01-01',
    'end_date': '2022-12-31',
    'factors': ['alpha001'],
    'rebalancing_frequency': 'weekly',
    'transaction_cost': 0.001,
    'quantile': 0.1
})

task_id = response.json()['task_id']

# 상태 확인
status = requests.get(f'http://localhost:5002/api/backtest/status/{task_id}')
print(status.json())
```

### JavaScript 클라이언트 예시
```javascript
// 백테스트 실행
const response = await fetch('http://localhost:5002/api/backtest', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    start_date: '2020-01-01',
    end_date: '2022-12-31',
    factors: ['alpha001'],
    rebalancing_frequency: 'weekly',
    transaction_cost: 0.001,
    quantile: 0.1
  })
});

const { task_id } = await response.json();

// 상태 확인
const statusResponse = await fetch(`http://localhost:5002/api/backtest/status/${task_id}`);
const status = await statusResponse.json();
console.log(status);
```
