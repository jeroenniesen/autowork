import React from 'react';
import { Box } from '@mui/material';
import { keyframes } from '@mui/material/styles';
import { styled } from '@mui/material/styles';

const bounce = keyframes`
  0%, 80%, 100% { 
    transform: translateY(0);
  }
  40% { 
    transform: translateY(-5px);
  }
`;

const TypingContainer = styled(Box)(({ theme }) => ({
  display: 'flex',
  gap: '4px',
  padding: '8px 12px',
  backgroundColor: theme.palette.background.paper,
  borderRadius: '8px',
  width: 'fit-content',
  marginBottom: '10px',
  marginLeft: '1rem', // Align to the left like bot messages
}));

const Dot = styled('div')(({ theme }) => ({
  width: '8px',
  height: '8px',
  backgroundColor: theme.palette.primary.main,
  borderRadius: '50%',
  animation: `${bounce} 1s infinite`,
  '&:nth-of-type(2)': {
    animationDelay: '0.2s',
  },
  '&:nth-of-type(3)': {
    animationDelay: '0.4s',
  },
}));

const TypingIndicator: React.FC = () => {
  return (
    <TypingContainer>
      <Dot />
      <Dot />
      <Dot />
    </TypingContainer>
  );
};

export default TypingIndicator;