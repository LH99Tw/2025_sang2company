import axios from 'axios';
import type {
  BacktestParams,
  BacktestStatus,
  GAParams,
  ApiResponse,
  ChatMessage,
  IncubatorChatResponse,
  IncubatorMessage,
} from '../types';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:5001';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

api.defaults.withCredentials = true;

// 🏥 시스템 상태 확인
export const checkHealth = async () => {
  const response = await api.get('/api/health');
  return response.data;
};

// 📈 백테스트 API
export const runBacktest = async (params: BacktestParams): Promise<ApiResponse & { task_id?: string; status_url?: string }> => {
  const response = await api.post('/api/backtest', params, { withCredentials: true });
  return response.data;
};

export const getBacktestStatus = async (taskId: string): Promise<BacktestStatus> => {
  const response = await api.get(`/api/backtest/status/${taskId}`, { withCredentials: true });
  return response.data;
};

// 💼 포트폴리오 API
export const selectStocks = async (params: {
  alpha_factor: string;
  top_count: number;
  selection_method: string;
}) => {
  const response = await api.post('/api/portfolio/stocks', params);
  return response.data;
};

export const analyzePerformance = async (params: {
  alpha_factor: string;
  top_count: number;
  start_date: string;
  end_date: string;
  transaction_cost: number;
  rebalancing_frequency: string;
}) => {
  const response = await api.post('/api/portfolio/performance', params);
  return response.data;
};

// 🤖 AI 에이전트 API
export const sendChatMessage = async (message: string, userId: string = 'user123'): Promise<ChatMessage> => {
  const response = await api.post('/api/chat', { message, user_id: userId });
  return {
    role: 'assistant',
    content: response.data.response || response.data.message,
    timestamp: new Date(),
  };
};

// Alias for compatibility
export const chatWithAgent = async (message: string) => {
  const response = await api.post('/api/chat', { message });
  return response.data;
};

// LangChain + MCTS Incubator API
export const postIncubatorChat = async (payload: {
  message: string;
  intent?: string;
  session_id?: string;
  history?: IncubatorMessage[];
}): Promise<IncubatorChatResponse> => {
  const response = await api.post('/api/incubator/chat', payload, { withCredentials: true });
  return response.data;
};

export const fetchIncubatorSession = async (sessionId: string): Promise<IncubatorChatResponse> => {
  const response = await api.get(`/api/incubator/session/${sessionId}`, { withCredentials: true });
  return response.data;
};

// Alpha Incubator GA API
export const startGAEvolution = async (params: {
  population_size?: number;
  generations?: number;
  max_depth?: number;
}) => {
  const response = await api.post('/api/ga/run', params, { withCredentials: true });
  return response.data;
};

export const getGAEvolutionStatus = async (taskId: string) => {
  const response = await api.get(`/api/ga/status/${taskId}`, { withCredentials: true });
  return response.data;
};

export const backtestGAAlphas = async (taskId: string, params: {
  start_date?: string;
  end_date?: string;
  rebalancing_frequency?: string;
  transaction_cost?: number;
  quantile?: number;
}) => {
  const response = await api.post(`/api/ga/backtest/${taskId}`, params, { withCredentials: true });
  return response.data;
};

// 🧬 GA 알고리즘 API
export const runGA = async (params: GAParams): Promise<ApiResponse & { task_id?: string; status_url?: string }> => {
  const response = await api.post('/api/ga/run', params, { withCredentials: true });
  return response.data;
};

export const getGAStatus = async (taskId: string) => {
  const response = await api.get(`/api/ga/status/${taskId}`, { withCredentials: true });
  return response.data;
};

export const fetchUserAlphas = async () => {
  const response = await api.get('/api/user-alpha/list', { withCredentials: true });
  return response.data;
};

export const saveUserAlphas = async (alphas: Array<{ id?: string; name: string; expression: string; description?: string; tags?: string[]; fitness?: number }>) => {
  const payload = alphas.map(alpha => {
    const fitness = typeof alpha.fitness === 'number' && Number.isFinite(alpha.fitness)
      ? alpha.fitness
      : undefined;

    return {
      id: alpha.id,
      name: alpha.name,
      expression: alpha.expression,
      description: alpha.description ?? '',
      tags: alpha.tags ?? [],
      metadata: {
        fitness,
      },
    };
  });

  const response = await api.post('/api/user-alpha/save', { alphas: payload }, { withCredentials: true });
  return response.data;
};

export const deleteUserAlpha = async (alphaId: string) => {
  const response = await api.delete(`/api/user-alpha/delete/${alphaId}`, { withCredentials: true });
  return response.data;
};

// 📊 데이터 API
export const getFactorsList = async () => {
  const response = await api.get('/api/data/factors');
  return response.data;
};

export const getDataStats = async () => {
  const response = await api.get('/api/data/stats');
  return response.data;
};

export const getTickerList = async () => {
  const response = await api.get('/api/data/ticker-list');
  return response.data;
};

export const getTickerPerformance = async (params: {
  tickers: string[];
  start_date?: string;
  end_date?: string;
}) => {
  const response = await api.post('/api/data/ticker-performance', params);
  return response.data;
};

export default api;
