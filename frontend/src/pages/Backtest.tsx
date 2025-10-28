import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import styled from 'styled-components';
import { GlassCard } from '../components/common/GlassCard';
import { GlassButton } from '../components/common/GlassButton';
import { GlassInput } from '../components/common/GlassInput';
import { Select, DatePicker, message, Progress, Tag } from 'antd';
import { PlayCircleOutlined, ReloadOutlined } from '@ant-design/icons';
import { theme } from '../styles/theme';
import { runBacktest, getBacktestStatus, fetchUserAlphas } from '../services/api';
import type { BacktestParams, BacktestStatus, BacktestResult } from '../types';
import dayjs from 'dayjs';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from 'recharts';

const { RangePicker } = DatePicker;
const BACKTEST_TASK_KEY = 'backtestTaskId';

type FactorOption = { label: string; value: string };

type OptionGroup = { label: string; options: FactorOption[] };

const PageWrapper = styled.div`
  display: flex;
  flex-direction: column;
  min-height: calc(100vh - 120px);
  padding-bottom: ${theme.spacing.xl};
`;

const BacktestContainer = styled.div`
  display: flex;
  flex-direction: column;
  gap: ${theme.spacing.xl};
  flex: 1;
`;

const FormGrid = styled.div`
  display: grid;
  grid-template-columns:
    minmax(220px, 3.5fr)
    minmax(200px, 3fr)
    minmax(170px, 1.7fr)
    minmax(120px, 1.2fr)
    minmax(120px, 1.2fr)
    minmax(120px, 1.4fr);
  column-gap: ${theme.spacing.sm};
  row-gap: ${theme.spacing.sm};
  align-items: end;
`;

const ControlCard = styled(GlassCard)`
  display: flex;
  flex-direction: column;
  gap: ${theme.spacing.sm};
  padding: ${theme.spacing.sm} ${theme.spacing.md};
`;

const Label = styled.label`
  display: flex;
  align-items: flex-end;
  color: ${theme.colors.textSecondary};
  font-size: ${theme.typography.fontSize.caption};
  font-weight: 600;
  line-height: 1;
  margin-bottom: 2px;
  min-height: 18px;
  white-space: nowrap;
`;

const StyledSelect = styled(Select)`
  .ant-select-selector {
    background: ${theme.colors.liquidGlass} !important;
    border: 1px solid ${theme.colors.liquidGlassBorder} !important;
    color: ${theme.colors.textPrimary} !important;
    height: 38px !important;
    border-radius: 8px !important;
    padding: 0 ${theme.spacing.sm} !important;
    display: flex !important;
    align-items: center !important;
  }

  .ant-select-selection-item {
    color: ${theme.colors.textPrimary} !important;
    font-size: 13px;
    line-height: 18px !important;
  }

  .ant-select-selection-placeholder {
    color: ${theme.colors.textSecondary} !important;
    font-size: 13px;
  }

  .ant-select-selection-overflow {
    align-items: center;
  }
`;

const StyledRangePicker = styled(RangePicker)`
  background: ${theme.colors.liquidGlass} !important;
  border: 1px solid ${theme.colors.liquidGlassBorder} !important;
  width: 100%;
  height: 38px;
  border-radius: 8px;
  padding: 6px ${theme.spacing.sm};
  
  input {
    color: ${theme.colors.textPrimary} !important;
    font-size: 13px;
  }

  .ant-picker-input {
    display: flex;
    align-items: center;
  }

  .ant-picker-suffix {
    color: ${theme.colors.textSecondary};
  }
`;

const ResultCard = styled(GlassCard)`
  margin-bottom: ${theme.spacing.lg};
`;

const ResultTitle = styled.h3`
  font-size: ${theme.typography.fontSize.h3};
  color: ${theme.colors.textPrimary};
  margin: 0 0 ${theme.spacing.lg} 0;
  font-weight: 600;
`;

const MetricRow = styled.div`
  display: flex;
  justify-content: space-between;
  padding: ${theme.spacing.md} 0;
  border-bottom: 1px solid ${theme.colors.liquidGlassBorder};

  &:last-child {
    border-bottom: none;
  }
`;

const MetricLabel = styled.span`
  color: ${theme.colors.textSecondary};
`;

const MetricValue = styled.span<{ $positive?: boolean }>`
  color: ${(props: { $positive?: boolean }) =>
    props.$positive !== undefined
      ? (props.$positive ? theme.colors.success : theme.colors.error)
      : theme.colors.textPrimary};
  font-weight: 600;
  font-family: ${theme.typography.fontFamily.display};
`;

const StatusCard = styled(GlassCard)`
  display: flex;
  flex-direction: column;
  gap: ${theme.spacing.sm};
`;

const StatusHeader = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
`;

const StatusTitle = styled.h3`
  margin: 0;
  font-size: ${theme.typography.fontSize.h4};
  color: ${theme.colors.textPrimary};
  font-weight: 600;
`;

const StatusMeta = styled.span`
  color: ${theme.colors.textSecondary};
  font-size: ${theme.typography.fontSize.caption};
`;

const LogList = styled.ul`
  list-style: none;
  margin: 0;
  padding: 0;
  max-height: 160px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: ${theme.spacing.xs};

  li {
    color: ${theme.colors.textSecondary};
    font-size: ${theme.typography.fontSize.caption};
    padding: ${theme.spacing.xs} ${theme.spacing.sm};
    background: ${theme.colors.liquidGlass};
    border-radius: ${theme.borderRadius.sm};
  }
`;

const EmptyLogs = styled.div`
  color: ${theme.colors.textSecondary};
  font-size: ${theme.typography.fontSize.caption};
`;

const PlaceholderText = styled.p`
  color: ${theme.colors.textSecondary};
  text-align: center;
  margin: 0;
`;

const ChartContainer = styled.div`
  height: 220px;
  margin-bottom: ${theme.spacing.lg};
  padding: ${theme.spacing.md};
  background: ${theme.colors.backgroundSecondary};
  border: 1px solid ${theme.colors.liquidGlassBorder};
  border-radius: ${theme.borderRadius.lg};
`;

const ActionRow = styled.div`
  display: flex;
  gap: ${theme.spacing.sm};
  margin-top: 0;
  height: 40px;
  justify-content: flex-end;

  .backtest-action-button {
    flex: 0 0 48px;
    width: 48px;
    height: 40px;
    padding: 0;
  }
`;

const Field = styled.div`
  display: flex;
  flex-direction: column;
  gap: 2px;
  justify-content: flex-start;
  height: 100%;
  width: 100%;
`;

const HiddenLabel = styled(Label)`
  visibility: hidden;
  margin-bottom: 0;
`;

const SrOnly = styled.span`
  border: 0;
  clip: rect(0 0 0 0);
  height: 1px;
  margin: -1px;
  overflow: hidden;
  padding: 0;
  position: absolute;
  width: 1px;
`;

const CompactInput = styled(GlassInput)`
  input {
    height: 38px;
    border-radius: 8px;
    padding: 8px ${theme.spacing.sm};
    font-size: 13px;
  }
`;

const CardHeader = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: ${theme.spacing.sm};
`;

const CardTitle = styled.h2`
  margin: 0;
  font-size: ${theme.typography.fontSize.h4};
  color: ${theme.colors.textPrimary};
  font-weight: 600;
`;

const CardSubtitle = styled.span`
  color: ${theme.colors.textSecondary};
  font-size: ${theme.typography.fontSize.caption};
`;

const ResultsWrapper = styled.div`
  display: flex;
  flex-direction: column;
  gap: ${theme.spacing.lg};
`;

const DEFAULT_BACKTEST_PARAMS: BacktestParams = {
  start_date: '2020-01-01',
  end_date: '2024-12-31',
  factors: [],
  rebalancing_frequency: 'weekly',
  transaction_cost: 0.001,
  quantile: 0.1,
};

const BacktestPage: React.FC = () => {
  const [params, setParams] = useState<BacktestParams>({ ...DEFAULT_BACKTEST_PARAMS });

  const [loading, setLoading] = useState(false);
  const [statusInfo, setStatusInfo] = useState<BacktestStatus | null>(null);
  const [results, setResults] = useState<Record<string, BacktestResult> | null>(null);
  const [alphaOptions, setAlphaOptions] = useState<{ shared: FactorOption[]; private: FactorOption[] }>({
    shared: [],
    private: [],
  });
  const [optionsLoading, setOptionsLoading] = useState(true);
  const pollingRef = useRef<NodeJS.Timeout | null>(null);
  const [activeTaskId, setActiveTaskId] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    const loadAlphas = async () => {
      setOptionsLoading(true);
      try {
        const data = await fetchUserAlphas();
        const shared = (data?.shared_alphas || []).map((alpha: any) => ({
          label: alpha.name || alpha.id,
          value: alpha.name || alpha.id,
        }));
        const personal = (data?.private_alphas || []).map((alpha: any) => ({
          label: alpha.name || alpha.id,
          value: alpha.name || alpha.id,
        }));
        if (mounted) {
          setAlphaOptions({ shared, private: personal });
        }
      } catch (error) {
        console.error('알파 목록 조회 실패:', error);
        if (mounted) {
          message.error('알파 목록을 불러오지 못했습니다');
        }
      } finally {
        if (mounted) {
          setOptionsLoading(false);
        }
      }
    };
    loadAlphas();
    return () => {
      mounted = false;
    };
  }, []);

  const groupedOptions: OptionGroup[] = useMemo(() => {
    const groups: OptionGroup[] = [];
    if (alphaOptions.shared.length) {
      groups.push({ label: `공용 알파 (${alphaOptions.shared.length})`, options: alphaOptions.shared });
    }
    if (alphaOptions.private.length) {
      groups.push({ label: `개인 알파 (${alphaOptions.private.length})`, options: alphaOptions.private });
    }
    return groups.length ? groups : [{ label: '사용 가능한 알파 없음', options: [] }];
  }, [alphaOptions]);

  const stopPolling = () => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }
  };

  const handleStatusUpdate = (status: BacktestStatus, taskId: string) => {
    const snapshot = status.logs ? { ...status, logs: [...status.logs] } : status;
    setStatusInfo(snapshot);

    if (status.status === 'completed') {
      setResults(status.results || null);
      setLoading(false);
      message.success('백테스트가 완료되었습니다');
      stopPolling();
      sessionStorage.removeItem(BACKTEST_TASK_KEY);
      setActiveTaskId(null);
    } else if (status.status === 'failed') {
      setLoading(false);
      message.error(status.error || '백테스트가 실패했습니다');
      stopPolling();
      sessionStorage.removeItem(BACKTEST_TASK_KEY);
      setActiveTaskId(null);
    } else {
      setActiveTaskId(taskId);
    }
  };

  const pollBacktestStatus = (taskId: string) => {
    sessionStorage.setItem(BACKTEST_TASK_KEY, taskId);
    setActiveTaskId(taskId);

    const fetchStatus = async () => {
      try {
        const status = await getBacktestStatus(taskId);
        handleStatusUpdate(status, taskId);
      } catch (error) {
        console.error('백테스트 상태 조회 실패:', error);
      }
    };

    stopPolling();
    fetchStatus();
    pollingRef.current = setInterval(fetchStatus, 2000);
  };

  useEffect(() => {
    const existingTaskId = sessionStorage.getItem(BACKTEST_TASK_KEY);
    if (existingTaskId) {
      pollBacktestStatus(existingTaskId);
    }
    return () => stopPolling();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleRunBacktest = async () => {
    if (params.factors.length === 0) {
      message.error('알파 팩터를 선택해주세요');
      return;
    }

    setLoading(true);
    setResults(null);
    setStatusInfo({ status: 'running', progress: 0 });
    try {
      const payload = { ...params, max_factors: Math.max(1, params.factors.length) };
      const response = await runBacktest(payload);
      const taskId = (response as { task_id?: string }).task_id || (response.data as any)?.task_id;
      if (response.success && taskId) {
        message.success('백테스트가 시작되었습니다');
        pollBacktestStatus(taskId);
      }
    } catch (error) {
      message.error('백테스트 실행 중 오류가 발생했습니다');
      setLoading(false);
    }
  };

  const handleResetParams = useCallback(() => {
    setParams({ ...DEFAULT_BACKTEST_PARAMS, factors: [] });
    setResults(null);
    setStatusInfo(null);
    setActiveTaskId(null);
  }, []);

  return (
    <PageWrapper>
      <BacktestContainer>
        <ControlCard>
          <CardHeader>
            <CardTitle>전략 설정</CardTitle>
            <CardSubtitle>필수 파라미터를 입력한 뒤 백테스트를 실행하세요.</CardSubtitle>
          </CardHeader>
          <FormGrid>
            <Field>
              <Label>알파 팩터</Label>
              <StyledSelect
                mode="multiple"
                placeholder="알파 팩터 선택"
                value={params.factors}
                loading={optionsLoading}
                optionFilterProp="label"
                filterOption={(input, option) => (option?.label ?? '').toLowerCase().includes(input.toLowerCase())}
                notFoundContent={optionsLoading ? '알파 목록을 불러오는 중...' : '사용 가능한 알파가 없습니다'}
                options={groupedOptions}
                onChange={(value) => setParams({ ...params, factors: value as string[] })}
              />
            </Field>

            <Field>
              <Label>기간</Label>
              <StyledRangePicker
                value={[dayjs(params.start_date), dayjs(params.end_date)]}
                onChange={(dates) => {
                  if (dates) {
                    setParams({
                      ...params,
                      start_date: dates[0]?.format('YYYY-MM-DD') || '',
                      end_date: dates[1]?.format('YYYY-MM-DD') || '',
                    });
                  }
                }}
              />
            </Field>

            <Field>
              <Label>리밸런싱 주기</Label>
              <StyledSelect
                value={params.rebalancing_frequency}
                onChange={(value) => setParams({ ...params, rebalancing_frequency: value as 'daily' | 'weekly' | 'monthly' | 'quarterly' })}
                options={[
                  { value: 'daily', label: '일간' },
                  { value: 'weekly', label: '주간' },
                  { value: 'monthly', label: '월간' },
                  { value: 'quarterly', label: '분기' },
                ]}
              />
            </Field>

            <Field>
              <Label>거래비용 (%)</Label>
              <CompactInput
                type="number"
                value={params.transaction_cost * 100}
                min={0}
                step={0.01}
                onChange={(e) => setParams({
                  ...params,
                  transaction_cost: Number(e.target.value) / 100,
                })}
              />
            </Field>

            <Field>
              <Label>분위수</Label>
              <CompactInput
                type="number"
                value={params.quantile}
                min={0.01}
                max={0.5}
                step={0.01}
                onChange={(e) => setParams({
                  ...params,
                  quantile: Number(e.target.value),
                })}
              />
            </Field>

            <Field>
              <HiddenLabel>액션 버튼</HiddenLabel>
              <ActionRow>
                <GlassButton
                  variant="secondary"
                  onClick={handleResetParams}
                  disabled={loading}
                  icon={<ReloadOutlined />}
                  className="backtest-action-button"
                >
                  <SrOnly>설정 초기화</SrOnly>
                </GlassButton>
                <GlassButton
                  variant="primary"
                  onClick={handleRunBacktest}
                  loading={loading}
                  disabled={loading}
                  icon={<PlayCircleOutlined />}
                  className="backtest-action-button"
                >
                  <SrOnly>백테스트 실행</SrOnly>
                </GlassButton>
              </ActionRow>
            </Field>
          </FormGrid>
        </ControlCard>

        <StatusCard>
          <StatusHeader>
            <StatusTitle>백테스트 진행 상태</StatusTitle>
              <StatusMeta>
                {statusInfo?.status === 'completed' && <Tag color="success">완료</Tag>}
                {statusInfo?.status === 'failed' && <Tag color="error">실패</Tag>}
                {statusInfo?.status === 'running' && <Tag color="processing">진행 중</Tag>}
                {!statusInfo && <Tag>대기 중</Tag>}
              </StatusMeta>
            </StatusHeader>

            <Progress
              percent={Math.round(statusInfo?.progress ?? 0)}
              status={statusInfo?.status === 'failed' ? 'exception' : statusInfo?.status === 'completed' ? 'success' : 'active'}
              strokeColor={{ '0%': theme.colors.accentPrimary, '100%': theme.colors.accentGold }}
            />

            <StatusMeta>
              {activeTaskId ? `작업 ID: ${activeTaskId}` : '진행 중인 작업이 없습니다'}
            </StatusMeta>

            <StatusTitle as="h4">최근 로그</StatusTitle>
            {statusInfo?.logs && statusInfo.logs.length > 0 ? (
              <LogList>
                {statusInfo.logs.slice(-6).reverse().map((log, index) => (
                  <li key={`${log}-${index}`}>{log}</li>
                ))}
              </LogList>
            ) : (
              <EmptyLogs>표시할 로그가 없습니다.</EmptyLogs>
            )}
          </StatusCard>

        <ResultsWrapper>
          {statusInfo?.status === 'running' && (
            <ResultCard>
              <ResultTitle>백테스트가 진행 중입니다</ResultTitle>
              <MetricLabel>결과가 준비되면 자동으로 표시됩니다.</MetricLabel>
            </ResultCard>
          )}

          {results && Object.keys(results).length > 0 && (
            <>
              {Object.entries(results).map(([factor, result]) => {
                const displayFactor = factor.toUpperCase();
                return (
                  <ResultCard key={factor}>
                    <ResultTitle>{displayFactor} 결과</ResultTitle>
                    {result.cumulative_returns && result.cumulative_returns.length > 0 && (
                      <ChartContainer>
                        <ResponsiveContainer width="100%" height="100%">
                          <LineChart data={result.cumulative_returns}>
                            <CartesianGrid stroke="rgba(255, 255, 255, 0.05)" strokeDasharray="3 3" />
                            <XAxis
                              dataKey="date"
                              tick={{ fill: theme.colors.textSecondary }}
                              minTickGap={30}
                            />
                            <YAxis
                              tick={{ fill: theme.colors.textSecondary }}
                              tickFormatter={(value) => `${(value * 100).toFixed(1)}%`}
                            />
                            <Tooltip
                              formatter={(value: number) => `${(value as number * 100).toFixed(2)}%`}
                              labelFormatter={(label: string) => `날짜: ${label}`}
                            />
                            <Line type="monotone" dataKey="value" stroke={theme.colors.accentPrimary} dot={false} />
                          </LineChart>
                        </ResponsiveContainer>
                      </ChartContainer>
                    )}
                    <MetricRow>
                      <MetricLabel>연평균 수익률 (CAGR)</MetricLabel>
                      <MetricValue $positive={result.cagr > 0}>
                        {(result.cagr * 100).toFixed(2)}%
                      </MetricValue>
                    </MetricRow>
                    <MetricRow>
                      <MetricLabel>샤프 지수</MetricLabel>
                      <MetricValue $positive={result.sharpe_ratio > 0}>
                        {result.sharpe_ratio.toFixed(2)}
                      </MetricValue>
                    </MetricRow>
                    <MetricRow>
                      <MetricLabel>최대 낙폭 (MDD)</MetricLabel>
                      <MetricValue $positive={result.max_drawdown > -0.1}>
                        {(result.max_drawdown * 100).toFixed(2)}%
                      </MetricValue>
                    </MetricRow>
                    <MetricRow>
                      <MetricLabel>정보 계수 (IC)</MetricLabel>
                      <MetricValue $positive={result.ic_mean > 0}>
                        {result.ic_mean.toFixed(3)}
                      </MetricValue>
                    </MetricRow>
                    <MetricRow>
                      <MetricLabel>승률</MetricLabel>
                      <MetricValue $positive={result.win_rate > 0.5}>
                        {(result.win_rate * 100).toFixed(2)}%
                      </MetricValue>
                    </MetricRow>
                    <MetricRow>
                      <MetricLabel>연간 변동성</MetricLabel>
                      <MetricValue>
                        {(result.volatility * 100).toFixed(2)}%
                      </MetricValue>
                    </MetricRow>
                  </ResultCard>
                );
              })}
            </>
          )}

          {(!results || Object.keys(results).length === 0) && statusInfo?.status !== 'running' && (
            <ResultCard>
              <ResultTitle>백테스트 안내</ResultTitle>
              <PlaceholderText>
                공용 또는 개인 알파를 선택해 백테스트를 실행하면 결과가 이 영역에 표시됩니다.
              </PlaceholderText>
            </ResultCard>
          )}
        </ResultsWrapper>
      </BacktestContainer>
    </PageWrapper>
  );
};

export const Backtest = BacktestPage;
export default BacktestPage;
