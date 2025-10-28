import React, { useEffect, useState, useCallback, useMemo } from 'react';
import styled from 'styled-components';
import { GlassCard } from '../components/common/GlassCard';
import { theme } from '../styles/theme';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip as RechartsTooltip,
} from 'recharts';
import type { TooltipProps } from 'recharts';
import ReactApexChart from 'react-apexcharts';
import type { ApexOptions } from 'apexcharts';
import dayjs, { Dayjs } from 'dayjs';
import { useAuth } from '../contexts/AuthContext';
import { Button, Input, Modal, Form, message, Popconfirm, Select, Tag, Tooltip, Pagination, DatePicker, Spin, Empty } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, EyeOutlined, ThunderboltOutlined } from '@ant-design/icons';
import { GlassButton } from '../components/common/GlassButton';
import { StoredAlpha, TickerPerformanceMetric, TickerPerformanceSeriesEntry, MarketHeatmapResponse } from '../types';
import { fetchUserAlphas, saveUserAlphas as saveUserAlphasApi, deleteUserAlpha as deleteUserAlphaApi, getTickerPerformance, getTickerList, getMarketHeatmap } from '../services/api';

// Chart.js 등록
const defaultAlphaSummary = {
  shared_count: 0,
  private_count: 0,
  total_count: 0,
  registry_size: 0,
};

const normalizeAlpha = (alpha: any): StoredAlpha => {
  if (!alpha || typeof alpha !== 'object') {
    return {
      id: `alpha_${Math.random().toString(36).slice(2)}`,
      name: 'Unknown Alpha',
      source: 'shared',
      provider: 'unknown',
      description: '',
      tags: [],
      metadata: {},
    };
  }

  const metadata = (alpha.metadata && typeof alpha.metadata === 'object') ? alpha.metadata : {};
  const rawTags = alpha.tags ?? metadata.tags ?? [];
  const tags = Array.isArray(rawTags)
    ? rawTags.map((tag: any) => String(tag).trim()).filter(Boolean)
    : [];

  return {
    id: alpha.id || metadata.id || alpha.name || `alpha_${Math.random().toString(36).slice(2)}`,
    name: alpha.name || metadata.name || 'Unnamed Alpha',
    expression: alpha.expression || metadata.expression || '',
    source: alpha.source || 'shared',
    provider: alpha.provider || metadata.provider || 'user-defined',
    owner: alpha.owner || metadata.owner,
    created_at: alpha.created_at || metadata.created_at,
    updated_at: alpha.updated_at || metadata.updated_at,
    description: alpha.description || metadata.description || '',
    tags,
    metadata,
  };
};

const normalizeAlphaList = (list?: any): StoredAlpha[] => {
  if (!Array.isArray(list)) {
    return [];
  }
  return list.map(normalizeAlpha);
};

const DashboardContainer = styled.div`
  display: flex;
  flex-direction: column;
  gap: ${theme.spacing.xl};
  min-height: calc(100vh - 200px);
`;

// 다이나믹 아일랜드 스타일 네비게이션 컨테이너
const DynamicIslandNav = styled.div`
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 0;
  padding: ${theme.spacing.md} ${theme.spacing.lg};
  background: ${theme.colors.liquidGlass};
  backdrop-filter: blur(20px);
  border: 1px solid ${theme.colors.liquidGlassBorder};
  border-radius: 28px;
  margin: ${theme.spacing.lg} ${theme.spacing.lg};
  box-shadow: ${theme.shadows.glass};
  position: relative;
  
  &::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: ${theme.colors.liquidGlass};
    border-radius: 28px;
    z-index: -1;
  }
`;

// 다이나믹 아일랜드 스타일 네비게이션 버튼
const DynamicIslandButton = styled.button<{ $active: boolean }>`
  position: relative;
  padding: ${theme.spacing.sm} ${theme.spacing.lg};
  background: transparent;
  border: none;
  border-radius: 20px;
  color: ${props => props.$active ? theme.colors.textPrimary : theme.colors.textSecondary};
  font-size: ${theme.typography.fontSize.body};
  font-weight: ${props => props.$active ? 600 : 400};
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
  min-width: 120px;
  text-align: center;
  z-index: 1;
  
  /* 호버 효과 */
  &:hover {
    background: ${theme.colors.liquidGlassHover};
    color: ${theme.colors.textPrimary};
    transform: scale(1.02);
  }
`;

const TabContent = styled.div`
  display: flex;
  flex-direction: column;
  gap: ${theme.spacing.xl};
  padding: ${theme.spacing.xl};
  flex: 1;
  overflow: visible;
  background: ${theme.colors.backgroundDark};
  border-radius: 20px;
  margin: 0 ${theme.spacing.lg};
  box-shadow: ${theme.shadows.glass};
`;

const CardsGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: ${theme.spacing.lg};

  @media (max-width: 768px) {
    grid-template-columns: 1fr;
  }
`;


const ChartCard = styled(GlassCard)`
  display: flex;
  flex-direction: column;
  gap: ${theme.spacing.lg};
  padding: ${theme.spacing.xl};
`;

const ChartTitle = styled.h3`
  font-size: ${theme.typography.fontSize.h3};
  color: ${theme.colors.textPrimary};
  margin: 0;
  font-weight: 600;
`;

const AnalyzerLayout = styled.div`
  display: grid;
  grid-template-columns: 2fr 1fr;
  grid-template-rows: auto auto;
  grid-template-areas:
    'chart settings'
    'metrics metrics';
  gap: ${theme.spacing.xl};
  align-items: stretch;

  @media (max-width: 1200px) {
    grid-template-columns: 1fr;
    grid-template-rows: auto auto auto;
    grid-template-areas:
      'chart'
      'settings'
      'metrics';
  }
`;

const AnalyzerColumn = styled.div`
  display: contents;
`;

const AnalyzerAside = styled.div`
  display: contents;
`;

const AnalyzerChartCard = styled(GlassCard)`
  display: flex;
  flex-direction: column;
  gap: ${theme.spacing.lg};
  padding: ${theme.spacing.xl};
  min-height: 420px;
  grid-area: chart;
`;

const MetricsCard = styled(GlassCard)`
  padding: ${theme.spacing.xl};
  display: flex;
  flex-direction: column;
  gap: ${theme.spacing.md};
  grid-area: metrics;
`;

const SettingsPanel = styled(GlassCard)`
  display: flex;
  flex-direction: column;
  gap: ${theme.spacing.lg};
  padding: ${theme.spacing.xl};
  min-height: 100%;
  grid-area: settings;
  align-self: stretch;
`;

const SettingsSection = styled.div`
  display: flex;
  flex-direction: column;
  gap: ${theme.spacing.sm};
`;

const SettingsLabel = styled.span`
  color: ${theme.colors.textSecondary};
  font-size: ${theme.typography.fontSize.caption};
  font-weight: 600;
  letter-spacing: 0.05em;
  text-transform: uppercase;
`;

const LegendList = styled.div`
  display: flex;
  flex-wrap: wrap;
  gap: ${theme.spacing.sm};
`;

const LegendItem = styled.button<{ $active: boolean }>`
  display: inline-flex;
  align-items: center;
  gap: ${theme.spacing.xs};
  padding: ${theme.spacing.xs} ${theme.spacing.sm};
  border-radius: 999px;
  border: 1px solid ${(props) => (props.$active ? theme.colors.accentPrimary : theme.colors.liquidGlassBorder)};
  background: ${(props) => (props.$active ? 'rgba(139, 170, 255, 0.12)' : theme.colors.liquidGlass)};
  color: ${theme.colors.textPrimary};
  cursor: pointer;
  transition: ${theme.transitions.normal};
  font-size: ${theme.typography.fontSize.caption};

  &:hover {
    border-color: ${theme.colors.accentPrimary};
    transform: translateY(-1px);
  }
`;

const LegendSwatch = styled.span`
  width: 10px;
  height: 10px;
  border-radius: 50%;
  display: block;
`;

const TooltipContainer = styled.div`
  background: ${theme.colors.backgroundSecondary};
  border: 1px solid ${theme.colors.liquidGlassBorder};
  border-radius: 12px;
  padding: ${theme.spacing.sm} ${theme.spacing.md};
  color: ${theme.colors.textPrimary};
  box-shadow: ${theme.shadows.glass};
`;

const TooltipRow = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: ${theme.spacing.sm};
  font-size: ${theme.typography.fontSize.caption};
`;

const TooltipValue = styled.span`
  font-weight: 600;
`;

const MetricsTable = styled.table`
  width: 100%;
  border-collapse: collapse;
`;

const MetricsHeadCell = styled.th`
  text-align: left;
  padding: ${theme.spacing.xs} ${theme.spacing.sm};
  color: ${theme.colors.textSecondary};
  font-size: ${theme.typography.fontSize.caption};
  font-weight: 600;
  border-bottom: 1px solid ${theme.colors.liquidGlassBorder};
`;

const MetricsRow = styled.tr`
  &:not(:last-child) {
    border-bottom: 1px solid ${theme.colors.liquidGlassBorder};
  }
`;

const MetricsCell = styled.td`
  padding: ${theme.spacing.sm};
  color: ${theme.colors.textPrimary};
  font-size: ${theme.typography.fontSize.caption};
  white-space: nowrap;
`;

const MetricsTicker = styled.span`
  font-weight: 600;
  color: ${theme.colors.textPrimary};
`;

const hashStringToHue = (input: string): number => {
  let hash = 0;
  for (let i = 0; i < input.length; i += 1) {
    hash = input.charCodeAt(i) + ((hash << 5) - hash);
  }
  return Math.abs(hash) % 360;
};

const colorFromTicker = (ticker: string): string => {
  const hue = hashStringToHue(ticker);
  return `hsl(${hue}, 70%, 60%)`;
};

const clampChange = (value: number): number => {
  if (!Number.isFinite(value)) {
    return 0;
  }
  return Math.max(-0.03, Math.min(0.03, value));
};

const getHeatmapColor = (change: number): string => {
  const clamped = clampChange(change);
  const abs = Math.abs(clamped);
  const ratio = Math.min(abs / 0.03, 1);

  if (abs < 1e-4) {
    return '#2f3136';
  }

  const saturation = 60 + ratio * 28;
  const lightness = 46 - ratio * 24;

  if (clamped >= 0) {
    const hue = 135 - ratio * 10;
    return `hsl(${hue}, ${saturation}%, ${lightness}%)`;
  }

  const hue = 355 + ratio * 5;
  return `hsl(${hue}, ${saturation}%, ${lightness}%)`;
};

const formatChangePercent = (value: number): string => {
  const percent = (value || 0) * 100;
  return `${percent >= 0 ? '+' : ''}${percent.toFixed(2)}%`;
};

interface ApexTreemapDatum {
  x: string;
  y: number;
  fillColor?: string;
  dataLabels?: {
    style?: {
      fontSize?: string;
      fontWeight?: string | number;
      colors?: string[];
    };
  };
  meta: {
    ticker: string;
    name: string;
    sector?: string;
    industry?: string;
    changeText?: string;
    changeValue?: number;
    price?: number;
    marketCap?: number;
    labelText?: string;
  };
}

type ApexTreemapSeries = { name: string; data: ApexTreemapDatum[] };

type HeatmapNodeType = 'sector' | 'industry' | 'ticker';

interface DecoratedHeatmapNode {
  name: string;
  value: number;
  change: number;
  displayChange: string;
  display_change?: string;
  color: string;
  fill?: string;
  type: HeatmapNodeType;
  kind?: HeatmapNodeType;
  label?: string;
  children?: DecoratedHeatmapNode[];
  sector?: string;
  industry?: string;
  ticker?: string;
  close?: number;
  market_cap?: number;
  change_pct?: number;
  change_value?: number;
}

const decorateHeatmapTree = (nodes: any[], depth = 0, parentSector?: string): DecoratedHeatmapNode[] => {
  if (!Array.isArray(nodes)) {
    return [];
  }

  return nodes.map((node: any) => {
    const children = Array.isArray(node.children) ? node.children : [];
    const type: HeatmapNodeType = depth === 0 ? 'sector' : depth === 1 ? 'industry' : 'ticker';
    const change = Number(node.change_pct ?? node.change ?? 0) || 0;
    const color = typeof node.color === 'string' ? node.color : getHeatmapColor(change);
    const display = typeof node.display_change === 'string' ? node.display_change : formatChangePercent(change);
    const sectorName = depth === 0 ? node.name : (node.sector ?? parentSector ?? node.name);
    const industryName = type === 'industry' ? node.name : node.industry;

    const decorated: DecoratedHeatmapNode = {
      name: node.name,
      label: node.label ?? node.name,
      value: Number(node.value ?? 0) || 0,
      change,
      change_pct: change,
      change_value: Number(node.change_value ?? 0) || 0,
      displayChange: display,
      display_change: typeof node.display_change === 'string' ? node.display_change : display,
      color,
      fill: color,
      type,
      kind: type,
      sector: sectorName,
      industry: industryName,
      ticker: node.ticker ?? node.name,
      close: node.close !== undefined ? Number(node.close) : undefined,
      market_cap: node.market_cap !== undefined ? Number(node.market_cap) : undefined,
    };

    if (children.length > 0) {
      decorated.children = decorateHeatmapTree(children, depth + 1, sectorName);
    }

    return decorated;
  });
};

const formatMarketCap = (cap?: number): string => {
  if (!Number.isFinite(cap) || !cap || cap <= 0) {
    return '-';
  }
  const units = [
    { value: 1e12, suffix: 'T' },
    { value: 1e9, suffix: 'B' },
    { value: 1e6, suffix: 'M' },
  ];
  for (const unit of units) {
    if (cap >= unit.value) {
      return `${(cap / unit.value).toFixed(2)}${unit.suffix}`;
    }
  }
  return `${cap.toFixed(0)}`;
};

const ensurePositiveValue = (value?: number): number => {
  const numeric = Number(value ?? 0);
  if (!Number.isFinite(numeric) || numeric <= 0) {
    return 0.0001;
  }
  return numeric;
};

const SECTOR_COLOR_PALETTE = [
  '#4F46E5',
  '#0EA5E9',
  '#10B981',
  '#F97316',
  '#EC4899',
  '#8B5CF6',
  '#6366F1',
  '#22D3EE',
  '#84CC16',
  '#F59E0B',
  '#14B8A6',
  '#F87171',
];

const hexToRgb = (hex: string) => {
  const normalized = hex.replace('#', '');
  const full = normalized.length === 3
    ? normalized.split('').map((ch) => ch + ch).join('')
    : normalized.padEnd(6, '0');
  const intVal = parseInt(full, 16);
  return {
    r: (intVal >> 16) & 255,
    g: (intVal >> 8) & 255,
    b: intVal & 255,
  };
};

const rgbToHex = (r: number, g: number, b: number) => {
  const clamp = (value: number) => Math.max(0, Math.min(255, Math.round(value)));
  return `#${[clamp(r), clamp(g), clamp(b)]
    .map((value) => value.toString(16).padStart(2, '0'))
    .join('')}`;
};

const mixColors = (colorA: string, colorB: string, amount: number) => {
  const ratio = Math.max(0, Math.min(1, amount));
  const a = hexToRgb(colorA);
  const b = hexToRgb(colorB);
  return rgbToHex(
    a.r + (b.r - a.r) * ratio,
    a.g + (b.g - a.g) * ratio,
    a.b + (b.b - a.b) * ratio,
  );
};

const NEUTRAL_COLOR = '#3C4043';
const NEGATIVE_BLEND = '#0F1115';
const DIM_BLEND = '#2F3136';
const LIGHT_BLEND = '#E5E7EB';

const applySectorTone = (baseColor: string, changeValue?: number) => {
  const clampChange = Math.max(-0.05, Math.min(0.05, Number(changeValue ?? 0)));
  const ratio = Math.abs(clampChange) / 0.05;

  if (clampChange >= 0) {
    const startBlend = 0.2; // 20% 섹터 색으로 시작
    const weight = startBlend + (0.95 - startBlend) * Math.pow(ratio, 0.7);
    return mixColors(NEUTRAL_COLOR, baseColor, weight);
  }

  const tintWeight = 0.18 * (1 - Math.pow(ratio, 0.6));
  const tinted = mixColors(NEUTRAL_COLOR, baseColor, tintWeight);
  const lightened = mixColors(tinted, LIGHT_BLEND, ratio * 0.5);
  const withDepth = mixColors(lightened, NEGATIVE_BLEND, ratio * 0.25);
  return withDepth;
};

const collectTickerNodes = (
  node: DecoratedHeatmapNode,
  baseColor: string,
  dimmed: boolean,
): ApexTreemapDatum[] => {
  if (!node.children || node.children.length === 0) {
    const value = ensurePositiveValue(node.value);
    const fontSize = Math.min(22, Math.max(10, Math.log10(value + 1) * 3 + 8));
    const changeValue = node.change_pct ?? node.change ?? 0;
    const changeText = node.display_change ?? formatChangePercent(changeValue);
    const tickerSymbol = node.ticker ?? node.label ?? node.name;
    const toneColor = applySectorTone(baseColor, changeValue);
    const fillColor = dimmed ? mixColors(toneColor, DIM_BLEND, 0.6) : toneColor;
    return [
      {
        x: tickerSymbol,
        y: value,
        fillColor,
        dataLabels: {
          style: {
            fontSize: `${fontSize.toFixed(1)}px`,
            fontWeight: 700,
            colors: [dimmed ? '#6B7280' : '#F9FAFB'],
          },
        },
        meta: {
          ticker: tickerSymbol,
          name: node.name,
          sector: node.sector,
          industry: node.industry,
          changeText,
          changeValue,
          price: node.close,
          marketCap: node.market_cap,
          labelText: tickerSymbol,
        },
      },
    ];
  }

  return node.children.flatMap((child) => collectTickerNodes(child, baseColor, dimmed));
};

const buildApexTreemapSeries = (
  sectors: DecoratedHeatmapNode[],
  activeSector: string | null,
): { series: ApexTreemapSeries[]; colorMap: Record<string, string> } => {
  const colorMap: Record<string, string> = {};
  let paletteIndex = 0;

  const ensureColor = (sectorName: string) => {
    if (!colorMap[sectorName]) {
      colorMap[sectorName] = SECTOR_COLOR_PALETTE[paletteIndex % SECTOR_COLOR_PALETTE.length];
      paletteIndex += 1;
    }
    return colorMap[sectorName];
  };

  const series = sectors
    .map((sector) => {
      const sectorName = sector.label ?? sector.name;
      const baseColor = ensureColor(sectorName);
      const dimmed = Boolean(activeSector && activeSector !== sectorName);
      const data = collectTickerNodes(sector, baseColor, dimmed);
      if (!data.length) {
        return null;
      }
      return {
        name: sectorName,
        data,
      };
    })
    .filter((series): series is ApexTreemapSeries => Boolean(series));

  return { series, colorMap };
};



const HeatmapHeader = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: ${theme.spacing.sm};
`;

const HeatmapInfoText = styled.span`
  color: ${theme.colors.textSecondary};
  font-size: ${theme.typography.fontSize.caption};
`;


const HeatmapWrapper = styled.div`
  width: 100%;
  min-height: 760px;
`;

const SectorChipRow = styled.div`
  display: flex;
  flex-wrap: wrap;
  gap: ${theme.spacing.sm};
  margin-bottom: ${theme.spacing.md};
`;

const SectorChip = styled.div<{ $color: string; $active: boolean; $dimmed: boolean }>`
  display: inline-flex;
  align-items: center;
  gap: ${theme.spacing.xs};
  padding: 6px 12px;
  border-radius: 12px;
  background: ${({ $color }) => `${$color}22`};
  border: ${({ $active }) => ($active ? '2px' : '1px')} solid ${({ $color }) => `${$color}80`};
  color: ${theme.colors.textPrimary};
  font-size: ${theme.typography.fontSize.caption};
  opacity: ${({ $dimmed }) => ($dimmed ? 0.45 : 1)};
  cursor: pointer;
  transition: all 0.2s ease;
  &:hover {
    opacity: 1;
    border-color: ${({ $color }) => `${$color}AA`};
  }
`;

export const Dashboard: React.FC = () => {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState(0);
  const [heatmapData, setHeatmapData] = useState<MarketHeatmapResponse | null>(null);
  const [heatmapLoading, setHeatmapLoading] = useState(false);
  const [heatmapError, setHeatmapError] = useState<string | null>(null);
  const [tickerOptions, setTickerOptions] = useState<string[]>([]);
  const [selectedTickers, setSelectedTickers] = useState<string[]>(['S&P500']);
  const [tickerColors, setTickerColors] = useState<Record<string, string>>({});
  const [highlightedTicker, setHighlightedTicker] = useState<string | null>(null);
  const [performanceSeries, setPerformanceSeries] = useState<TickerPerformanceSeriesEntry[]>([]);
  const [performanceMetrics, setPerformanceMetrics] = useState<TickerPerformanceMetric[]>([]);
  const [missingTickers, setMissingTickers] = useState<string[]>([]);
  const [analysisError, setAnalysisError] = useState<string | null>(null);
  const [performanceLoading, setPerformanceLoading] = useState(false);
  const [autoAnalyzeQueued, setAutoAnalyzeQueued] = useState(false);
  const [dateRange, setDateRange] = useState<[Dayjs, Dayjs]>([dayjs('2000-01-01'), dayjs()]);
  const [legendHoverSector, setLegendHoverSector] = useState<string | null>(null);
  const [legendLockedSector, setLegendLockedSector] = useState<string | null>(null);
  const [activeSectorFromLegend, setActiveSectorFromLegend] = useState<string | null>(null);

  const ensureTickerColors = useCallback((tickers: string[]) => {
    setTickerColors((prev) => {
      const next = { ...prev };
      tickers.forEach((ticker) => {
        if (!next[ticker]) {
          next[ticker] = colorFromTicker(ticker);
        }
      });
      return next;
    });
  }, []);

  useEffect(() => {
    const loadTickerUniverse = async () => {
      try {
        const response = await getTickerList();
        if (response?.success && Array.isArray(response.tickers)) {
          const normalized = response.tickers.map((ticker: string) => ticker.toUpperCase());
          const withIndex = normalized.includes('S&P500')
            ? normalized
            : ['S&P500', ...normalized];
          const uniqueOptions = Array.from(new Set<string>(withIndex));
          setTickerOptions(uniqueOptions);
          setAutoAnalyzeQueued(true);
        }
      } catch (error) {
        console.error('티커 목록 로드 실패:', error);
      }
    };

    loadTickerUniverse();
  }, []);

  useEffect(() => {
    if (selectedTickers.length > 0) {
      ensureTickerColors(selectedTickers);
    }
  }, [selectedTickers, ensureTickerColors]);

  const formatPercent = useCallback((value?: number, digits = 2) => {
    if (value === undefined || value === null || Number.isNaN(value)) {
      return '-';
    }
    return `${(value * 100).toFixed(digits)}%`;
  }, []);

  const formatNumber = useCallback((value?: number, digits = 2) => {
    if (value === undefined || value === null || Number.isNaN(value)) {
      return '-';
    }
    return value.toFixed(digits);
  }, []);

  const renderTooltip = useCallback(
    ({ active, payload, label }: TooltipProps<number, string>) => {
      if (!active || !payload || payload.length === 0) {
        return null;
      }

      return (
        <TooltipContainer>
          <div style={{ fontWeight: 600, marginBottom: theme.spacing.xs }}>{label}</div>
          {payload.map((entry) => {
            if (entry.value === undefined || entry.value === null) {
              return null;
            }
            return (
              <TooltipRow key={entry.dataKey as string}>
                <div style={{ display: 'flex', alignItems: 'center', gap: theme.spacing.xs }}>
                  <LegendSwatch style={{ background: entry.color }} />
                  <span>{entry.dataKey}</span>
                </div>
                <TooltipValue>{formatPercent(Number(entry.value))}</TooltipValue>
              </TooltipRow>
            );
          })}
        </TooltipContainer>
      );
    },
    [formatPercent]
  );

  const handleLegendToggle = useCallback((ticker: string) => {
    setHighlightedTicker((prev) => (prev === ticker ? null : ticker));
  }, []);

  const handleAnalyze = useCallback(async () => {
    if (!selectedTickers.length) {
      message.warning('분석할 종목을 선택해주세요.');
      return;
    }

    setPerformanceLoading(true);
    setAnalysisError(null);

    try {
      ensureTickerColors(selectedTickers);
      const [start, end] = dateRange;
      const response = await getTickerPerformance({
        tickers: selectedTickers,
        start_date: start.format('YYYY-MM-DD'),
        end_date: end.format('YYYY-MM-DD'),
      });

      if (!response?.success) {
        setPerformanceSeries([]);
        setPerformanceMetrics([]);
        setMissingTickers(response?.missing_tickers || []);
        setAnalysisError(response?.error || '종목 성과 분석에 실패했습니다.');
      } else {
        setPerformanceSeries(Array.isArray(response.series) ? response.series : []);
        setPerformanceMetrics(Array.isArray(response.metrics) ? response.metrics : []);
        setMissingTickers(Array.isArray(response.missing_tickers) ? response.missing_tickers : []);
        setHighlightedTicker(null);
      }
    } catch (error) {
      console.error('종목 성과 분석 실패:', error);
      setPerformanceSeries([]);
      setPerformanceMetrics([]);
      setMissingTickers([]);
      setAnalysisError('종목 성과 분석 중 오류가 발생했습니다.');
    } finally {
      setPerformanceLoading(false);
    }
  }, [selectedTickers, ensureTickerColors, dateRange]);

  useEffect(() => {
    if (autoAnalyzeQueued && selectedTickers.length > 0) {
      handleAnalyze();
      setAutoAnalyzeQueued(false);
    }
  }, [autoAnalyzeQueued, selectedTickers, handleAnalyze]);

  useEffect(() => {
    if (selectedTickers.length === 0 && !performanceLoading) {
      setPerformanceSeries([]);
      setPerformanceMetrics([]);
      setMissingTickers([]);
      setAnalysisError(null);
    }
  }, [selectedTickers.length, performanceLoading]);

  // 알파 관리 상태
  const [privateAlphas, setPrivateAlphas] = useState<StoredAlpha[]>([]);
  const [sharedAlphas, setSharedAlphas] = useState<StoredAlpha[]>([]);
  const [alphaSummary, setAlphaSummary] = useState({ ...defaultAlphaSummary });
  const [alphaLoading, setAlphaLoading] = useState(false);
  const [isAlphaModalVisible, setIsAlphaModalVisible] = useState(false);
  const [editingAlpha, setEditingAlpha] = useState<StoredAlpha | null>(null);
  const [alphaSearch, setAlphaSearch] = useState('');
  const [alphaPage, setAlphaPage] = useState(1);
  const alphaPageSize = 10;
  const [alphaForm] = Form.useForm();

  const sectorNodes = useMemo(
    () => (heatmapData?.sectors ?? []) as DecoratedHeatmapNode[],
    [heatmapData?.sectors]
  );

  const activeLegendSector = legendLockedSector ?? legendHoverSector;

  const highlightSector = activeLegendSector ?? activeSectorFromLegend;

  const { series: apexHeatmapSeries, colorMap: sectorColorMap } = useMemo(() => {
    return buildApexTreemapSeries(sectorNodes, highlightSector ?? null);
  }, [sectorNodes, highlightSector]);

  const sectorSummaries = useMemo(
    () =>
      apexHeatmapSeries.map((series) => {
        const totalValue = series.data.reduce((sum, item) => sum + item.y, 0);
        const weightedChange =
          totalValue > 0
            ? series.data.reduce((acc, item) => acc + (item.meta.changeValue ?? 0) * item.y, 0) / totalValue
            : 0;
        return {
          name: series.name,
          color: sectorColorMap[series.name] ?? theme.colors.accentPrimary,
          totalValue,
          changeValue: weightedChange,
          changeText: formatChangePercent(weightedChange),
        };
      }),
    [apexHeatmapSeries, sectorColorMap]
  );

  const handleSectorChipEnter = useCallback((name: string) => {
    if (legendLockedSector) return;
    setLegendHoverSector(name);
  }, [legendLockedSector]);

  const handleSectorChipLeave = useCallback(() => {
    if (legendLockedSector) return;
    setLegendHoverSector(null);
  }, [legendLockedSector]);

  const handleSectorChipClick = useCallback((name: string) => {
    setLegendLockedSector((prev) => (prev === name ? null : name));
    setLegendHoverSector(null);
    setActiveSectorFromLegend(null);
  }, []);

  const handleLegendClick = useCallback((seriesIndex: number, opts: any) => {
    const seriesArr = opts?.config?.series as ApexTreemapSeries[] | undefined;
    const seriesName = seriesArr?.[seriesIndex]?.name;
    if (!seriesName) return;
    setActiveSectorFromLegend((prev) => (prev === seriesName ? null : seriesName));
    setLegendLockedSector(null);
    setLegendHoverSector(null);
  }, []);

  const apexHeatmapOptions = useMemo<ApexOptions>(() => {
    return {
      chart: {
        type: 'treemap',
        background: 'transparent',
        toolbar: { show: false },
        animations: { enabled: false },
        fontFamily: theme.typography.fontFamily.primary,
      },
      legend: {
        show: true,
        position: 'top',
        onItemClick: {
          toggleDataSeries: false,
        },
        labels: {
          colors: theme.colors.textSecondary,
        },
        itemMargin: {
          horizontal: 12,
          vertical: 4,
        },
        formatter: (seriesName, opts) => {
          return `<span data-legend-index="${opts.seriesIndex}">${seriesName}</span>`;
        },
      },
      colors: apexHeatmapSeries.map((series) => sectorColorMap[series.name] ?? theme.colors.accentPrimary),
      dataLabels: {
        enabled: true,
        style: {
          fontSize: '14px',
          fontWeight: 700,
          colors: ['#F9FAFB'],
        },
        formatter: (_value, opts) => {
          const series = opts.w.config.series as ApexTreemapSeries[] | undefined;
          const datum = series?.[opts.seriesIndex]?.data?.[opts.dataPointIndex] as ApexTreemapDatum | undefined;
          return datum?.meta?.labelText ?? datum?.meta?.ticker ?? '';
        },
      },
      tooltip: {
        theme: 'dark',
        custom: ({ seriesIndex, dataPointIndex, w }) => {
          const series = w.config.series as ApexTreemapSeries[] | undefined;
          const datum = series?.[seriesIndex]?.data?.[dataPointIndex] as ApexTreemapDatum | undefined;
          if (!datum) {
            return '';
          }
          const meta = datum.meta;
          const lines: string[] = [];
          lines.push(`<div style="font-weight:700;margin-bottom:4px;">${meta.ticker}${meta.name && meta.name !== meta.ticker ? ` · ${meta.name}` : ''}</div>`);
          if (meta.changeText) {
            lines.push(`<div>변동: ${meta.changeText}</div>`);
          }
          if (typeof meta.price === 'number' && Number.isFinite(meta.price)) {
            lines.push(`<div>가격: $${meta.price.toFixed(2)}</div>`);
          }
          lines.push(`<div>시가총액: ${formatMarketCap(meta.marketCap)}</div>`);
          if (meta.sector) {
            lines.push(`<div>섹터: ${meta.sector}</div>`);
          }
          if (meta.industry) {
            lines.push(`<div>산업: ${meta.industry}</div>`);
          }
          return `
            <div style="background:${theme.colors.backgroundSecondary};border:1px solid ${theme.colors.border};border-radius:8px;padding:8px 12px;color:${theme.colors.textPrimary};font-size:${theme.typography.fontSize.caption};min-width:180px;">
              ${lines.join('')}
            </div>
          `;
        },
      },
      plotOptions: {
        treemap: {
          enableShades: true,
          shadeIntensity: 0.4,
          reverseNegativeShade: true,
          useFillColorAsStroke: true,
          stroke: {
            width: 1,
            colors: [theme.colors.backgroundDark],
          },
          dataLabels: {
            format: 'truncate',
          },
          colorScale: {
            ranges: [
              { from: -100, to: -0.0001, color: '#CD363A' },
              { from: -0.0001, to: 0.0001, color: '#3C4043' },
              { from: 0.0001, to: 100, color: '#128A5E' },
            ],
          },
        },
      },
      noData: {
        text: '히트맵 데이터를 불러오는 중입니다...',
        align: 'center',
        verticalAlign: 'middle',
        style: {
          color: theme.colors.textSecondary,
        },
      },
    };
  }, [apexHeatmapSeries, sectorColorMap, handleLegendClick]);


  // 알파 관리 함수들
  const loadAlphas = useCallback(async () => {
    try {
      setAlphaLoading(true);
      const data = await fetchUserAlphas();
      setSharedAlphas(normalizeAlphaList(data.shared_alphas));
      setPrivateAlphas(normalizeAlphaList(data.private_alphas));
      setAlphaSummary(data.summary ? { ...defaultAlphaSummary, ...data.summary } : { ...defaultAlphaSummary });
    } catch (error) {
      console.error('알파 목록 로드 실패:', error);
      setSharedAlphas([]);
      setPrivateAlphas([]);
      setAlphaSummary({ ...defaultAlphaSummary });
    } finally {
      setAlphaLoading(false);
    }
  }, []);

  const handleSaveAlpha = useCallback(async (values: any) => {
    if (!user) {
      message.error('알파를 저장하려면 로그인이 필요합니다.');
      return;
    }

    try {
      const alphaData = {
        id: editingAlpha?.id,
        name: values.name,
        expression: values.expression,
        description: values.description || '',
        tags: values.tags || [],
        fitness: values.fitness !== undefined && values.fitness !== null ? Number(values.fitness) : undefined,
      };

      const response = await saveUserAlphasApi([alphaData]);

      if (response.success) {
        message.success('알파가 성공적으로 저장되었습니다.');
        setIsAlphaModalVisible(false);
        alphaForm.resetFields();
        setPrivateAlphas(normalizeAlphaList(response.private_alphas));
        setSharedAlphas(normalizeAlphaList(response.shared_alphas));
        setAlphaSummary(response.summary ? { ...defaultAlphaSummary, ...response.summary } : { ...defaultAlphaSummary });
      } else {
        message.error(response.error || '알파 저장에 실패했습니다.');
      }
    } catch (error) {
      console.error('알파 저장 실패:', error);
      message.error('알파 저장에 실패했습니다.');
    }
  }, [user, editingAlpha, alphaForm]);

  const handleDeleteAlpha = useCallback(async (alphaId: string) => {
    if (!user) {
      message.error('알파를 삭제하려면 로그인이 필요합니다.');
      return;
    }

    try {
      const response = await deleteUserAlphaApi(alphaId);

      if (response.success) {
        message.success('알파가 성공적으로 삭제되었습니다.');
        setPrivateAlphas(normalizeAlphaList(response.private_alphas));
        setSharedAlphas(normalizeAlphaList(response.shared_alphas));
        setAlphaSummary(response.summary ? { ...defaultAlphaSummary, ...response.summary } : { ...defaultAlphaSummary });
      } else {
        message.error(response.error || '알파 삭제에 실패했습니다.');
      }
    } catch (error) {
      console.error('알파 삭제 실패:', error);
      message.error('알파 삭제에 실패했습니다.');
    }
  }, [user]);

  const loadHeatmap = useCallback(async () => {
    try {
      if (heatmapLoading || heatmapData) {
        return;
      }
      setHeatmapLoading(true);
      setHeatmapError(null);
      const response = await getMarketHeatmap();
      if (response?.success) {
        const decorated = decorateHeatmapTree(response.sectors || []);
        setHeatmapData({ ...response, sectors: decorated as any });
      } else {
        setHeatmapError('시장 히트맵 데이터를 불러오지 못했습니다.');
      }
    } catch (error) {
      console.error('시장 히트맵 로드 실패:', error);
      setHeatmapError('시장 히트맵 데이터를 불러오지 못했습니다.');
    } finally {
      setHeatmapLoading(false);
    }
  }, [heatmapData, heatmapLoading]);

  const handleEditAlpha = (alpha: StoredAlpha) => {
    setEditingAlpha(alpha);
    alphaForm.setFieldsValue({
      name: alpha.name,
      expression: alpha.expression || alpha.metadata?.expression || '',
      description: alpha.description || '',
      tags: alpha.tags || [],
      fitness: alpha.metadata?.fitness ?? undefined,
    });
    setIsAlphaModalVisible(true);
  };

  const handleAddAlpha = () => {
    setEditingAlpha(null);
    alphaForm.resetFields();
    setIsAlphaModalVisible(true);
  };

  useEffect(() => {
    if (!user) return;
    loadAlphas();
  }, [user, loadAlphas]);

  useEffect(() => {
    if (activeTab === 1 && !heatmapData && !heatmapLoading) {
      loadHeatmap();
    }
  }, [activeTab, heatmapData, heatmapLoading, loadHeatmap]);


  const renderMarketPerformance = () => {
    const hasSeries = performanceSeries.length > 0 && selectedTickers.length > 0;
    const hasMetrics = performanceMetrics.length > 0;

    return (
      <AnalyzerLayout>
        <AnalyzerColumn>
          <AnalyzerChartCard>
            <ChartTitle>시장 수익률</ChartTitle>
            <div style={{ display: 'flex', flexDirection: 'column', gap: theme.spacing.md }}>
              {missingTickers.length > 0 && (
                <div
                  style={{
                    fontSize: theme.typography.fontSize.caption,
                    color: theme.colors.textSecondary,
                    background: theme.colors.liquidGlass,
                    border: `1px solid ${theme.colors.liquidGlassBorder}`,
                    borderRadius: theme.borderRadius.lg,
                    padding: `${theme.spacing.sm} ${theme.spacing.md}`,
                  }}
                >
                  데이터가 누락된 종목: {missingTickers.join(', ')}
                </div>
              )}
              <div style={{ height: 380 }}>
                {performanceLoading ? (
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      height: '100%',
                    }}
                  >
                    <Spin tip="수익률을 계산하는 중입니다..." />
                  </div>
                ) : hasSeries ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={performanceSeries}>
                      <CartesianGrid stroke="rgba(255, 255, 255, 0.08)" strokeDasharray="3 3" />
                      <XAxis
                        dataKey="date"
                        tick={{ fill: theme.colors.textSecondary }}
                        minTickGap={32}
                        tickLine={false}
                      />
                      <YAxis
                        tick={{ fill: theme.colors.textSecondary }}
                        tickFormatter={(value: number) => `${(value * 100).toFixed(0)}%`}
                        tickLine={false}
                        width={60}
                      />
                      <RechartsTooltip content={renderTooltip} />
                      {selectedTickers.map((ticker) => {
                        const color = tickerColors[ticker] || colorFromTicker(ticker);
                        const isMuted = highlightedTicker !== null && highlightedTicker !== ticker;
                        return (
                          <Line
                            key={ticker}
                            type="monotone"
                            dataKey={ticker}
                            stroke={color}
                            strokeWidth={highlightedTicker === ticker ? 3 : 2.2}
                            dot={false}
                            strokeOpacity={isMuted ? 0.2 : 1}
                            activeDot={{ r: highlightedTicker === ticker ? 5 : 4 }}
                            connectNulls
                            onClick={() => handleLegendToggle(ticker)}
                          />
                        );
                      })}
                    </LineChart>
                  </ResponsiveContainer>
                ) : (
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      height: '100%',
                      color: theme.colors.textSecondary,
                    }}
                  >
                    {analysisError || '종목 분석을 실행하면 기간별 누적 수익률을 확인할 수 있습니다.'}
                  </div>
                )}
              </div>

              {analysisError && (
                <div style={{ color: theme.colors.error, fontSize: theme.typography.fontSize.caption }}>
                  {analysisError}
                </div>
              )}

              {selectedTickers.length > 0 && (
                <LegendList>
                  {selectedTickers.map((ticker) => (
                    <LegendItem
                      key={ticker}
                      type="button"
                      $active={!highlightedTicker || highlightedTicker === ticker}
                      onClick={() => handleLegendToggle(ticker)}
                      style={{ opacity: missingTickers.includes(ticker) ? 0.4 : 1 }}
                    >
                      <LegendSwatch style={{ background: tickerColors[ticker] || colorFromTicker(ticker) }} />
                      <span>{ticker}</span>
                    </LegendItem>
                  ))}
                </LegendList>
              )}
            </div>
          </AnalyzerChartCard>

          <MetricsCard>
            <ChartTitle>종목별 핵심 지표</ChartTitle>
            {performanceLoading ? (
              <div style={{ display: 'flex', justifyContent: 'center', padding: theme.spacing.lg }}>
                <Spin />
              </div>
            ) : hasMetrics ? (
              <MetricsTable>
                <thead>
                  <tr>
                    <MetricsHeadCell>종목</MetricsHeadCell>
                    <MetricsHeadCell>누적 수익률</MetricsHeadCell>
                    <MetricsHeadCell>CAGR</MetricsHeadCell>
                    <MetricsHeadCell>Sharpe</MetricsHeadCell>
                    <MetricsHeadCell>Sortino</MetricsHeadCell>
                    <MetricsHeadCell>MDD</MetricsHeadCell>
                    <MetricsHeadCell>Win Rate</MetricsHeadCell>
                    <MetricsHeadCell>Volatility</MetricsHeadCell>
                  </tr>
                </thead>
                <tbody>
                  {performanceMetrics.map((metric) => {
                    if (metric.error) {
                      return (
                        <MetricsRow key={metric.ticker}>
                          <MetricsCell colSpan={8} style={{ color: theme.colors.textSecondary }}>
                            {metric.ticker}: {metric.error}
                          </MetricsCell>
                        </MetricsRow>
                      );
                    }

                    return (
                      <MetricsRow key={metric.ticker}>
                        <MetricsCell>
                          <MetricsTicker>{metric.ticker}</MetricsTicker>
                        </MetricsCell>
                        <MetricsCell>{formatPercent(metric.total_return)}</MetricsCell>
                        <MetricsCell>{formatPercent(metric.cagr)}</MetricsCell>
                        <MetricsCell>{formatNumber(metric.sharpe_ratio)}</MetricsCell>
                        <MetricsCell>{formatNumber(metric.sortino_ratio)}</MetricsCell>
                        <MetricsCell>{formatPercent(metric.max_drawdown)}</MetricsCell>
                        <MetricsCell>{formatPercent(metric.win_rate)}</MetricsCell>
                        <MetricsCell>{formatPercent(metric.volatility)}</MetricsCell>
                      </MetricsRow>
                    );
                  })}
                </tbody>
              </MetricsTable>
            ) : (
              <Empty description="분석 결과가 없습니다" image={Empty.PRESENTED_IMAGE_SIMPLE} />
            )}
          </MetricsCard>
        </AnalyzerColumn>

        <AnalyzerAside>
          <SettingsPanel>
            <ChartTitle>분석 설정</ChartTitle>
            <SettingsSection>
              <SettingsLabel>기간 선택</SettingsLabel>
              <DatePicker.RangePicker
                value={dateRange}
                onChange={(values) => {
                  if (values && values[0] && values[1]) {
                    setDateRange([values[0], values[1]]);
                  }
                }}
                allowClear={false}
                format="YYYY-MM-DD"
                style={{ width: '100%' }}
              />
            </SettingsSection>

            <SettingsSection>
              <SettingsLabel>종목 검색</SettingsLabel>
              <Select
                mode="multiple"
                allowClear
                showSearch
                placeholder="종목코드를 선택하세요"
                value={selectedTickers}
                onChange={(value) => {
                  setSelectedTickers(value);
                  ensureTickerColors(value);
                  setHighlightedTicker(null);
                }}
                filterOption={(input, option) =>
                  String(option?.value ?? '').toLowerCase().includes(input.toLowerCase())
                }
                options={tickerOptions.map((ticker) => ({ label: ticker, value: ticker }))}
                style={{ width: '100%' }}
              />
            </SettingsSection>

            <GlassButton
              variant="primary"
              onClick={handleAnalyze}
              disabled={performanceLoading || selectedTickers.length === 0}
            >
              종목 분석
            </GlassButton>

            <div style={{ fontSize: theme.typography.fontSize.caption, color: theme.colors.textSecondary }}>
              기간의 시작점을 0%로 정규화하여 종목별 누적 수익률을 비교합니다.
            </div>
          </SettingsPanel>
        </AnalyzerAside>
      </AnalyzerLayout>
    );
  };

  const sortedPrivateAlphas = useMemo(() => {
    return [...privateAlphas].sort((a, b) => {
      const aTime = new Date(a.updated_at || a.created_at || 0).getTime();
      const bTime = new Date(b.updated_at || b.created_at || 0).getTime();
      return bTime - aTime;
    });
  }, [privateAlphas]);

  const combinedAlphas = useMemo(
    () => [...sortedPrivateAlphas, ...sharedAlphas],
    [sortedPrivateAlphas, sharedAlphas]
  );

  const filteredCombinedAlphas = useMemo(() => {
    const keyword = alphaSearch.trim().toLowerCase();
    if (!keyword) {
      return [...combinedAlphas];
    }
    return combinedAlphas.filter((alpha) => {
      const name = alpha.name?.toLowerCase() || '';
      const expression = (alpha.expression || alpha.metadata?.expression || '').toLowerCase();
      return name.includes(keyword) || expression.includes(keyword);
    });
  }, [combinedAlphas, alphaSearch]);

  const totalAlphaPages = Math.max(1, Math.ceil(filteredCombinedAlphas.length / alphaPageSize));

  useEffect(() => {
    if (alphaPage > totalAlphaPages) {
      setAlphaPage(totalAlphaPages);
    }
  }, [alphaPage, totalAlphaPages]);

  useEffect(() => {
    setAlphaPage(1);
  }, [alphaSearch, combinedAlphas.length]);

  const paginatedCombinedAlphas = useMemo(
    () =>
      filteredCombinedAlphas.slice(
        (alphaPage - 1) * alphaPageSize,
        alphaPage * alphaPageSize
      ),
    [filteredCombinedAlphas, alphaPage, alphaPageSize]
  );

  const renderAlphaManagement = () => {

    return (
      <>
        {/* 알파 관리 헤더 */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: theme.spacing.lg }}>
        <div>
          <h2 style={{ margin: 0, color: theme.colors.textPrimary, fontSize: theme.typography.fontSize.h2, fontWeight: 600 }}>
            알파 관리
          </h2>
          <p style={{ margin: `${theme.spacing.sm} 0 0 0`, color: theme.colors.textSecondary }}>
            공용 알파와 개인 알파를 관리하세요
          </p>
        </div>
        <GlassButton
          variant="primary"
          icon={<PlusOutlined />}
          onClick={handleAddAlpha}
        >
          새 알파 추가
        </GlassButton>
      </div>

      <CardsGrid>
        {/* 공용 알파 섹션 */}
        <ChartCard>
          <ChartTitle style={{ display: 'flex', alignItems: 'center', gap: theme.spacing.sm }}>
            <ThunderboltOutlined style={{ color: theme.colors.accentGold }} />
            공용 알파 라이브러리
          </ChartTitle>
          <div
            style={{
              padding: theme.spacing.lg,
              background: theme.colors.liquidGlass,
              border: `1px solid ${theme.colors.liquidGlassBorder}`,
              borderRadius: '12px',
              textAlign: 'center',
            }}
          >
            <div
              style={{
                color: theme.colors.textSecondary,
                fontSize: theme.typography.fontSize.body,
                marginBottom: theme.spacing.sm,
              }}
            >
              저장된 공용 알파
            </div>
            <div
              style={{
                color: theme.colors.textPrimary,
                fontSize: theme.typography.fontSize.h3,
                fontWeight: 600,
              }}
            >
              {sharedAlphas.length}개 사용 가능
            </div>
          </div>
        </ChartCard>

        {/* 개인 알파 섹션 */}
        <ChartCard>
          <ChartTitle style={{ display: 'flex', alignItems: 'center', gap: theme.spacing.sm }}>
            <EyeOutlined style={{ color: theme.colors.accentPrimary }} />
            내 알파 컬렉션
          </ChartTitle>
          <div style={{ display: 'flex', flexDirection: 'column', gap: theme.spacing.md }}>
            <div style={{
              padding: theme.spacing.lg,
              background: theme.colors.liquidGoldGradient,
              border: `1px solid ${theme.colors.liquidGoldBorder}`,
              borderRadius: '12px',
              textAlign: 'center'
            }}>
              <div style={{ color: theme.colors.textPrimary, fontSize: theme.typography.fontSize.body, marginBottom: theme.spacing.sm, fontWeight: 600 }}>
                저장된 개인 알파
              </div>
              <div style={{ color: theme.colors.textPrimary, fontSize: theme.typography.fontSize.h3, fontWeight: 700 }}>
                {alphaSummary.private_count || privateAlphas.length}개
              </div>
            </div>
          </div>
        </ChartCard>
      </CardsGrid>

      {/* 알파 목록 */}
      <ChartCard>
        <ChartTitle>알파 목록</ChartTitle>
        <div style={{ display: 'flex', flexDirection: 'column', gap: theme.spacing.md }}>
          <Input.Search
            placeholder="알파 이름 또는 수식을 검색하세요"
            allowClear
            value={alphaSearch}
            onChange={(event) => setAlphaSearch(event.target.value)}
            onSearch={(value) => setAlphaSearch(value)}
            style={{ borderRadius: '12px' }}
          />

          {alphaLoading ? (
            <div style={{ textAlign: 'center', padding: theme.spacing.xl, color: theme.colors.textSecondary }}>
              알파 목록을 불러오는 중...
            </div>
          ) : filteredCombinedAlphas.length > 0 ? (
            paginatedCombinedAlphas.map(alpha => {
              const fitnessValue =
                typeof alpha.metadata?.fitness === 'number'
                  ? Number(alpha.metadata?.fitness)
                  : null;
              const tags = Array.isArray(alpha.tags) ? alpha.tags : [];
              const expressionDisplay =
                alpha.expression ||
                alpha.metadata?.expression ||
                alpha.metadata?.python_source ||
                '수식 정보 없음';

              return (
                <div key={alpha.id} style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: theme.spacing.lg,
                  background: alpha.source === 'private' ? theme.colors.liquidGoldGradient : theme.colors.liquidGlass,
                  border: `1px solid ${alpha.source === 'private' ? theme.colors.liquidGoldBorder : theme.colors.liquidGlassBorder}`,
                  borderRadius: '12px',
                  transition: 'all 0.3s cubic-bezier(0.16, 1, 0.3, 1)',
                }}>
                  <div style={{ flex: 1 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: theme.spacing.sm, marginBottom: theme.spacing.sm }}>
                      <span style={{
                        color: theme.colors.textPrimary,
                        fontWeight: 600,
                        fontSize: theme.typography.fontSize.body
                      }}>
                        {alpha.name}
                      </span>
                      <Tag color={alpha.source === 'private' ? 'gold' : 'blue'}>
                        {alpha.source === 'private' ? '개인' : '공용'}
                      </Tag>
                      {fitnessValue !== null && Number.isFinite(fitnessValue) && (
                        <Tag color="green">
                          적합도: {fitnessValue.toFixed(3)}
                        </Tag>
                      )}
                    </div>
                    <div style={{
                      color: theme.colors.textSecondary,
                      fontSize: theme.typography.fontSize.caption,
                      marginBottom: theme.spacing.sm
                    }}>
                      {alpha.description || '설명이 없습니다.'}
                    </div>
                    <div style={{
                      fontFamily: 'monospace',
                      fontSize: theme.typography.fontSize.caption,
                      color: theme.colors.accentGold,
                      background: theme.colors.backgroundTertiary,
                      padding: theme.spacing.sm,
                      borderRadius: '6px',
                      maxWidth: '400px',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                      wordBreak: 'break-all'
                    }}>
                      {expressionDisplay}
                    </div>
                    {tags.length > 0 && (
                      <div style={{ marginTop: theme.spacing.sm, display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                        {tags.map((tag, idx) => (
                          <Tag key={idx} style={{ fontSize: '11px' }}>
                            {tag}
                          </Tag>
                        ))}
                      </div>
                    )}
                  </div>
                  {alpha.source === 'private' && (
                    <div style={{ display: 'flex', gap: theme.spacing.sm }}>
                      <Tooltip title="편집">
                        <Button
                          type="text"
                          icon={<EditOutlined />}
                          onClick={() => handleEditAlpha(alpha)}
                          style={{ color: theme.colors.textSecondary }}
                        />
                      </Tooltip>
                      <Popconfirm
                        title="알파 삭제"
                        description="정말로 이 알파를 삭제하시겠습니까?"
                        onConfirm={() => handleDeleteAlpha(alpha.id)}
                        okText="삭제"
                        cancelText="취소"
                      >
                        <Tooltip title="삭제">
                          <Button
                            type="text"
                            danger
                            icon={<DeleteOutlined />}
                          />
                        </Tooltip>
                      </Popconfirm>
                    </div>
                  )}
                </div>
              );
            })
          ) : (
            <div style={{ textAlign: 'center', padding: theme.spacing.xl, color: theme.colors.textSecondary }}>
              <ThunderboltOutlined style={{ fontSize: '48px', marginBottom: theme.spacing.md, opacity: 0.5 }} />
              <div>아직 알파가 없습니다</div>
              <div style={{ fontSize: theme.typography.fontSize.caption, marginTop: theme.spacing.sm }}>
                새 알파를 추가하거나 공용 알파를 활용해보세요
              </div>
            </div>
          )}

          <Pagination
            current={alphaPage}
            pageSize={alphaPageSize}
            total={filteredCombinedAlphas.length}
            onChange={(page) => setAlphaPage(page)}
            showSizeChanger={false}
            hideOnSinglePage
          />
        </div>
      </ChartCard>
      </>
    );
  };

const renderSectorHeatmap = () => {
  const sectors = heatmapData?.sectors ?? [];

  return (
    <ChartCard>
      <HeatmapHeader>
        <div>
          <ChartTitle>섹터별 수익률 트리맵</ChartTitle>
          <HeatmapInfoText>
            기준일: {heatmapData?.date ?? '데이터 없음'}
          </HeatmapInfoText>
        </div>
      </HeatmapHeader>

        {heatmapLoading ? (
          <div style={{ textAlign: 'center', padding: theme.spacing.xl, color: theme.colors.textSecondary }}>
            히트맵을 불러오는 중...
          </div>
        ) : heatmapError ? (
          <div style={{ textAlign: 'center', padding: theme.spacing.xl, color: theme.colors.error }}>
            {heatmapError}
          </div>
        ) : sectors.length === 0 ? (
          <Empty description="표시할 데이터가 없습니다." />
        ) : apexHeatmapSeries.length === 0 ? (
          <div style={{ textAlign: 'center', padding: theme.spacing.xl, color: theme.colors.textSecondary }}>
            표시 가능한 티커 데이터가 없습니다.
          </div>
        ) : (
          <HeatmapWrapper>
            <ReactApexChart
              options={apexHeatmapOptions}
              series={apexHeatmapSeries as unknown as ApexAxisChartSeries}
              type="treemap"
              height={820}
            />
            {sectorSummaries.length > 0 && (
              <SectorChipRow style={{ marginTop: theme.spacing.md }}>
                {sectorSummaries.map((sector) => {
                  const isActive = Boolean(highlightSector && highlightSector === sector.name);
                  const isDimmed = Boolean(highlightSector && highlightSector !== sector.name);
                  return (
                    <SectorChip
                      key={sector.name}
                      $color={sector.color ?? theme.colors.accentPrimary}
                      $active={isActive}
                      $dimmed={isDimmed}
                      onMouseEnter={() => handleSectorChipEnter(sector.name)}
                      onMouseLeave={handleSectorChipLeave}
                      onClick={() => handleSectorChipClick(sector.name)}
                    >
                      <span style={{ fontWeight: 700 }}>{sector.name}</span>
                      <span style={{ color: theme.colors.textSecondary }}>
                        {formatMarketCap(sector.totalValue)}
                      </span>
                      <span
                        style={{
                          color: (sector.changeValue ?? 0) < 0 ? theme.colors.error : theme.colors.success,
                          fontWeight: 600,
                        }}
                      >
                        {sector.changeText}
                      </span>
                    </SectorChip>
                  );
                })}
              </SectorChipRow>
            )}
          </HeatmapWrapper>
        )}
      </ChartCard>
    );
  };

  useEffect(() => {
    const handler = (event: MouseEvent) => {
      const target = event.target as HTMLElement;
      const parentLegend = target?.closest('.apexcharts-legend');
      if (!parentLegend) {
        setActiveSectorFromLegend(null);
        setLegendLockedSector(null);
        setLegendHoverSector(null);
      }
    };

    document.addEventListener('click', handler);
    return () => {
      document.removeEventListener('click', handler);
    };
  }, []);

  return (
    <DashboardContainer>
      <DynamicIslandNav>
        <DynamicIslandButton $active={activeTab === 0} onClick={() => setActiveTab(0)}>
          시장 수익률
        </DynamicIslandButton>
        <DynamicIslandButton $active={activeTab === 1} onClick={() => setActiveTab(1)}>
          섹터별 수익률
        </DynamicIslandButton>
        <DynamicIslandButton $active={activeTab === 2} onClick={() => setActiveTab(2)}>
          알파 관리
        </DynamicIslandButton>
      </DynamicIslandNav>

      <TabContent>
        {activeTab === 0 && renderMarketPerformance()}
        {activeTab === 1 && renderSectorHeatmap()}
        {activeTab === 2 && renderAlphaManagement()}
      </TabContent>

      {/* 알파 추가/수정 모달 */}
      <Modal
        title={
          <div style={{ display: 'flex', alignItems: 'center', gap: theme.spacing.sm }}>
            <ThunderboltOutlined style={{ color: theme.colors.accentGold }} />
            {editingAlpha ? '알파 수정' : '새 알파 추가'}
          </div>
        }
        open={isAlphaModalVisible}
        onCancel={() => {
          setIsAlphaModalVisible(false);
          alphaForm.resetFields();
        }}
        footer={null}
        width={600}
        centered
        bodyStyle={{
          background: theme.colors.backgroundSecondary,
          borderRadius: '16px',
        }}
      >
        <Form
          form={alphaForm}
          layout="vertical"
          onFinish={handleSaveAlpha}
          style={{ marginTop: theme.spacing.lg }}
        >
          <Form.Item
            name="name"
            label="알파 이름"
            rules={[
              { required: true, message: '알파 이름을 입력해주세요' },
              { min: 2, message: '알파 이름은 최소 2자 이상이어야 합니다' }
            ]}
          >
            <Input
              placeholder="예: 모멘텀 전략, 가치 투자"
              style={{
                background: theme.colors.liquidGlass,
                border: `1px solid ${theme.colors.liquidGlassBorder}`,
                borderRadius: '8px',
                color: theme.colors.textPrimary,
              }}
            />
          </Form.Item>

          <Form.Item
            name="expression"
            label="알파 표현식"
            rules={[
              { required: true, message: '알파 표현식을 입력해주세요' },
              {
                pattern: /^[a-zA-Z0-9\s_(),\-+*/.]+$/,
                message: '올바른 표현식을 입력해주세요'
              }
            ]}
            help="예: ts_rank(close, 20), sma(volume, 10) 등"
          >
            <Input.TextArea
              rows={3}
              placeholder="ts_rank(close, 20), sma(volume, 10) 등"
              style={{
                background: theme.colors.liquidGlass,
                border: `1px solid ${theme.colors.liquidGlassBorder}`,
                borderRadius: '8px',
                color: theme.colors.textPrimary,
                fontFamily: 'monospace',
              }}
            />
          </Form.Item>

          <Form.Item
            name="description"
            label="설명"
          >
            <Input.TextArea
              rows={2}
              placeholder="이 알파에 대한 설명을 입력하세요"
              style={{
                background: theme.colors.liquidGlass,
                border: `1px solid ${theme.colors.liquidGlassBorder}`,
                borderRadius: '8px',
                color: theme.colors.textPrimary,
              }}
            />
          </Form.Item>

          <Form.Item
            name="fitness"
            label="적합도 (선택사항)"
            help="GA에서 계산된 적합도 값 (0.0 ~ 1.0)"
          >
            <Input
              type="number"
              min={0}
              max={1}
              step={0.001}
              placeholder="0.85"
              style={{
                background: theme.colors.liquidGlass,
                border: `1px solid ${theme.colors.liquidGlassBorder}`,
                borderRadius: '8px',
                color: theme.colors.textPrimary,
              }}
            />
          </Form.Item>

          <Form.Item
            name="tags"
            label="태그 (선택사항)"
            help="쉼표로 구분하여 입력하세요"
          >
            <Select
              mode="tags"
              placeholder="태그를 입력하세요 (예: 모멘텀, 가치, 기술적)"
              style={{
                background: theme.colors.liquidGlass,
                borderRadius: '8px',
              }}
              dropdownStyle={{
                background: theme.colors.backgroundSecondary,
                border: `1px solid ${theme.colors.border}`,
              }}
            />
          </Form.Item>

          <div style={{ display: 'flex', gap: theme.spacing.md, justifyContent: 'flex-end', marginTop: theme.spacing.xl }}>
            <GlassButton
              variant="secondary"
              onClick={() => {
                setIsAlphaModalVisible(false);
                alphaForm.resetFields();
              }}
            >
              취소
            </GlassButton>
            <GlassButton
              variant="primary"
              onClick={() => alphaForm.submit()}
            >
              {editingAlpha ? '수정' : '추가'}
            </GlassButton>
          </div>
        </Form>
      </Modal>
    </DashboardContainer>
  );
};
