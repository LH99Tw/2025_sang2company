import React, { useEffect, useMemo, useState } from 'react';
import styled from 'styled-components';
import {
  DatePicker,
  Empty,
  InputNumber,
  message,
  Radio,
  Select,
  Slider,
  Space,
  Spin,
  Switch,
  Table,
  Tag,
  Tooltip,
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import dayjs, { Dayjs } from 'dayjs';
import {
  ThunderboltOutlined,
  FundOutlined,
  BarChartOutlined,
  FilterOutlined,
} from '@ant-design/icons';
import { GlassCard } from '../components/common/GlassCard';
import { GlassButton } from '../components/common/GlassButton';
import { theme } from '../styles/theme';
import { getFactorsList, selectStocks, type AlphaPortfolioParams } from '../services/api';
import type {
  AlphaFactorMetadata,
  AlphaPortfolioResponse,
  AlphaPortfolioStockResult,
} from '../types';
import axios from 'axios';

const { Option } = Select;

const PageContainer = styled.div`
  display: flex;
  flex-direction: column;
  gap: ${theme.spacing.xl};
`;

const FormGroup = styled.div`
  display: flex;
  flex-direction: column;
  gap: ${theme.spacing.sm};
`;

const Label = styled.label`
  color: ${theme.colors.textSecondary};
  font-size: ${theme.typography.fontSize.caption};
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  display: flex;
  align-items: center;
  gap: 6px;
`;

const InlineNote = styled.span`
  color: ${theme.colors.textSecondary};
  font-size: ${theme.typography.fontSize.caption};
`;

const SliderContainer = styled.div`
  display: flex;
  flex-direction: column;
  gap: ${theme.spacing.sm};
`;

const SliderRow = styled.div`
  display: flex;
  align-items: center;
  gap: ${theme.spacing.sm};
`;

const SliderLabel = styled.div`
  flex: 0 0 120px;
  display: flex;
  flex-direction: column;
  color: ${theme.colors.textPrimary};
  font-weight: 600;
  font-size: ${theme.typography.fontSize.body};
`;

const SliderWeight = styled.span`
  color: ${theme.colors.textSecondary};
  font-size: ${theme.typography.fontSize.caption};
  font-weight: 500;
`;

const WeightSlider = styled(Slider)`
  flex: 1;

  .ant-slider-track {
    background: ${theme.colors.accentGold} !important;
  }

  .ant-slider-handle::after {
    box-shadow: 0 0 0 2px rgba(212, 175, 55, 0.45) !important;
  }
`;

const ControlPanel = styled(GlassCard)`
  display: flex;
  flex-direction: column;
  gap: ${theme.spacing.md};
  padding: ${theme.spacing.md} ${theme.spacing.lg};
`;

const ControlBar = styled.div`
  display: flex;
  align-items: flex-end;
  gap: ${theme.spacing.sm};
  flex-wrap: nowrap;
  overflow-x: auto;
  padding-bottom: ${theme.spacing.xs};
`;

const ControlField = styled.div`
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 140px;
`;

const ControlLabel = styled.span`
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: ${theme.colors.textSecondary};
  font-size: ${theme.typography.fontSize.caption};
  font-weight: 600;
  letter-spacing: 0.05em;
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

const ControlActionField = styled.div`
  display: flex;
  align-items: flex-end;
  justify-content: flex-end;
  flex-shrink: 0;
`;

const CompactSelect = styled(Select)`
  width: 100%;

  .ant-select-selector {
    background: ${theme.colors.liquidGlass} !important;
    border: 1px solid ${theme.colors.liquidGlassBorder} !important;
    border-radius: 10px !important;
    min-height: 38px !important;
    padding: 4px ${theme.spacing.sm} !important;
    display: flex !important;
    align-items: center !important;
  }

  .ant-select-selection-item {
    display: flex;
    align-items: center;
    color: ${theme.colors.textPrimary};
    font-size: 13px;
  }

  .ant-select-selection-placeholder {
    color: ${theme.colors.textSecondary};
    font-size: 13px;
  }

  &.ant-select-focused .ant-select-selector,
  .ant-select-selector:hover {
    border-color: ${theme.colors.accentGold} !important;
  }
`;

const CompactDatePicker = styled(DatePicker)`
  width: 100%;
  height: 38px;

  .ant-picker-input > input {
    font-size: 13px;
    color: ${theme.colors.textPrimary};
  }

  .ant-picker-input {
    display: flex;
    align-items: center;
  }

  .ant-picker-suffix {
    color: ${theme.colors.textSecondary};
  }

  &.ant-picker-focused,
  &:hover {
    border-color: ${theme.colors.accentGold};
  }
`;

const CompactInputNumber = styled(InputNumber)`
  width: 100%;
  height: 38px;
  border-radius: 10px;

  .ant-input-number-input {
    height: 38px;
    padding: 0 ${theme.spacing.sm};
    font-size: 13px;
  }

  &.ant-input-number-focused,
  &:hover {
    border-color: ${theme.colors.accentGold} !important;
  }
`;

const CompactRadioGroup = styled(Radio.Group)`
  display: inline-flex;
  align-items: center;
  height: 38px;

  .ant-radio-button-wrapper {
    height: 38px;
    line-height: 38px;
    padding: 0 12px;
    font-size: 13px;
    border: 1px solid ${theme.colors.liquidGlassBorder};
    background: ${theme.colors.liquidGlass};
    color: ${theme.colors.textSecondary};
  }

  .ant-radio-button-wrapper:not(:first-child)::before {
    display: none;
  }

  .ant-radio-button-wrapper-checked,
  .ant-radio-button-wrapper-checked:hover {
    background: ${theme.colors.accentGold};
    border-color: ${theme.colors.accentGold};
    color: ${theme.colors.textPrimary};
  }
`;

const SwitchRow = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 10px;
  border: 1px solid ${theme.colors.liquidGlassBorder};
  border-radius: 10px;
  background: ${theme.colors.liquidGlass};
  min-height: 38px;
`;

const CompactSwitch = styled(Switch)`
  &.ant-switch-checked {
    background: ${theme.colors.accentGold};
  }
`;

const ResultsContainer = styled.div`
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: ${theme.spacing.lg};
  min-width: 520px;
`;

const SummaryGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: ${theme.spacing.lg};
`;

const SummaryCard = styled(GlassCard)`
  display: flex;
  flex-direction: column;
  gap: ${theme.spacing.sm};
`;

const SummaryHeader = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
`;

const SummaryTitle = styled.span`
  color: ${theme.colors.textSecondary};
  font-size: ${theme.typography.fontSize.caption};
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
`;

const SummaryValue = styled.span`
  font-size: ${theme.typography.fontSize.h3};
  font-weight: 700;
  color: ${theme.colors.textPrimary};
  font-family: ${theme.typography.fontFamily.display};
`;

const SummarySubtitle = styled.span`
  color: ${theme.colors.textSecondary};
  font-size: ${theme.typography.fontSize.body};
`;

const ResultsCard = styled(GlassCard)`
  display: flex;
  flex-direction: column;
  gap: ${theme.spacing.lg};

  .ant-table {
    background: transparent !important;
  }

  .ant-table-thead > tr > th {
    background: ${theme.colors.liquidGlass} !important;
    border-bottom: 1px solid ${theme.colors.border} !important;
    color: ${theme.colors.textSecondary} !important;
    font-weight: 600;
  }

  .ant-table-tbody > tr > td {
    background: transparent !important;
    border-bottom: 1px solid ${theme.colors.liquidGlassBorder} !important;
    color: ${theme.colors.textPrimary} !important;
  }

  .ant-table-tbody > tr:hover > td {
    background: ${theme.colors.liquidGlassHover} !important;
  }
`;

interface NormalizedWeights {
  [factor: string]: number;
}

const computeSoftmax = (selected: string[], weights: Record<string, number>): NormalizedWeights => {
  if (selected.length === 0) return {};
  const rawValues = selected.map(factor => Number.isFinite(weights[factor]) ? weights[factor] : 1);
  const maxVal = Math.max(...rawValues);
  const exps = rawValues.map(value => Math.exp(value - maxVal));
  const sumExps = exps.reduce((acc, value) => acc + value, 0);
  if (!Number.isFinite(sumExps) || sumExps === 0) {
    const equal = 1 / selected.length;
    return selected.reduce<NormalizedWeights>((acc, factor) => {
      acc[factor] = equal;
      return acc;
    }, {});
  }
  return selected.reduce<NormalizedWeights>((acc, factor, idx) => {
    acc[factor] = exps[idx] / sumExps;
    return acc;
  }, {});
};

const formatPercent = (value?: number | null) => {
  if (value === undefined || value === null || Number.isNaN(value)) return '-';
  return `${(value * 100).toFixed(1)}%`;
};

const formatScore = (value?: number | null) => {
  if (value === undefined || value === null || Number.isNaN(value)) return '-';
  return value.toFixed(4);
};

export const Portfolio: React.FC = () => {
  const [factorsLoading, setFactorsLoading] = useState(false);
  const [generateLoading, setGenerateLoading] = useState(false);
  const [factorList, setFactorList] = useState<AlphaFactorMetadata[]>([]);
  const [selectedFactors, setSelectedFactors] = useState<string[]>([]);
  const [factorWeights, setFactorWeights] = useState<Record<string, number>>({});
  const [asOfDate, setAsOfDate] = useState<Dayjs | null>(dayjs());
  const [selectionMode, setSelectionMode] = useState<'count' | 'percentage'>('count');
  const [topCount, setTopCount] = useState<number>(10);
  const [topPercentage, setTopPercentage] = useState<number>(10);
  const [includeBreakdown, setIncludeBreakdown] = useState<boolean>(true);
  const [result, setResult] = useState<AlphaPortfolioResponse | null>(null);

  useEffect(() => {
    const loadFactors = async () => {
      setFactorsLoading(true);
      try {
        const data = await getFactorsList();
        const metadata = Array.isArray(data.metadata) ? data.metadata : [];
        metadata.sort((a, b) => a.name.localeCompare(b.name));
        setFactorList(metadata);
      } catch (error) {
        console.error('알파 목록 로드 실패:', error);
        message.error('알파 목록을 불러오지 못했습니다.');
      } finally {
        setFactorsLoading(false);
      }
    };

    loadFactors();
  }, []);

  const normalizedWeights = useMemo(
    () => computeSoftmax(selectedFactors, factorWeights),
    [selectedFactors, factorWeights],
  );

  const factorOptions = useMemo(
    () =>
      factorList.map(meta => ({
        value: meta.name,
        label: meta.name,
      })),
    [factorList],
  );

const handleFactorsChange = (values: string[]) => {
  setSelectedFactors(values);
  setFactorWeights(prev => {
    const next: Record<string, number> = {};
    values.forEach(value => {
      next[value] = Number.isFinite(prev[value]) ? prev[value] : 1;
    });
    return next;
  });
};

  const handleWeightChange = (factor: string, value: number) => {
    setFactorWeights(prev => ({
      ...prev,
      [factor]: value,
    }));
  };

  const columns: ColumnsType<AlphaPortfolioStockResult> = useMemo(
    () => [
      {
        title: '순위',
        dataIndex: 'rank',
        key: 'rank',
        width: 80,
        align: 'center',
      },
      {
        title: '종목',
        dataIndex: 'ticker',
        key: 'ticker',
        render: (ticker: string) => (
          <span style={{ fontWeight: 600, color: theme.colors.textPrimary }}>{ticker}</span>
        ),
      },
      {
        title: 'Composite Score',
        dataIndex: 'composite_score',
        key: 'composite_score',
        align: 'right',
        render: (value: number | null) => (
          <span style={{ fontFamily: theme.typography.fontFamily.display }}>
            {formatScore(value)}
          </span>
        ),
      },
      {
        title: '종가',
        dataIndex: 'close',
        key: 'close',
        align: 'right',
        render: (value: number | null | undefined) =>
          value !== undefined && value !== null ? value.toFixed(2) : '-',
      },
      {
        title: '알파 기여도',
        key: 'factors',
        render: (_: unknown, record: AlphaPortfolioStockResult) => {
          if (!record.factors || record.factors.length === 0) {
            return <InlineNote>상세 정보 미포함</InlineNote>;
          }

          return (
            <Space wrap size={6}>
              {record.factors.map(factor => (
                <Tooltip
                  key={`${record.ticker}-${factor.name}`}
                  title={
                    <div>
                      <div>{factor.description || '설명 없음'}</div>
                      <div>Percentile: {formatPercent(factor.rank)}</div>
                      <div>Value: {factor.value !== null ? factor.value.toFixed(4) : '-'}</div>
                      <div>Weight: {formatPercent(factor.weight ?? normalizedWeights[factor.name] ?? 0)}</div>
                    </div>
                  }
                >
                  <Tag color="gold" style={{ marginBottom: 4 }}>
                    {factor.name}
                    <span style={{ marginLeft: 6, fontWeight: 600 }}>
                      {formatPercent(factor.weight ?? normalizedWeights[factor.name] ?? 0)}
                    </span>
                  </Tag>
                </Tooltip>
              ))}
            </Space>
          );
        },
      },
    ],
    [normalizedWeights],
  );

  const handleGenerate = async () => {
    if (selectedFactors.length === 0) {
      message.warning('알파를 최소 한 개 이상 선택해주세요.');
      return;
    }

    const nonZero = selectedFactors.some(factor => (factorWeights[factor] ?? 0) !== 0);
    if (!nonZero) {
      message.warning('모든 알파 가중치가 0입니다. 슬라이더를 조정해주세요.');
      return;
    }

    const payload: AlphaPortfolioParams = {
      alpha_factors: selectedFactors,
      alpha_weights: selectedFactors.reduce<Record<string, number>>((acc, factor) => {
        acc[factor] = Number.isFinite(factorWeights[factor]) ? factorWeights[factor] : 1;
        return acc;
      }, {}),
      selection_method: selectionMode,
      include_breakdown: includeBreakdown,
    };

    if (selectionMode === 'count') {
      payload.top_count = topCount;
    } else {
      payload.top_percentage = topPercentage;
    }

    if (asOfDate) {
      payload.as_of_date = asOfDate.format('YYYY-MM-DD');
    }

    setGenerateLoading(true);
    try {
      const response = await selectStocks(payload);
      setResult(response);
      if (response.missing_factors && response.missing_factors.length) {
        message.warning(`일부 알파는 데이터에 없어 제외되었습니다: ${response.missing_factors.join(', ')}`);
      } else {
        message.success('알파 포트폴리오가 생성되었습니다.');
      }
    } catch (error) {
      console.error('알파 포트폴리오 생성 실패:', error);
      if (axios.isAxiosError(error) && error.response?.data?.error) {
        message.error(error.response.data.error);
      } else {
        message.error('포트폴리오 생성을 실패했습니다. 설정을 확인해주세요.');
      }
    } finally {
      setGenerateLoading(false);
    }
  };

  return (
    <PageContainer>
      <ControlPanel>
        <ControlBar>
          <ControlField style={{ minWidth: 140, maxWidth: 180 }}>
            <ControlLabel>
              <FilterOutlined style={{ marginRight: 4 }} />
              알파 선택
            </ControlLabel>
            <CompactSelect
              mode="multiple"
              allowClear
              showSearch
              placeholder="알파를 선택하세요"
              onChange={(value) => handleFactorsChange(value as string[])}
              value={selectedFactors}
              loading={factorsLoading}
              optionFilterProp="value"
              style={{ width: '100%' }}
            >
              {factorOptions.map(option => (
                <Option key={option.value} value={option.value}>
                  {option.label}
                </Option>
              ))}
            </CompactSelect>
            
          </ControlField>

          <ControlField style={{ minWidth: 160 }}>
            <ControlLabel>평가 시점</ControlLabel>
            <CompactDatePicker
              value={asOfDate}
              onChange={(value) =>
                setAsOfDate(Array.isArray(value) ? (value[0] ?? null) : value ?? null)
              }
              allowClear
            />
          </ControlField>

          <ControlField style={{ minWidth: 150 }}>
            <ControlLabel>선별 기준</ControlLabel>
            <CompactRadioGroup
              value={selectionMode}
              onChange={event => setSelectionMode(event.target.value)}
              buttonStyle="solid"
            >
              <Radio.Button value="percentage">퍼센트</Radio.Button>
              <Radio.Button value="count">개수</Radio.Button>
            </CompactRadioGroup>
          </ControlField>

          <ControlField style={{ minWidth: 140 }}>
            <ControlLabel>{selectionMode === 'percentage' ? '상위 퍼센트 (%)' : '상위 종목 수'}</ControlLabel>
            <CompactInputNumber
              min={selectionMode === 'percentage' ? 1 : 1}
              max={selectionMode === 'percentage' ? 100 : 500}
              value={selectionMode === 'percentage' ? topPercentage : topCount}
              onChange={value => {
                const next = Number(value ?? 1);
                if (selectionMode === 'percentage') {
                  setTopPercentage(Math.min(Math.max(next, 1), 100));
                } else {
                  setTopCount(Math.min(Math.max(next, 1), 500));
                }
              }}
            />
          </ControlField>

          <ControlField style={{ minWidth: 140 }}>
            <ControlLabel>상세 팩터 정보</ControlLabel>
            <SwitchRow>
              <span style={{ fontSize: 12, color: theme.colors.textSecondary }}>
                {includeBreakdown ? '표시' : '숨김'}
              </span>
              <CompactSwitch
                checked={includeBreakdown}
                onChange={checked => setIncludeBreakdown(checked)}
              />
            </SwitchRow>
          </ControlField>

          <ControlActionField>
              <GlassButton
                icon={<ThunderboltOutlined />}
                onClick={handleGenerate}
                loading={generateLoading}
                disabled={factorsLoading}
                style={{ height: 40, width: 44, padding: 0 }}
              >
                <SrOnly>포트폴리오 생성</SrOnly>
              </GlassButton>
          </ControlActionField>
        </ControlBar>

        {selectedFactors.length > 0 && (
          <SliderContainer>
            {selectedFactors.map(factor => (
              <SliderRow key={factor}>
                <SliderLabel>
                  <span>{factor}</span>
                  <SliderWeight>
                    비중 {formatPercent(normalizedWeights[factor])}
                  </SliderWeight>
                </SliderLabel>
                <WeightSlider
                  max={10}
                  min={0}
                  step={0.1}
                  value={factorWeights[factor] ?? 1}
                  onChange={value => handleWeightChange(factor, Number(value))}
                  tooltip={{ formatter: value => `가중치 ${value}` }}
                />
              </SliderRow>
            ))}
          </SliderContainer>
        )}
      </ControlPanel>

      <ResultsContainer>
        {generateLoading && (
          <GlassCard>
            <Spin />
          </GlassCard>
        )}

        {result ? (
          <>
            <SummaryGrid>
              <SummaryCard>
                <SummaryHeader>
                  <SummaryTitle>선별 종목</SummaryTitle>
                  <ThunderboltOutlined style={{ color: theme.colors.accentPrimary, fontSize: 22 }} />
                </SummaryHeader>
                <SummaryValue>{result.parameters.selected_stocks ?? 0} 종목</SummaryValue>
                <SummarySubtitle>{result.summary.selection_criteria}</SummarySubtitle>
              </SummaryCard>

              <SummaryCard>
                <SummaryHeader>
                  <SummaryTitle>사용된 알파</SummaryTitle>
                  <BarChartOutlined style={{ color: theme.colors.accentGold, fontSize: 22 }} />
                </SummaryHeader>
                <SummaryValue>{result.summary.used_factor_count ?? 0}</SummaryValue>
                <SummarySubtitle>
                  요청 {result.summary.requested_factor_count ?? 0}개 / 누락{' '}
                  {(result.missing_factors || []).length}개
                </SummarySubtitle>
              </SummaryCard>

              <SummaryCard>
                <SummaryHeader>
                  <SummaryTitle>합성 점수 범위</SummaryTitle>
                  <FundOutlined style={{ color: theme.colors.accentGold, fontSize: 22 }} />
                </SummaryHeader>
                <SummaryValue>{formatScore(result.summary.best_score)}</SummaryValue>
                <SummarySubtitle>최저 {formatScore(result.summary.worst_score)}</SummarySubtitle>
              </SummaryCard>
            </SummaryGrid>

            <ResultsCard>
              <SummaryHeader>
                <SummaryTitle>선별된 종목</SummaryTitle>
                <InlineNote>
                  평가 시점: {result.parameters.as_of_date ?? result.parameters.end_date ?? '최신'}
                </InlineNote>
              </SummaryHeader>

              {result.stocks.length > 0 ? (
                <Table
                  columns={columns}
                  dataSource={result.stocks}
                  rowKey={record => `${record.ticker}-${record.rank}`}
                  pagination={{ pageSize: 20 }}
                />
              ) : (
                <Empty description="표시할 종목이 없습니다." />
              )}

              {result.missing_factor_errors && Object.keys(result.missing_factor_errors).length > 0 && (
                <Space wrap>
                  {Object.entries(result.missing_factor_errors).map(([factor, reason]) => (
                    <Tooltip key={factor} title={reason}>
                      <Tag color="red">미포함: {factor}</Tag>
                    </Tooltip>
                  ))}
                </Space>
              )}
            </ResultsCard>
          </>
        ) : (
          <GlassCard>
            <Empty description="조건을 설정하고 포트폴리오를 생성하세요." />
          </GlassCard>
        )}
      </ResultsContainer>
    </PageContainer>
  );
};
