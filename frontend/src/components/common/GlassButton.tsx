import React, { ReactNode } from 'react';
import styled from 'styled-components';
import { theme } from '../../styles/theme';

interface GlassButtonProps {
  children: ReactNode;
  onClick?: ((event?: any) => void) | ((event?: any) => Promise<void>);
  variant?: 'primary' | 'secondary';
  disabled?: boolean;
  loading?: boolean;
  icon?: ReactNode;
  loadingIcon?: ReactNode;
  className?: string;
  style?: React.CSSProperties;
}

const PrimaryButton = styled.button`
  background: ${theme.colors.liquidGoldGradient};
  backdrop-filter: blur(15px);
  color: #FFFFFF;
  border: 1px solid ${theme.colors.liquidGoldBorder};
  border-radius: 12px;
  padding: 12px 24px;
  font-weight: 600;
  font-size: 16px;
  cursor: pointer;
  transition: all ${theme.transitions.spring};
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  position: relative;
  overflow: hidden;

  &::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: ${theme.colors.liquidGoldGradient};
    opacity: 0;
    transition: opacity ${theme.transitions.spring};
  }

  &:hover:not(:disabled) {
    transform: translateY(-2px);
    box-shadow: 0 8px 32px rgba(212, 175, 55, 0.3);
    border-color: ${theme.colors.liquidGoldBorder};
    color: #FFFFFF;
    
    &::before {
      opacity: 1;
    }
  }

  &:active:not(:disabled) {
    transform: translateY(0);
  }

  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
`;

const SecondaryButton = styled.button`
  background: ${theme.colors.liquidGlass};
  border: 1px solid ${theme.colors.liquidGlassBorder};
  color: ${theme.colors.textPrimary};
  border-radius: 8px;
  padding: 12px 24px;
  font-weight: 600;
  font-size: 16px;
  cursor: pointer;
  backdrop-filter: blur(10px);
  transition: all ${theme.transitions.spring};
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;

  &:hover:not(:disabled) {
    background: rgba(255, 255, 255, 0.1);
    border-color: ${theme.colors.accentGold};
    color: ${theme.colors.accentGold};
  }

  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
`;

export const GlassButton: React.FC<GlassButtonProps> = ({ 
  children, 
  onClick, 
  variant = 'primary', 
  disabled = false,
  loading = false,
  icon,
  loadingIcon,
  className,
  style,
}) => {
  const ButtonComponent = variant === 'primary' ? PrimaryButton : SecondaryButton;

  return (
    <ButtonComponent 
      onClick={onClick} 
      disabled={disabled || loading}
      className={className}
      style={style}
    >
      {(loading ? (loadingIcon || icon) : icon) && (
        <span>
          {loading ? (loadingIcon || icon) : icon}
        </span>
      )}
      {children}
    </ButtonComponent>
  );
};
