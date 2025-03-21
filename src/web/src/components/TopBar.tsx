import React from 'react';
import { AppBar, Toolbar, Typography, Button } from '@mui/material';
import { styled } from '@mui/material/styles';
import SettingsIcon from '@mui/icons-material/Settings';

const StyledAppBar = styled(AppBar)({
  backgroundColor: '#128C7E',
});

export interface Profile {
  name: string;
  description: string;
}

interface TopBarProps {
  onManageProfiles: () => void;
}

const TopBar: React.FC<TopBarProps> = ({ onManageProfiles }) => {
  return (
    <StyledAppBar position="static">
      <Toolbar>
        <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
          Agent Chat
        </Typography>
        <Button
          startIcon={<SettingsIcon />}
          onClick={onManageProfiles}
          sx={{
            color: 'white',
            '&:hover': {
              backgroundColor: 'rgba(255, 255, 255, 0.1)',
            },
          }}
        >
          Manage Profiles
        </Button>
      </Toolbar>
    </StyledAppBar>
  );
};

export default TopBar;