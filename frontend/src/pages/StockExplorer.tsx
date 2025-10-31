import React, { useCallback, useEffect, useMemo, useState } from 'react';
import styled from 'styled-components';
import { Input, Select, Button, Table, Tag, Space, message, Modal, Form } from 'antd';
import { CaretDownOutlined, CaretUpOutlined } from '@ant-design/icons';
import type { ColumnsType, TableProps } from 'antd/es/table';
import { theme } from '../styles/theme';
import { getExplorerList, ExplorerListParams, getFactorsList, getStocks } from '../services/api';

const Container = styled.div`
  display: flex;
  flex-direction: column;
  gap: ${theme.spacing.lg};
`;

const Filters = styled.div`
  display: grid;
  grid-template-columns: 1.5fr 1fr 1fr 1fr 1.2fr 1.5fr auto auto;
  gap: ${theme.spacing.md};
  align-items: center;
`;

const Title = styled.h1`
  font-size: ${theme.typography.fontSize.h2};
  color: ${theme.colors.textPrimary};
  margin: 0;
`;

type Row = {
  Ticker: string;
  Name: string;
  Sector: string;
  Close: number;
  DailyReturn: number;
  Vol20: number;
  Market_Cap: number | null;
  SizeBucket: 'large' | 'mid' | 'small';
  AlphaScore?: number | null;
};

export const StockExplorer: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [rows, setRows] = useState<Row[]>([]);
  const [sectors, setSectors] = useState<string[]>([]);
  const [params, setParams] = useState<ExplorerListParams>({
    sort_by: 'change_pct',
    order: 'desc',
    limit: 200,
  });

  const [search, setSearch] = useState('');
  // 알파: 보유 알파 선택 중심 (수식 입력 제거)
  const [alphaFactor, setAlphaFactor] = useState<string | undefined>(undefined);
  const [factorOptions, setFactorOptions] = useState<{label:string,value:string}[]>([]);

  const [saveModal, setSaveModal] = useState(false);
  const [saveName, setSaveName] = useState('');
  // Tech filters
  const [rsiPeriod] = useState<number>(14);
  const [rsiPreset, setRsiPreset] = useState<string | undefined>(undefined);
  const [macdPreset, setMacdPreset] = useState<string | undefined>(undefined);

  const fetchData = useCallback(async (override?: Partial<ExplorerListParams>) => {
    setLoading(true);
    // 프리셋 → 수치 범위 변환
    const rsiRange = (() => {
      switch (rsiPreset) {
        case 'overbought': return { rsi_min: 70, rsi_max: 100 };
        case 'oversold': return { rsi_min: 0, rsi_max: 30 };
        case 'above50': return { rsi_min: 50, rsi_max: 100 };
        case 'below50': return { rsi_min: 0, rsi_max: 50 };
        case 'neutral': return { rsi_min: 30, rsi_max: 70 };
        default: return {} as any;
      }
    })();
    const macdRange = (() => {
      switch (macdPreset) {
        case 'positive': return { macd_hist_min: 0.0, macd_hist_max: undefined };
        case 'negative': return { macd_hist_min: undefined, macd_hist_max: 0.0 };
        case 'near_zero': return { macd_hist_min: -0.002, macd_hist_max: 0.002 };
        case 'strong_positive': return { macd_hist_min: 0.01, macd_hist_max: undefined };
        case 'strong_negative': return { macd_hist_min: undefined, macd_hist_max: -0.01 };
        default: return {} as any;
      }
    })();

    let res: any = null;
    try {
      res = await getExplorerList({
        ...params,
        ...override,
        q: search || undefined,
        alpha_factor: alphaFactor,
        rsi_period: rsiPeriod as any,
        ...(rsiRange as any),
        ...(macdRange as any),
      });
    } catch (err) {
      res = null;
    }

    let finalRows: Row[] = [];
    let finalSectors: string[] = [];

    const consumeExplorer = (payload: any) => {
      finalRows = (payload.rows || []) as Row[];
      finalSectors = (payload.sectors && payload.sectors.length)
        ? payload.sectors
        : Array.from(new Set((payload.rows || []).map((x: any) => String(x.Sector || '')).filter((s: string) => !!s))) as string[];
    };

    if (res && res.success && (res.rows || []).length) {
      consumeExplorer(res);
    } else {
      let plain: any = null;
      try {
        plain = await getStocks({
          q: search || undefined,
          sector: (params.sector as string) || undefined,
          order: params.sort_by === 'ticker' ? 'ticker' : 'market_cap',
          dir: params.order || 'desc',
          limit: params.limit || 200,
          offset: 0,
        });
      } catch (err) {
        plain = null;
      }

      if (plain && plain.success && (plain.rows || []).length) {
        finalRows = (plain.rows || []).map((r: any) => ({
          Ticker: r.Ticker,
          Name: r.Name,
          Sector: r.Sector,
          Close: Number(r.Close ?? 0),
          DailyReturn: Number(r.DailyReturn ?? 0),
          Vol20: Number.isFinite(r.Vol20) ? Number(r.Vol20) : 0,
          Market_Cap: Number(r.Market_Cap ?? 0),
          SizeBucket: (r.SizeBucket as any) || 'mid',
          AlphaScore: null,
        }));
        finalSectors = Array.from(new Set((plain.rows || []).map((x: any) => String(x.Sector || '')).filter((s: string) => !!s))) as string[];
      } else {
        message.error(res?.error || plain?.error || '종목 목록을 불러오지 못했습니다');
      }
    }

    setRows(finalRows);
    setSectors(finalSectors);
    setLoading(false);
  }, [params, search, alphaFactor, rsiPreset, macdPreset, rsiPeriod]);

  useEffect(() => {
    fetchData();
    (async () => {
      try {
        const f = await getFactorsList();
        const opts = (f.metadata || [])?.map((m:any)=>({label:m.name||m.title||m.id,value:m.name})) ||
                     (f.factors||[]).map((x:string)=>({label:x,value:x}));
        setFactorOptions(opts);
      } catch {}
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  type SortKey = NonNullable<ExplorerListParams['sort_by']> | 'ticker';

  const handleSort = useCallback((key: SortKey, forcedOrder?: 'asc' | 'desc') => {
    setParams(prev => {
      const nextOrder: 'asc' | 'desc' = forcedOrder ?? (prev.sort_by === key
        ? (prev.order === 'desc' ? 'asc' : 'desc')
        : 'desc');
      const nextState: ExplorerListParams = {
        ...prev,
        sort_by: key as ExplorerListParams['sort_by'],
        order: nextOrder,
      };
      fetchData({ sort_by: nextState.sort_by, order: nextState.order });
      return nextState;
    });
  }, [fetchData]);

  const renderSortableHeader = useCallback((label: string, key: SortKey) => {
    const active = params.sort_by === key;
    const isDesc = params.order === 'desc';
    return (
      <span
        style={{ cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: 4 }}
        onClick={() => handleSort(key)}
      >
        {label}
        {active && (isDesc ? <CaretDownOutlined /> : <CaretUpOutlined />)}
      </span>
    );
  }, [handleSort, params.order, params.sort_by]);

  const getSortOrder = useCallback((key: SortKey) => {
    if (params.sort_by !== key) return undefined;
    return params.order === 'desc' ? 'descend' : 'ascend';
  }, [params.order, params.sort_by]);

  const columns: ColumnsType<Row> = useMemo(() => [
    {
      title: renderSortableHeader('티커', 'ticker'),
      dataIndex: 'Ticker',
      key: 'Ticker',
      width: 100,
      sorter: true,
      sortOrder: getSortOrder('ticker'),
      render: (v: string) => <Tag color={theme.colors.accentGold}>{v}</Tag>,
    },
    {
      title: '종목명',
      dataIndex: 'Name',
      key: 'Name',
      width: 240,
      ellipsis: true,
    },
    {
      title: '섹터',
      dataIndex: 'Sector',
      key: 'Sector',
      width: 160,
    },
    {
      title: renderSortableHeader('현재가', 'close'),
      dataIndex: 'Close',
      key: 'Close',
      align: 'right',
      width: 120,
      sorter: true,
      sortOrder: getSortOrder('close'),
      render: (v: number) => `$${(v ?? 0).toFixed(2)}`,
    },
    {
      title: renderSortableHeader('1일 수익률', 'change_pct'),
      dataIndex: 'DailyReturn',
      key: 'DailyReturn',
      align: 'right',
      width: 120,
      sorter: true,
      sortOrder: getSortOrder('change_pct'),
      render: (v: number) => <span style={{ color: v >= 0 ? '#ff6b6b' : '#4dabf7' }}>{(v * 100).toFixed(2)}%</span>,
    },
    {
      title: renderSortableHeader('변동성(20일)', 'volatility'),
      dataIndex: 'Vol20',
      key: 'Vol20',
      align: 'right',
      width: 130,
      sorter: true,
      sortOrder: getSortOrder('volatility'),
      render: (v: number) => `${((v || 0) * 100).toFixed(2)}%`,
    },
    {
      title: '규모',
      dataIndex: 'SizeBucket',
      key: 'SizeBucket',
      width: 90,
      render: (v: Row['SizeBucket']) => <Tag>{v}</Tag>,
    },
    {
      title: renderSortableHeader('알파 점수', 'alpha_score'),
      dataIndex: 'AlphaScore',
      key: 'AlphaScore',
      align: 'right',
      width: 120,
      sorter: true,
      sortOrder: getSortOrder('alpha_score'),
      render: (v?: number | null) => (v != null ? (v * 100).toFixed(1) : '-')
    },
  ], [getSortOrder, renderSortableHeader]);

  type TableChangeArgs = Parameters<NonNullable<TableProps<Row>['onChange']>>;
  const handleTableChange = useCallback((...args: TableChangeArgs) => {
    const sorter = args[2];
    if (!sorter) return;
    const single = Array.isArray(sorter) ? sorter[0] : sorter;
    if (!single || !single.order) return;
    const order = single.order === 'ascend' ? 'asc' : single.order === 'descend' ? 'desc' : undefined;
    if (!order) return;
    let key: SortKey = 'change_pct';
    switch (single.field) {
      case 'Ticker': key = 'ticker'; break;
      case 'Close': key = 'close'; break;
      case 'DailyReturn': key = 'change_pct'; break;
      case 'Vol20': key = 'volatility'; break;
      case 'AlphaScore': key = 'alpha_score'; break;
      default: key = 'change_pct';
    }
    handleSort(key, order);
  }, [handleSort]);

  return (
    <>
    <Container>
      <Space direction="vertical" size="middle">
        <Title>종목 탐색</Title>
        <Filters>
          <Input.Search 
            placeholder="티커/종목명 검색"
            allowClear
            value={search}
            onChange={e => setSearch(e.target.value)}
            onSearch={() => fetchData()}
          />
          <Select 
            mode="multiple"
            placeholder="섹터"
            allowClear
            options={sectors.map(s => ({ label: s, value: s }))}
            onChange={(vals) => { const v = (vals as string[]).join(','); setParams(p => ({ ...p, sector: v || undefined })); }}
          />
          <Select
            mode="multiple"
            placeholder="규모"
            allowClear
            options={[{value:'large',label:'대형'},{value:'mid',label:'중형'},{value:'small',label:'소형'}]}
            onChange={(vals) => { const v = (vals as string[]).join(','); setParams(p => ({ ...p, size: v || undefined })); }}
          />
          <Select
            value={params.sort_by}
            options={[
              { value: 'change_pct', label: '일간 수익률' },
              { value: 'volatility', label: '변동성' },
              { value: 'market_cap', label: '시가총액' },
              { value: 'close', label: '현재가' },
              { value: 'alpha_score', label: '알파 점수' },
              { value: 'ticker', label: '티커' },
            ]}
            onChange={(v) => setParams(p => {
              const next = { ...p, sort_by: v as any };
              fetchData({ sort_by: next.sort_by, order: next.order });
              return next;
            })}
          />
          <Select
            value={params.order}
            options={[{value:'desc',label:'내림차순'},{value:'asc',label:'오름차순'}]}
            onChange={(v) => setParams(p => {
              const next = { ...p, order: v as any };
              fetchData({ sort_by: next.sort_by, order: next.order });
              return next;
            })}
          />
          <Select
            showSearch
            allowClear
            placeholder="내 알파 선택"
            style={{ minWidth: 220 }}
            options={factorOptions}
            value={alphaFactor}
            onChange={(v) => setAlphaFactor(v || undefined)}
          />
          <Button onClick={()=>setSaveModal(true)}>필터 저장</Button>
          <Button type="primary" onClick={() => fetchData()} loading={loading}>적용</Button>
        </Filters>
        <Space wrap>
          <Tag color="gold">RSI</Tag>
          <Select
            placeholder="RSI 범위"
            allowClear
            style={{ minWidth: 180 }}
            options={[
              { value: 'overbought', label: '과매수(≥70)' },
              { value: 'neutral', label: '중립(30~70)' },
              { value: 'oversold', label: '과매도(≤30)' },
              { value: 'above50', label: '50 이상' },
              { value: 'below50', label: '50 미만' },
            ]}
            value={rsiPreset}
            onChange={(v)=>setRsiPreset(v)}
          />
          <Tag color="gold">MACD</Tag>
          <Select
            placeholder="MACD 히스토그램"
            allowClear
            style={{ minWidth: 200 }}
            options={[
              { value: 'positive', label: '양수(>0)' },
              { value: 'negative', label: '음수(<0)' },
              { value: 'near_zero', label: '제로근처(-0.002~0.002)' },
              { value: 'strong_positive', label: '강한 양수(>0.01)' },
              { value: 'strong_negative', label: '강한 음수(<-0.01)' },
            ]}
            value={macdPreset}
            onChange={(v)=>setMacdPreset(v)}
          />
          <Button onClick={()=>fetchData()}>기술 필터 적용</Button>
        </Space>
     </Space>

      <Table<Row>
        rowKey={(r) => r.Ticker}
        columns={columns}
        dataSource={rows}
        loading={loading}
        pagination={{ pageSize: 50 }}
        bordered
        size="middle"
        onChange={handleTableChange}
      />
    </Container>

    <Modal
      title="현재 필터 저장"
      open={saveModal}
      onCancel={()=>setSaveModal(false)}
      onOk={async ()=>{
        try{
          const payload = { name: saveName || `filter_${Date.now()}`, params: { ...params, q: search, alpha_factor: alphaFactor, rsi_preset: rsiPreset, macd_preset: macdPreset } };
          const res = await fetch('/api/explorer/filters/save', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload), credentials:'include' });
          const data = await res.json();
          if(data.success){ message.success('저장되었습니다'); setSaveModal(false); setSaveName(''); }
          else{ message.error(data.error || '저장 실패'); }
        }catch(e:any){ message.error(e.message||'저장 실패'); }
      }}
    >
      <Form layout="vertical">
        <Form.Item label="필터 이름">
          <Input value={saveName} onChange={(e)=>setSaveName(e.target.value)} placeholder="예: 대형주_상승률TOP" />
        </Form.Item>
      </Form>
    </Modal>
    </>
  );
};

export default StockExplorer;
