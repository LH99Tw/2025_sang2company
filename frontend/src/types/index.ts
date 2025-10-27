// 📊 알파 팩터 타입
export interface AlphaFactor {
  id: string;
  name: string;
  description?: string;
  formula?: string;
}

// 📈 백테스트 파라미터
export interface BacktestParams {
  start_date: string;
  end_date: string;
  factors: string[];
  rebalancing_frequency: 'daily' | 'weekly' | 'monthly' | 'quarterly';
  transaction_cost: number;
  quantile: number;
  max_factors?: number;
}

// 📊 백테스트 결과
export interface BacktestResult {
  cagr: number;
  sharpe_ratio: number;
  sortino_ratio: number;
  max_drawdown: number;
  ic_mean: number;
  win_rate: number;
  volatility: number;
  total_return?: number;
  cumulative_returns?: Array<{ date: string; value: number }>;
  cagr_series?: Array<{ date: string; value: number }>;
}

// 💼 포트폴리오 종목 (실제 데이터베이스 구조)
export interface PortfolioStock {
  portfolio_id: string;
  user_id: string;
  ticker: string;
  company_name: string;
  quantity: number;
  avg_price: number;
  current_price: number;
  sector: string;
  purchase_date: string;
  updated_at: string;
}

// 💼 포트폴리오 응답 타입
export interface PortfolioResponse {
  portfolio: PortfolioStock[];
  total_value?: number;
}

// 📈 거래 내역 (실제 데이터베이스 구조)
export interface Transaction {
  transaction_id: string;
  user_id: string;
  transaction_type: '입금' | '출금' | '매수' | '매도' | '배당';
  ticker?: string;
  quantity?: number;
  price?: number;
  amount: number;
  transaction_date: string;
  note?: string;
}

// 📈 거래 내역 응답 타입
export interface TransactionResponse {
  transactions: Transaction[];
}

// 📊 자산 변동 이력 (실제 데이터베이스 구조)
export interface AssetHistory {
  history_id: string;
  user_id: string;
  total_assets: number;
  cash: number;
  stock_value: number;
  recorded_at: string;
}

// 📊 자산 변동 이력 응답 타입
export interface AssetHistoryResponse {
  history: AssetHistory[];
}

// 💰 투자 요약 데이터 (CSV 기반)
export interface InvestmentData {
  user_id: string;
  total_assets: number;
  cash: number;
  stock_value: number;
  updated_at: string;
}

// 💼 포트폴리오 종목 (기존 호환용 - 가중치 기반)
export interface PortfolioStockLegacy {
  ticker: string;
  weight: number;
  alpha_value: number;
  expected_return?: number;
}

// 👤 사용자 정보
export interface User {
  id: string;
  username: string;
  email?: string;
  name?: string;
}

// 📊 대시보드 메트릭
export interface DashboardMetrics {
  totalAlphas: number;
  activeBacktests: number;
  portfolioValue: number;
  dailyPnL: number;
}

// 🤖 AI 채팅 메시지
export interface ChatMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
}

export interface IncubatorMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp?: string;
  id?: string;
  pending?: boolean;
}

export interface AlphaCandidate {
  id: string;
  name: string;
  expression: string;
  rationale: string;
  score: number;
  path?: string[];
  selected: boolean;
}

export interface MctsTraceEntry {
  iteration: number;
  prompt: string;
  raw_response: string;
  scored_expression: string;
  score: number;
  reason?: string;
}

export interface IncubatorChatResponse {
  success: boolean;
  session_id: string;
  intent: string;
  reply: string;
  error?: string;
  candidates?: AlphaCandidate[];
  mcts_trace?: MctsTraceEntry[];
  warnings?: string[];
  history: IncubatorMessage[];
  llm_provider?: string;
}

// 🧬 GA 파라미터
export interface GAParams {
  start_date: string;
  end_date: string;
  population_size: number;
  generations: number;
  max_alphas: number;
  max_depth?: number;
  registry_seed_limit?: number;
  registry_seed_shuffle?: boolean;
  rebalancing_frequency: string;
  transaction_cost: number;
  quantile: number;
}

// 📊 차트 데이터 포인트
export interface ChartDataPoint {
  date: string;
  value: number;
  label?: string;
}

export interface TickerPerformanceSeriesEntry {
  date: string;
  [ticker: string]: number | string | null;
}

export interface TickerPerformanceMetric {
  ticker: string;
  cagr?: number;
  sharpe_ratio?: number;
  sortino_ratio?: number;
  max_drawdown?: number;
  win_rate?: number;
  volatility?: number;
  total_return?: number;
  ic_mean?: number | null;
  error?: string;
}

// ⚙️ API 응답
export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
  task_id?: string;
  status_url?: string;
}

// 🔄 백테스트 상태
export interface BacktestStatus {
  status: 'pending' | 'running' | 'completed' | 'failed';
  progress: number;
  results?: Record<string, BacktestResult>;
  error?: string;
  logs?: string[];
  parameters?: Record<string, any>;
}

// 📊 알파 저장소 타입 (백엔드 호환용)
export interface StoredAlpha {
  id: string;
  name: string;
  expression?: string;
  source: string;
  provider: string;
  owner?: string;
  created_at?: string;
  updated_at?: string;
  description?: string;
  tags?: string[];
  metadata?: {
    fitness?: number | null;
    transpiler_version?: string;
    python_source?: string;
    expression?: string;
    created_at?: string;
    updated_at?: string;
    [key: string]: any;
  };
}

// 📊 알파 정의 타입
export interface AlphaDefinition {
  name: string;
  compute: (dataset: any) => any;
  source: string;
  provider: string;
  owner?: string;
  description: string;
  version: string;
  tags: string[];
  metadata: Record<string, any>;
}

// 📝 알파 추가 요청 타입
export interface AddAlphaRequest {
  name: string;
  expression: string;
  description?: string;
  tags?: string[];
  metadata?: {
    fitness?: number;
  };
}

// 📝 알파 수정 요청 타입
export interface UpdateAlphaRequest extends AddAlphaRequest {
  id: string;
}
