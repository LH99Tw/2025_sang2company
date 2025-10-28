import React, { useMemo } from 'react';
import styled from 'styled-components';
import {
  ResponsiveContainer,
  Treemap,
  Tooltip as RechartsTooltip,
} from 'recharts';
import type { TooltipProps } from 'recharts';
import { theme } from '../styles/theme';

interface DemoNode {
  name: string;
  label?: string;
  value: number;
  change: number;
  type: 'sector' | 'industry' | 'ticker';
  children?: DemoNode[];
  sector?: string;
  industry?: string;
  close?: number;
  market_cap?: number;
  color?: string;
  fill?: string;
}

const PageContainer = styled.div`
  display: flex;
  flex-direction: column;
  gap: ${theme.spacing.lg};
  padding: ${theme.spacing.xl};
  color: ${theme.colors.textPrimary};
`;

const Title = styled.h2`
  margin: 0;
  font-size: ${theme.typography.fontSize.h2};
  font-weight: 700;
`;

const Subtitle = styled.div`
  font-size: ${theme.typography.fontSize.body};
  color: ${theme.colors.textSecondary};
`;

const TreemapWrapper = styled.div`
  width: 100%;
  height: 640px;
  background: ${theme.colors.backgroundSecondary};
  border-radius: 20px;
  border: 1px solid ${theme.colors.liquidGlassBorder};
  box-shadow: ${theme.shadows.glass};
  padding: ${theme.spacing.lg};
`;

const TooltipContainer = styled.div`
  background: ${theme.colors.backgroundSecondary};
  border: 1px solid ${theme.colors.border};
  border-radius: 8px;
  padding: ${theme.spacing.sm} ${theme.spacing.md};
  color: ${theme.colors.textPrimary};
  box-shadow: ${theme.shadows.soft};
`;

const TooltipTitle = styled.div`
  font-weight: 600;
  margin-bottom: ${theme.spacing.xs};
`;

const TooltipText = styled.div`
  font-size: ${theme.typography.fontSize.caption};
  color: ${theme.colors.textSecondary};
`;

const clampChange = (value: number): number => {
  if (!Number.isFinite(value)) return 0;
  return Math.max(-0.03, Math.min(0.03, value));
};

const formatPercent = (value: number): string => {
  return `${value >= 0 ? '+' : ''}${(value * 100).toFixed(2)}%`;
};

const getHeatmapColor = (value: number): string => {
  const clamped = clampChange(value);
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

const demoData: DemoNode[] = [
  {
    name: 'Technology',
    value: 320,
    change: 0.018,
    type: 'sector',
    children: [
      {
        name: 'Semiconductors',
        value: 180,
        change: 0.026,
        type: 'industry',
        children: [
          { name: 'NVDA', label: 'NVDA', value: 80, change: 0.031, type: 'ticker', close: 125.3 },
          { name: 'AMD', label: 'AMD', value: 40, change: 0.018, type: 'ticker', close: 111.8 },
          { name: 'AVGO', label: 'AVGO', value: 60, change: 0.009, type: 'ticker', close: 908.1 },
        ],
      },
      {
        name: 'Software',
        value: 140,
        change: -0.012,
        type: 'industry',
        children: [
          { name: 'MSFT', label: 'MSFT', value: 70, change: -0.015, type: 'ticker', close: 420.2 },
          { name: 'ORCL', label: 'ORCL', value: 40, change: -0.008, type: 'ticker', close: 131.1 },
          { name: 'CRM', label: 'CRM', value: 30, change: 0.004, type: 'ticker', close: 288.6 },
        ],
      },
    ],
  },
  {
    name: 'Consumer',
    value: 220,
    change: -0.009,
    type: 'sector',
    children: [
      {
        name: 'E-commerce',
        value: 120,
        change: 0.012,
        type: 'industry',
        children: [
          { name: 'AMZN', label: 'AMZN', value: 70, change: 0.015, type: 'ticker', close: 189.4 },
          { name: 'SHOP', label: 'SHOP', value: 30, change: 0.01, type: 'ticker', close: 82.6 },
          { name: 'MELI', label: 'MELI', value: 20, change: -0.006, type: 'ticker', close: 1250.3 },
        ],
      },
      {
        name: 'Retail',
        value: 100,
        change: -0.022,
        type: 'industry',
        children: [
          { name: 'TSLA', label: 'TSLA', value: 60, change: -0.027, type: 'ticker', close: 235.9 },
          { name: 'SBUX', label: 'SBUX', value: 25, change: -0.018, type: 'ticker', close: 92.4 },
          { name: 'NKE', label: 'NKE', value: 15, change: -0.013, type: 'ticker', close: 98.7 },
        ],
      },
    ],
  },
  {
    name: 'Financials',
    value: 180,
    change: 0.004,
    type: 'sector',
    children: [
      {
        name: 'Banks',
        value: 110,
        change: 0.006,
        type: 'industry',
        children: [
          { name: 'JPM', label: 'JPM', value: 60, change: 0.008, type: 'ticker', close: 198.4 },
          { name: 'BAC', label: 'BAC', value: 30, change: 0.005, type: 'ticker', close: 40.1 },
          { name: 'WFC', label: 'WFC', value: 20, change: -0.002, type: 'ticker', close: 53.6 },
        ],
      },
      {
        name: 'Insurance',
        value: 70,
        change: -0.002,
        type: 'industry',
        children: [
          { name: 'BRK.B', label: 'BRK.B', value: 50, change: -0.004, type: 'ticker', close: 418.2 },
          { name: 'AIG', label: 'AIG', value: 20, change: 0.003, type: 'ticker', close: 76.5 },
        ],
      },
    ],
  },
];

const decorate = (nodes: DemoNode[], parentSector?: string): DemoNode[] => {
  return nodes.map((node) => {
    if (node.children && node.children.length > 0) {
      const children = decorate(node.children, parentSector ?? node.name);
      const totalValue = children.reduce((sum, child) => sum + child.value, 0) || node.value;
      const weightedChange =
        children.reduce((sum, child) => sum + child.change * child.value, 0) || node.change * node.value;
      const aggregatedChange = totalValue ? weightedChange / totalValue : node.change;
      return {
        ...node,
        value: totalValue,
        change: aggregatedChange,
        label: node.label ?? node.name,
        color: getHeatmapColor(aggregatedChange),
        fill: getHeatmapColor(aggregatedChange),
        children,
      };
    }

    return {
      ...node,
      label: node.label ?? node.name,
      sector: parentSector ?? node.sector,
      color: getHeatmapColor(node.change),
      fill: getHeatmapColor(node.change),
    };
  });
};

const HeatmapTile: React.FC<any> = (props) => {
  const { depth, x, y, width, height, name, payload, fill } = props;
  const dataNode = (payload?.payload ?? payload ?? {}) as DemoNode;
  const value = Number(dataNode?.change ?? 0) || 0;
  const color = fill ?? dataNode?.fill ?? dataNode?.color ?? getHeatmapColor(value);
  const label = dataNode?.label ?? dataNode?.name ?? name;

  if (width <= 0 || height <= 0) {
    return null;
  }

  if (depth === 1) {
    return (
      <g>
        <rect x={x} y={y} width={width} height={height} fill={color} stroke="#1f2229" strokeWidth={1.2} />
        {width > 64 && height > 28 && (
          <text
            x={x + 14}
            y={y + 24}
            fill={theme.colors.textPrimary}
            fontSize={18}
            fontWeight={700}
            style={{ paintOrder: 'stroke' }}
            stroke="rgba(0,0,0,0.35)"
            strokeWidth={3}
          >
            {label}
          </text>
        )}
      </g>
    );
  }

  if (depth === 2) {
    return (
      <g>
        <rect x={x} y={y} width={width} height={height} fill={color} stroke="#1f2229" strokeWidth={0.8} rx={3} ry={3} />
        {width > 26 && height > 18 && (
          <text
            x={x + width / 2}
            y={y + height / 2 - 2}
            fill="#f9fafb"
            fontSize={Math.max(10, Math.min(width / 4.5, height / 2.5, 20))}
            fontWeight={700}
            textAnchor="middle"
            dominantBaseline="central"
            style={{ paintOrder: 'stroke' }}
            stroke="rgba(0,0,0,0.4)"
            strokeWidth={2}
          >
            {label}
          </text>
        )}
        {width > 30 && height > 28 && (
          <text
            x={x + width / 2}
            y={y + height / 2 + Math.min(width / 4.5, height / 2.5)}
            fill="#f9fafb"
            fontSize={Math.max(9, Math.min(width / 6, height / 3, 16))}
            textAnchor="middle"
            dominantBaseline="hanging"
            style={{ paintOrder: 'stroke' }}
            stroke="rgba(0,0,0,0.35)"
            strokeWidth={1.6}
          >
            {formatPercent(value)}
          </text>
        )}
      </g>
    );
  }

  return (
    <g>
      <rect x={x} y={y} width={width} height={height} fill={color} stroke="#1f2229" strokeWidth={1.4} />
      {width > 80 && height > 32 && (
        <text
          x={x + 16}
          y={y + 26}
          fill={theme.colors.textPrimary}
          fontSize={20}
          fontWeight={700}
          style={{ paintOrder: 'stroke' }}
          stroke="rgba(0,0,0,0.35)"
          strokeWidth={3}
        >
          {label}
        </text>
      )}
    </g>
  );
};

const renderTooltip: React.FC<TooltipProps<number, string>> = ({ active, payload }) => {
  if (!active || !payload || payload.length === 0) {
    return null;
  }
  const node = payload[0]?.payload?.payload ?? payload[0]?.payload;
  if (!node || Array.isArray(node.children)) {
    return null;
  }

  const changeValue = Number(node.change ?? 0) || 0;

  return (
    <TooltipContainer>
      <TooltipTitle>{node.label ?? node.name}</TooltipTitle>
      <TooltipText>변동: {formatPercent(changeValue)}</TooltipText>
      {node.close && <TooltipText>가격: ${node.close.toFixed(2)}</TooltipText>}
      {node.market_cap && <TooltipText>시가총액: {(node.market_cap / 1e9).toFixed(2)}B</TooltipText>}
    </TooltipContainer>
  );
};

export const HeatmapDemo: React.FC = () => {
  const data = useMemo(() => decorate(demoData), []);

  return (
    <PageContainer>
      <div>
        <Title>섹터 수익률 히트맵 (Demo)</Title>
        <Subtitle>정상적인 색상/수익률 반영 여부 점검용 가상의 데이터입니다.</Subtitle>
      </div>
      <TreemapWrapper>
        <ResponsiveContainer width="100%" height="100%">
          <Treemap
            data={data}
            dataKey="value"
            isAnimationActive={false}
            content={<HeatmapTile />}
          >
            <RechartsTooltip content={renderTooltip} />
          </Treemap>
        </ResponsiveContainer>
      </TreemapWrapper>
    </PageContainer>
  );
};

export default HeatmapDemo;
