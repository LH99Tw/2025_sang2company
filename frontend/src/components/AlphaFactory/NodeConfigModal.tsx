import React, { useEffect, useState } from 'react';
import styled from 'styled-components';
import { Modal, Select, DatePicker, InputNumber, Progress, message, Switch } from 'antd';
import { theme } from '../../styles/theme';
import { GlassButton } from '../common/GlassButton';
import dayjs from 'dayjs';

const { RangePicker } = DatePicker;

const ModalContent = styled.div`
  display: flex;
  flex-direction: column;
  gap: ${theme.spacing.lg};
`;

const FormGroup = styled.div`
  display: flex;
  flex-direction: column;
  gap: ${theme.spacing.sm};
`;

const Label = styled.label`
  color: ${theme.colors.textPrimary};
  font-size: ${theme.typography.fontSize.body};
  font-weight: 600;
`;

const Description = styled.p`
  color: ${theme.colors.textSecondary};
  font-size: ${theme.typography.fontSize.caption};
  margin: 0;
`;

const SummaryCard = styled.div`
  background: ${theme.colors.liquidGlass};
  border: 1px solid ${theme.colors.liquidGlassBorder};
  border-radius: 12px;
  padding: ${theme.spacing.md};
  display: flex;
  flex-direction: column;
  gap: ${theme.spacing.sm};
`;

const SummaryItem = styled.div`
  display: flex;
  justify-content: space-between;
  color: ${theme.colors.textPrimary};
  font-size: ${theme.typography.fontSize.caption};
  
  .label {
    color: ${theme.colors.textSecondary};
  }
  
  .value {
    font-weight: 600;
  }
`;

interface NodeConfigModalProps {
  visible: boolean;
  nodeType: 'data' | 'backtest' | 'ga' | 'evolution' | 'results';
  nodeData: any;
  onSave: (data: any) => void;
  onClose: () => void;
}

export const NodeConfigModal: React.FC<NodeConfigModalProps> = ({
  visible,
  nodeType,
  nodeData,
  onSave,
  onClose,
}) => {
  const [formData, setFormData] = useState(nodeData || {});

  useEffect(() => {
    if (visible) {
      setFormData(nodeData || {});
    }
  }, [nodeData, visible]);

  const handleSave = () => {
    onSave(formData);
    message.success('설정이 저장되었습니다');
    onClose();
  };

  const renderContent = () => {
    switch (nodeType) {
      case 'data':
        return (
          <ModalContent>
            <FormGroup>
              <Label>데이터 소스</Label>
              <Description>백테스트에 사용할 데이터를 선택하세요</Description>
              <Select
                value={formData.dataSource || 'sp500'}
                onChange={(value) => setFormData({ ...formData, dataSource: value })}
                options={[
                  { label: 'S&P 500', value: 'sp500' },
                  { label: 'NASDAQ 100 (준비중)', value: 'nasdaq100', disabled: true },
                  { label: 'KOSPI 200 (준비중)', value: 'kospi200', disabled: true },
                ]}
                style={{ width: '100%' }}
              />
            </FormGroup>

            <FormGroup>
              <Label>날짜 범위</Label>
              <Description>분석할 데이터의 기간을 설정하세요</Description>
              <RangePicker
                value={formData.dateRange ? [
                  dayjs(formData.dateRange[0]),
                  dayjs(formData.dateRange[1])
                ] : undefined}
                onChange={(dates) => {
                  if (dates) {
                    setFormData({
                      ...formData,
                      dateRange: [dates[0]?.format('YYYY-MM-DD'), dates[1]?.format('YYYY-MM-DD')]
                    });
                  }
                }}
                style={{ width: '100%' }}
              />
            </FormGroup>

            <SummaryCard>
              <SummaryItem>
                <span className="label">데이터 소스:</span>
                <span className="value">{formData.dataSource === 'sp500' ? 'S&P 500' : formData.dataSource}</span>
              </SummaryItem>
              <SummaryItem>
                <span className="label">예상 종목 수:</span>
                <span className="value">500개</span>
              </SummaryItem>
            </SummaryCard>
          </ModalContent>
        );

      case 'backtest':
        return (
          <ModalContent>
            <FormGroup>
              <Label>리밸런싱 주기</Label>
              <Description>포트폴리오를 재조정하는 주기를 선택하세요</Description>
              <Select
                value={formData.rebalancingFrequency || 'weekly'}
                onChange={(value) => setFormData({ ...formData, rebalancingFrequency: value })}
                options={[
                  { label: '일별 (Daily)', value: 'daily' },
                  { label: '주별 (Weekly)', value: 'weekly' },
                  { label: '월별 (Monthly)', value: 'monthly' },
                  { label: '분기별 (Quarterly)', value: 'quarterly' },
                ]}
                style={{ width: '100%' }}
              />
            </FormGroup>

            <FormGroup>
              <Label>거래 비용 (%)</Label>
              <Description>매수/매도 시 발생하는 거래 비용</Description>
              <InputNumber
                value={formData.transactionCost ? formData.transactionCost * 100 : 0.1}
                onChange={(value) => setFormData({ ...formData, transactionCost: (value || 0.1) / 100 })}
                min={0}
                max={5}
                step={0.01}
                formatter={value => `${value}%`}
                parser={value => parseFloat(value?.replace('%', '') || '0')}
                style={{ width: '100%' }}
              />
            </FormGroup>

            <FormGroup>
              <Label>Quantile (%)</Label>
              <Description>상위/하위 몇 %의 종목을 선택할지 설정</Description>
              <InputNumber
                value={formData.quantile ? formData.quantile * 100 : 10}
                onChange={(value) => setFormData({ ...formData, quantile: (value || 10) / 100 })}
                min={1}
                max={50}
                step={1}
                formatter={value => `${value}%`}
                parser={value => parseFloat(value?.replace('%', '') || '10')}
                style={{ width: '100%' }}
              />
            </FormGroup>

            <SummaryCard>
              <SummaryItem>
                <span className="label">리밸런싱:</span>
                <span className="value">
                  {formData.rebalancingFrequency === 'daily' ? '일별' :
                   formData.rebalancingFrequency === 'weekly' ? '주별' :
                   formData.rebalancingFrequency === 'monthly' ? '월별' : '분기별'}
                </span>
              </SummaryItem>
              <SummaryItem>
                <span className="label">거래 비용:</span>
                <span className="value">{((formData.transactionCost || 0.001) * 100).toFixed(2)}%</span>
              </SummaryItem>
              <SummaryItem>
                <span className="label">선택 비율:</span>
                <span className="value">상위/하위 {((formData.quantile || 0.1) * 100).toFixed(0)}%</span>
              </SummaryItem>
            </SummaryCard>
          </ModalContent>
        );

      case 'ga':
        return (
          <ModalContent>
            <FormGroup>
              <Label>개체 수 (Population Size)</Label>
              <Description>각 세대에서 유지할 알파의 개수</Description>
              <InputNumber
                value={formData.populationSize || 50}
                onChange={(value) => setFormData({ ...formData, populationSize: value })}
                min={10}
                max={200}
                step={10}
                style={{ width: '100%' }}
              />
            </FormGroup>

            <FormGroup>
              <Label>세대 수 (Generations)</Label>
              <Description>진화 알고리즘을 반복할 횟수</Description>
              <InputNumber
                value={formData.generations || 20}
                onChange={(value) => setFormData({ ...formData, generations: value })}
                min={5}
                max={100}
                step={5}
                style={{ width: '100%' }}
              />
            </FormGroup>

            <FormGroup>
              <Label>트리 최대 깊이 (Max Tree Depth)</Label>
              <Description>수식 트리가 가질 수 있는 최대 연산 단계</Description>
              <InputNumber
                value={formData.maxDepth || 6}
                onChange={(value) => setFormData({ ...formData, maxDepth: value })}
                min={2}
                max={50}
                step={1}
                style={{ width: '100%' }}
              />
            </FormGroup>

            <FormGroup>
              <Label>최종 생존 수 (Elite Count)</Label>
              <Description>세대 종료 후 보존할 상위 알파 개수</Description>
              <InputNumber
                value={formData.maxAlphas || 10}
                onChange={(value) => setFormData({ ...formData, maxAlphas: value })}
                min={1}
                max={50}
                step={1}
                style={{ width: '100%' }}
              />
            </FormGroup>

            <FormGroup>
              <Label>시드 알파 수 (Registry Seeds)</Label>
              <Description>레지스트리에서 초기 부모로 사용할 알파 개수</Description>
              <InputNumber
                value={formData.registrySeedLimit ?? 16}
                onChange={(value) => setFormData({ ...formData, registrySeedLimit: value })}
                min={1}
                max={200}
                step={1}
                style={{ width: '100%' }}
              />
            </FormGroup>

            <FormGroup>
              <Label>시드 셔플 여부</Label>
              <Description>실행마다 레지스트리 시드를 무작위로 선택합니다</Description>
              <Switch
                checked={formData.registrySeedShuffle ?? false}
                onChange={(checked) => setFormData({ ...formData, registrySeedShuffle: checked })}
              />
            </FormGroup>

            <SummaryCard>
              <SummaryItem>
                <span className="label">총 진화 횟수:</span>
                <span className="value">{(formData.populationSize || 50) * (formData.generations || 20)} 회</span>
              </SummaryItem>
              <SummaryItem>
                <span className="label">트리 깊이:</span>
                <span className="value">{formData.maxDepth || 6} 단계</span>
              </SummaryItem>
              <SummaryItem>
                <span className="label">예상 소요 시간:</span>
                <span className="value">약 {Math.ceil((formData.generations || 20) * 0.5)} 분</span>
              </SummaryItem>
              <SummaryItem>
                <span className="label">최종 선별:</span>
                <span className="value">{formData.maxAlphas || 10} 개</span>
              </SummaryItem>
              <SummaryItem>
                <span className="label">시드/셔플:</span>
                <span className="value">
                  {(formData.registrySeedLimit ?? 16)}개 / {formData.registrySeedShuffle ? '랜덤' : '고정'}
                </span>
              </SummaryItem>
            </SummaryCard>
          </ModalContent>
        );

      case 'evolution':
        return (
          <ModalContent>
            <FormGroup>
              <Label>진화 진행 상태</Label>
              <Description>유전 알고리즘의 진행 상황을 표시합니다</Description>
              <Progress
                percent={formData.progress || 0}
                status={formData.status === 'failed' ? 'exception' : 'active'}
                strokeColor={{
                  '0%': theme.colors.accentPrimary,
                  '100%': theme.colors.accentGold,
                }}
              />
            </FormGroup>

            <SummaryCard>
              <SummaryItem>
                <span className="label">현재 세대:</span>
                <span className="value">{formData.currentGeneration || 0} / {formData.totalGenerations || 20}</span>
              </SummaryItem>
              <SummaryItem>
                <span className="label">최고 적합도:</span>
                <span className="value">{formData.bestFitness?.toFixed(4) || '-'}</span>
              </SummaryItem>
              <SummaryItem>
                <span className="label">상태:</span>
                <span className="value">
                  {formData.status === 'running' ? '실행 중' :
                   formData.status === 'completed' ? '완료' :
                   formData.status === 'failed' ? '실패' : '대기 중'}
                </span>
              </SummaryItem>
            </SummaryCard>
          </ModalContent>
        );

      case 'results':
        return (
          <ModalContent>
            <FormGroup>
              <Label>GA 실행 결과</Label>
              <Description>생성된 알파 팩터의 요약 정보</Description>
            </FormGroup>

            <SummaryCard>
              <SummaryItem>
                <span className="label">생성된 알파 수:</span>
                <span className="value">{formData.alphas?.length || 0} 개</span>
              </SummaryItem>
              <SummaryItem>
                <span className="label">평균 적합도:</span>
                <span className="value">
                  {formData.alphas?.length > 0
                    ? (formData.alphas.reduce((sum: number, a: any) => sum + (a.fitness || 0), 0) / formData.alphas.length).toFixed(4)
                    : '-'}
                </span>
              </SummaryItem>
              <SummaryItem>
                <span className="label">최고 적합도:</span>
                <span className="value">
                  {formData.alphas?.length > 0
                    ? Math.max(...formData.alphas.map((a: any) => a.fitness || 0)).toFixed(4)
                    : '-'}
                </span>
              </SummaryItem>
            </SummaryCard>

            {formData.alphas?.length > 0 && (
              <FormGroup>
                <Label>상위 3개 알파</Label>
                {formData.alphas.slice(0, 3).map((alpha: any, index: number) => (
                  <SummaryCard key={index}>
                    <SummaryItem>
                      <span className="label">#{index + 1}</span>
                      <span className="value">적합도: {alpha.fitness?.toFixed(4)}</span>
                    </SummaryItem>
                    <div style={{ 
                      color: theme.colors.textSecondary, 
                      fontSize: theme.typography.fontSize.caption,
                      fontFamily: theme.typography.fontFamily.display,
                      wordBreak: 'break-all'
                    }}>
                      {alpha.expression}
                    </div>
                  </SummaryCard>
                ))}
              </FormGroup>
            )}
          </ModalContent>
        );

      default:
        return <div>설정 없음</div>;
    }
  };

  const getTitle = () => {
    switch (nodeType) {
      case 'data': return '데이터 소스 설정';
      case 'backtest': return '백테스트 조건 설정';
      case 'ga': return 'GA 엔진 설정';
      case 'evolution': return '진화 과정';
      case 'results': return '최종 결과';
      default: return '설정';
    }
  };

  return (
    <Modal
      title={getTitle()}
      open={visible}
      onCancel={onClose}
      footer={nodeType !== 'evolution' && nodeType !== 'results' ? [
        <GlassButton key="cancel" variant="secondary" onClick={onClose}>
          취소
        </GlassButton>,
        <GlassButton key="save" variant="primary" onClick={handleSave}>
          저장
        </GlassButton>,
      ] : [
        <GlassButton key="close" variant="primary" onClick={onClose}>
          닫기
        </GlassButton>,
      ]}
      width={600}
      styles={{
        body: {
          maxHeight: '70vh',
          overflowY: 'auto',
        },
      }}
    >
      {renderContent()}
    </Modal>
  );
};
