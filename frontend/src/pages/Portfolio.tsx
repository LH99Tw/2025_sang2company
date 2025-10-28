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
  SlidersOutlined,
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

const Header = styled.div`
  display: flex;
  flex-direction: column;
  gap: ${theme.spacing.sm};
`;

const Title = styled.h1`
  font-size: ${theme.typography.fontSize.h1};
  color: ${theme.colors.textPrimary};
  margin: 0;
  font-weight: 700;
`;

const Subtitle = styled.span`
  color: ${theme.colors.textSecondary};
  font-size: ${theme.typography.fontSize.body};
`;

const Layout = styled.div`
  display: flex;
  justify-content: center;
  align-items: flex-start;
  gap: ${theme.spacing.xl};
  flex-wrap: wrap;
`;

const SettingsPanel = styled(GlassCard)`
  flex: 0 0 420px;
  display: flex;
  flex-direction: column;
  gap: ${theme.spacing.lg};
`;

const SettingsHeader = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
`;

const SettingsTitle = styled.h2`
  margin: 0;
  font-size: ${theme.typography.fontSize.h4};
  color: ${theme.colors.textPrimary};
  font-weight: 700;
`;

const SettingsBody = styled.div`
  display: flex;
  flex-direction: column;
  gap: ${theme.spacing.md};
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

const ActionsRow = styled.div`
  display: flex;
  justify-content: flex-end;
  gap: ${theme.spacing.sm};
  flex-wrap: wrap;
`;

const NoFactors = styled.div`
  color: ${theme.colors.textSecondary};
  font-size: ${theme.typography.fontSize.caption};
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
      <Header>
        <Title>알파 포트폴리오</Title>
        <Subtitle>좌측에서 알파와 가중치를 설정하고, 우측에서 결과를 확인하세요.</Subtitle>
      </Header>

      <Layout>
        <SettingsPanel>
          <SettingsHeader>
            <SettingsTitle>
              <SlidersOutlined style={{ marginRight: 8 }} />
              설정
            </SettingsTitle>
            <InlineNote>Softmax로 가중치를 정규화합니다.</InlineNote>
          </SettingsHeader>

          <SettingsBody>
            <FormGroup>
              <Label>
                <FilterOutlined />
                알파 선택
              </Label>
              <Select
                mode="multiple"
                allowClear
                showSearch
                placeholder="알파를 선택하세요"
                onChange={handleFactorsChange}
                value={selectedFactors}
                loading={factorsLoading}
                optionFilterProp="value"
              >
                {factorOptions.map(option => (
                  <Option key={option.value} value={option.value}>
                    {option.label}
                  </Option>
                ))}
              </Select>
              {selectedFactors.length === 0 && <NoFactors>선택된 알파가 없습니다.</NoFactors>}
            </FormGroup>

          <FormGroup>
            <Label>평가 시점</Label>
            <DatePicker
              style={{ width: '100%' }}
              value={asOfDate}
              onChange={value => setAsOfDate(value)}
              allowClear
            />
            <InlineNote>지정한 날짜 기준으로 알파를 계산합니다. 비워두면 최신 데이터가 사용됩니다.</InlineNote>
          </FormGroup>

            <FormGroup>
              <Label>선별 기준</Label>
              <Radio.Group
                value={selectionMode}
                onChange={event => setSelectionMode(event.target.value)}
              >
                <Space direction="vertical">
                  <Radio value="percentage">상위 퍼센트</Radio>
                  <Radio value="count">상위 개수</Radio>
                </Space>
              </Radio.Group>
            </FormGroup>

            {selectionMode === 'percentage' ? (
              <FormGroup>
                <Label>상위 퍼센트 (%)</Label>
                <InputNumber
                  min={1}
                  max={100}
                  value={topPercentage}
                  onChange={value => setTopPercentage(value ?? 1)}
                  style={{ width: '100%' }}
                />
              </FormGroup>
            ) : (
              <FormGroup>
                <Label>상위 종목 수</Label>
                <InputNumber
                  min={1}
                  max={500}
                  value={topCount}
                  onChange={value => setTopCount(value ?? 1)}
                  style={{ width: '100%' }}
                />
              </FormGroup>
            )}

            <FormGroup>
              <Label>알파 가중치 조정</Label>
              {selectedFactors.length === 0 ? (
                <NoFactors>알파를 선택하면 가중치를 조정할 수 있습니다.</NoFactors>
              ) : (
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
            </FormGroup>

            <FormGroup>
              <Label>상세 팩터 정보</Label>
              <Switch checked={includeBreakdown} onChange={checked => setIncludeBreakdown(checked)} />
            </FormGroup>
          </SettingsBody>

          <ActionsRow>
            <GlassButton
              icon={<ThunderboltOutlined />}
              onClick={handleGenerate}
              loading={generateLoading}
              disabled={factorsLoading}
            >
              포트폴리오 생성
            </GlassButton>
          </ActionsRow>
        </SettingsPanel>

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
                    <BarChartOutlined style={{ color: theme.colors.info, fontSize: 22 }} />
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
                <FundOutlined style={{ color: theme.colors.accentPrimary, fontSize: 22 }} />
                  </SummaryHeader>
                  <SummaryValue>{formatScore(result.summary.best_score)}</SummaryValue>
                  <SummarySubtitle>최저 {formatScore(result.summary.worst_score)}</SummarySubtitle>
                </SummaryCard>
              </SummaryGrid>

              <ResultsCard>
                <SettingsHeader>
                  <SettingsTitle>선별된 종목</SettingsTitle>
                  <InlineNote>
                    평가 시점: {result.parameters.as_of_date ?? result.parameters.end_date ?? '최신'}
                  </InlineNote>
                </SettingsHeader>

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
      </Layout>
    </PageContainer>
  );
};
