import React, { useState, useRef } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import styled from 'styled-components';
import {
  DashboardOutlined,
  ExperimentOutlined,
  FundOutlined,
  RobotOutlined,
  ThunderboltOutlined,
  StockOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  UserOutlined
} from '@ant-design/icons';
import { theme } from '../../styles/theme';
import { useSidebar } from './Layout';

const SidebarContainer = styled.nav<{ $collapsed: boolean; $sidebarPosition: number }>`
  width: ${props => props.$collapsed ? '60px' : '240px'};
  height: ${props => props.$collapsed ? 'auto' : '100vh'};
  background: ${props => props.$collapsed 
    ? 'rgba(41, 42, 45, 0.95)' 
    : theme.colors.backgroundSecondary
  };
  border: ${props => props.$collapsed 
    ? '1px solid rgba(255, 255, 255, 0.1)' 
    : `1px solid ${theme.colors.border}`
  };
  border-right: ${props => props.$collapsed ? 'none' : `1px solid ${theme.colors.border}`};
  padding: ${props => props.$collapsed ? '12px 8px' : theme.spacing.lg};
  display: flex;
  flex-direction: column;
  gap: ${props => props.$collapsed ? '0' : theme.spacing.md};
  position: fixed;
  left: ${props => props.$collapsed ? '20px' : '0'};
  top: ${props => props.$collapsed ? `${props.$sidebarPosition}%` : '0'};
  transform: ${props => props.$collapsed ? 'translateY(-50%)' : 'none'};
  transition: ${props => props.$collapsed 
    ? `width 0.4s cubic-bezier(0.16, 1, 0.3, 1), 
       height 0.35s cubic-bezier(0.16, 1, 0.3, 1) 0.05s,
       border-radius 0.3s cubic-bezier(0.16, 1, 0.3, 1) 0.1s,
       backdrop-filter 0.25s cubic-bezier(0.16, 1, 0.3, 1) 0.15s,
       box-shadow 0.3s cubic-bezier(0.16, 1, 0.3, 1) 0.1s,
       left 0.4s cubic-bezier(0.16, 1, 0.3, 1) 0.05s,
       top 0.35s cubic-bezier(0.16, 1, 0.3, 1) 0.1s,
       transform 0.35s cubic-bezier(0.16, 1, 0.3, 1) 0.1s,
       padding 0.3s cubic-bezier(0.16, 1, 0.3, 1) 0.05s`
    : `width 0.4s cubic-bezier(0.16, 1, 0.3, 1) 0.1s,
       height 0.35s cubic-bezier(0.16, 1, 0.3, 1) 0.05s,
       border-radius 0.3s cubic-bezier(0.16, 1, 0.3, 1) 0.05s,
       backdrop-filter 0.25s cubic-bezier(0.16, 1, 0.3, 1) 0.05s,
       box-shadow 0.3s cubic-bezier(0.16, 1, 0.3, 1) 0.05s,
       left 0.4s cubic-bezier(0.16, 1, 0.3, 1) 0.1s,
       top 0.35s cubic-bezier(0.16, 1, 0.3, 1) 0.05s,
       transform 0.35s cubic-bezier(0.16, 1, 0.3, 1) 0.05s,
       padding 0.3s cubic-bezier(0.16, 1, 0.3, 1) 0.1s`
  };
  z-index: 100;
  overflow: hidden;
  border-radius: ${props => props.$collapsed ? '28px' : '0'};
  backdrop-filter: ${props => props.$collapsed ? 'blur(20px)' : 'none'};
  box-shadow: ${props => props.$collapsed 
    ? '0 8px 32px rgba(0, 0, 0, 0.3), 0 0 0 1px rgba(255, 255, 255, 0.05)' 
    : 'none'
  };
`;

const Logo = styled.div<{ $collapsed: boolean }>`
  display: flex;
  align-items: center;
  justify-content: ${props => props.$collapsed ? 'center' : 'flex-start'};
  gap: ${props => props.$collapsed ? '0' : theme.spacing.md};
  color: ${theme.colors.textPrimary};
  font-size: ${theme.typography.fontSize.h3};
  font-weight: 700;
  margin-bottom: ${props => props.$collapsed ? '0' : theme.spacing.xl};
  padding: ${props => props.$collapsed ? '8px 12px' : theme.spacing.md};
  min-height: ${props => props.$collapsed ? '36px' : '48px'};
  width: ${props => props.$collapsed ? '44px' : 'auto'};
  border-radius: ${props => props.$collapsed ? '12px' : '0'};
  transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);
  
  .logo-icon {
    font-size: ${props => props.$collapsed ? '20px' : '28px'};
    transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);
    color: #FFFFFF;
    display: flex;
    align-items: center;
    justify-content: center;
    width: ${props => props.$collapsed ? '26px' : '34px'};
    height: ${props => props.$collapsed ? '26px' : '34px'};
    border-radius: 50%;
  }
  
  .logo-text {
    opacity: ${props => props.$collapsed ? 0 : 1};
    transform: ${props => props.$collapsed ? 'translateX(-8px)' : 'translateX(0)'};
    transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);
    white-space: nowrap;
    overflow: hidden;
  }
`;

const NavItem = styled.div<{ $active: boolean; $collapsed: boolean }>`
  display: flex;
  align-items: center;
  justify-content: ${props => props.$collapsed ? 'center' : 'flex-start'};
  gap: ${props => props.$collapsed ? '0' : theme.spacing.md};
  padding: ${props => props.$collapsed ? '6px' : '12px 16px'};
  border-radius: ${props => props.$collapsed ? '12px' : '12px'};
  color: ${(props: { $active: boolean }) => props.$active ? '#FFFFFF' : theme.colors.textSecondary};
  background: ${(props: { $active: boolean, $collapsed: boolean }) => 
    props.$active 
      ? (props.$collapsed ? theme.colors.liquidGoldGradient : theme.colors.liquidGoldGradient)
      : 'transparent'
  };
  border: ${(props: { $active: boolean, $collapsed: boolean }) => 
    props.$active 
      ? (props.$collapsed ? `1px solid ${theme.colors.liquidGoldBorder}` : `1px solid ${theme.colors.liquidGoldBorder}`)
      : '1px solid transparent'
  };
  cursor: pointer;
  transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);
  font-weight: ${(props: { $active: boolean }) => props.$active ? '600' : '400'};
  position: relative;
  overflow: hidden;
  min-height: ${props => props.$collapsed ? '32px' : '44px'};
  width: ${props => props.$collapsed ? '32px' : 'auto'};
  margin: ${props => props.$collapsed ? '2px auto' : '0'};
  text-align: left;

  &:hover {
    background: ${props => props.$collapsed 
      ? theme.colors.liquidGoldHover 
      : theme.colors.liquidGlassHover
    };
    color: #FFFFFF;
    transform: ${props => props.$collapsed ? 'scale(1.1)' : 'translateX(4px)'};
    box-shadow: ${props => props.$collapsed 
      ? '0 4px 12px rgba(212, 175, 55, 0.3)' 
      : 'none'
    };
  }
  
  &::before {
    content: '';
    position: absolute;
    left: 0;
    top: 0;
    bottom: 0;
    width: 3px;
    background: ${theme.colors.accentPrimary};
    transform: scaleY(${(props: { $active: boolean }) => props.$active ? 1 : 0});
    transition: transform 0.4s cubic-bezier(0.25, 0.46, 0.45, 0.94);
    display: ${props => props.$collapsed ? 'none' : 'block'};
  }

  .anticon {
    font-size: ${props => props.$collapsed ? '16px' : '20px'};
    min-width: ${props => props.$collapsed ? '16px' : '20px'};
    width: ${props => props.$collapsed ? '16px' : '20px'};
    height: ${props => props.$collapsed ? '16px' : '20px'};
    display: flex;
    align-items: center;
    justify-content: center;
    transition: font-size 0.4s cubic-bezier(0.25, 0.46, 0.45, 0.94);
  }
  
  .nav-label {
    opacity: ${(props: { $collapsed: boolean }) => props.$collapsed ? 0 : 1};
    transition: opacity 0.4s cubic-bezier(0.25, 0.46, 0.45, 0.94);
    white-space: nowrap;
    overflow: hidden;
  }
`;

const NavSection = styled.div<{ $collapsed: boolean }>`
  margin-top: ${props => props.$collapsed ? '0' : theme.spacing.lg};
  display: flex;
  flex-direction: column;
  align-items: ${props => props.$collapsed ? 'center' : 'stretch'};
  gap: ${props => props.$collapsed ? '4px' : '0'};
  
  /* 토글 상태에서 첫 번째 섹션은 마진 없음 */
  &:first-of-type {
    margin-top: 0;
  }
`;

const SectionTitle = styled.div<{ $collapsed: boolean }>`
  color: ${theme.colors.textTertiary};
  font-size: ${theme.typography.fontSize.caption};
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  margin-bottom: ${theme.spacing.sm};
  padding: 0 16px;
  opacity: ${props => props.$collapsed ? 0 : 1};
  transition: opacity 0.3s;
`;

const BottomButtonContainer = styled.div<{ $collapsed: boolean }>`
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: ${props => props.$collapsed ? '12px' : 'auto'};
  align-self: ${props => props.$collapsed ? 'center' : 'flex-start'};
  width: ${props => props.$collapsed ? 'auto' : '100%'};
`;

const ProfileButton = styled.button`
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border-radius: 12px;
  background: ${theme.colors.liquidGlass};
  border: 1px solid ${theme.colors.border};
  color: ${theme.colors.textSecondary};
  cursor: pointer;
  transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);
  
  &:hover {
    background: ${theme.colors.liquidGlassHover};
    color: ${theme.colors.accentPrimary};
    border-color: ${theme.colors.accentPrimary};
    transform: scale(1.05);
  }
  
  .anticon {
    font-size: 16px;
  }
`;

const CollapseButton = styled.button<{ $collapsed: boolean }>`
  display: flex;
  align-items: center;
  justify-content: center;
  width: ${props => props.$collapsed ? '40px' : '40px'};
  height: ${props => props.$collapsed ? '40px' : '40px'};
  border-radius: 12px;
  background: ${props => props.$collapsed 
    ? theme.colors.liquidGold 
    : theme.colors.liquidGlass
  };
  border: ${props => props.$collapsed 
    ? `1px solid ${theme.colors.liquidGoldBorder}` 
    : `1px solid ${theme.colors.border}`
  };
  color: ${props => props.$collapsed ? theme.colors.accentPrimary : theme.colors.textSecondary};
  cursor: pointer;
  transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);
  
  &:hover {
    background: ${props => props.$collapsed 
      ? 'rgba(138, 180, 248, 0.2)' 
      : theme.colors.liquidGlassHover
    };
    color: ${theme.colors.accentPrimary};
    border-color: ${theme.colors.accentPrimary};
    transform: ${props => props.$collapsed ? 'scale(1.1)' : 'scale(1.05)'};
    box-shadow: ${props => props.$collapsed 
      ? '0 4px 12px rgba(138, 180, 248, 0.3)' 
      : 'none'
    };
  }
  
  .anticon {
    font-size: ${props => props.$collapsed ? '16px' : '16px'};
    transition: font-size 0.4s cubic-bezier(0.25, 0.46, 0.45, 0.94);
  }
`;

export const Sidebar: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { collapsed, setCollapsed } = useSidebar();
  const [sidebarPosition, setSidebarPosition] = useState(50); // 0-100% 범위
  const sidebarRef = useRef<HTMLDivElement>(null);

  const menuItems = [
    { path: '/', icon: <DashboardOutlined />, label: '대시보드' },
  ];

  const analysisItems = [
    { path: '/backtest', icon: <ExperimentOutlined />, label: '백테스트' },
    { path: '/portfolio', icon: <FundOutlined />, label: '포트폴리오' },
    { path: '/explorer', icon: <StockOutlined />, label: '종목 탐색' },
  ];

  const alphaItems = [
    { path: '/alpha-pool', icon: <ThunderboltOutlined />, label: '알파 풀' },
    { path: '/alpha-incubator', icon: <RobotOutlined />, label: '알파 부화장' },
  ];

  const tradingItems = [
    { path: '/simulation', icon: <StockOutlined />, label: '모의투자' },
  ];

  return (
    <SidebarContainer ref={sidebarRef} $collapsed={collapsed} $sidebarPosition={sidebarPosition}>
      <Logo $collapsed={collapsed}>
        <span className="logo-icon">○</span>
        <span className="logo-text">LAB</span>
      </Logo>
      
      {collapsed ? (
        // 토글 상태: 모든 아이템을 하나의 컨테이너에
        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', alignItems: 'center' }}>
          {menuItems.map(item => (
            <NavItem
              key={item.path}
              $active={location.pathname === item.path}
              $collapsed={collapsed}
              onClick={() => navigate(item.path)}
            >
              {item.icon}
              <span className="nav-label">{item.label}</span>
            </NavItem>
          ))}
          {analysisItems.map(item => (
            <NavItem
              key={item.path}
              $active={location.pathname === item.path}
              $collapsed={collapsed}
              onClick={() => navigate(item.path)}
            >
              {item.icon}
              <span className="nav-label">{item.label}</span>
            </NavItem>
          ))}
          {alphaItems.map(item => (
            <NavItem
              key={item.path}
              $active={location.pathname === item.path}
              $collapsed={collapsed}
              onClick={() => navigate(item.path)}
            >
              {item.icon}
              <span className="nav-label">{item.label}</span>
            </NavItem>
          ))}
          {tradingItems.map(item => (
            <NavItem
              key={item.path}
              $active={location.pathname === item.path}
              $collapsed={collapsed}
              onClick={() => navigate(item.path)}
            >
              {item.icon}
              <span className="nav-label">{item.label}</span>
            </NavItem>
          ))}
        </div>
      ) : (
        // 오픈 상태: 섹션별로 구분
        <>
          <NavSection $collapsed={collapsed}>
            {menuItems.map(item => (
              <NavItem
                key={item.path}
                $active={location.pathname === item.path}
                $collapsed={collapsed}
                onClick={() => navigate(item.path)}
              >
                {item.icon}
                <span className="nav-label">{item.label}</span>
              </NavItem>
            ))}
          </NavSection>

          <NavSection $collapsed={collapsed}>
            <SectionTitle $collapsed={collapsed}>분석</SectionTitle>
            {analysisItems.map(item => (
              <NavItem
                key={item.path}
                $active={location.pathname === item.path}
                $collapsed={collapsed}
                onClick={() => navigate(item.path)}
              >
                {item.icon}
                <span className="nav-label">{item.label}</span>
              </NavItem>
            ))}
          </NavSection>

          <NavSection $collapsed={collapsed}>
            <SectionTitle $collapsed={collapsed}>알파 팩토리</SectionTitle>
            {alphaItems.map(item => (
              <NavItem
                key={item.path}
                $active={location.pathname === item.path}
                $collapsed={collapsed}
                onClick={() => navigate(item.path)}
              >
                {item.icon}
                <span className="nav-label">{item.label}</span>
              </NavItem>
            ))}
          </NavSection>

          <NavSection $collapsed={collapsed}>
            <SectionTitle $collapsed={collapsed}>투자</SectionTitle>
            {tradingItems.map(item => (
              <NavItem
                key={item.path}
                $active={location.pathname === item.path}
                $collapsed={collapsed}
                onClick={() => navigate(item.path)}
              >
                {item.icon}
                <span className="nav-label">{item.label}</span>
              </NavItem>
            ))}
          </NavSection>
        </>
      )}

      <BottomButtonContainer $collapsed={collapsed}>
        {!collapsed && (
          <ProfileButton onClick={() => navigate('/profile')}>
            <UserOutlined />
          </ProfileButton>
        )}
        
        <CollapseButton 
          $collapsed={collapsed} 
          onClick={() => setCollapsed(!collapsed)}
          onMouseDown={(e) => {
            if (!collapsed) return;
            e.preventDefault();
            const startY = e.clientY;
            const startPosition = sidebarPosition;
            
                const handleMouseMove = (e: MouseEvent) => {
                  const deltaY = e.clientY - startY;
                  const viewportHeight = window.innerHeight;
                  const sidebarHeight = sidebarRef.current?.offsetHeight || 0;
                  const leftPadding = 20; // 좌측 패딩

                  // 최소/최대 위치 계산 (좌측 패딩 고려)
                  const minAllowedPosition = ((leftPadding + sidebarHeight / 2) / viewportHeight) * 100;
                  const maxAllowedPosition = ((viewportHeight - leftPadding - sidebarHeight / 2) / viewportHeight) * 100;

                  // 즉시 반응하도록 실시간 계산
                  const newPosition = startPosition + (deltaY / viewportHeight) * 100;
                  const clampedPosition = Math.max(minAllowedPosition, Math.min(maxAllowedPosition, newPosition));
                  
                  // 즉시 업데이트 (지연 없음)
                  setSidebarPosition(clampedPosition);
                };
            
            const handleMouseUp = () => {
              document.removeEventListener('mousemove', handleMouseMove);
              document.removeEventListener('mouseup', handleMouseUp);
            };
            
            document.addEventListener('mousemove', handleMouseMove);
            document.addEventListener('mouseup', handleMouseUp);
          }}
          style={{ cursor: collapsed ? 'ns-resize' : 'pointer' }}
        >
          {collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
        </CollapseButton>
      </BottomButtonContainer>
    </SidebarContainer>
  );
};
