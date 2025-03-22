import React from 'react';
import { AppBar, Toolbar, Typography, Button, Box } from '@mui/material';
import { styled } from '@mui/material/styles';
import SettingsIcon from '@mui/icons-material/Settings';
import LibraryBooksIcon from '@mui/icons-material/LibraryBooks';

const StyledAppBar = styled(AppBar)({
  backgroundColor: '#128C7E',
});

export interface Profile {
  name: string;
  description: string;
}

interface TopBarProps {
  onManageProfiles: () => void;
  onManageKnowledgeSets: () => void;
}

const TopBar: React.FC<TopBarProps> = ({ onManageProfiles, onManageKnowledgeSets }) => {
  return (
    <StyledAppBar position="static">
      <Toolbar>
        <Typography variant="h6" component="div">
          AutoWork
        </Typography>
        <Box sx={{ display: 'flex', gap: 1, marginLeft: 'auto' }}>
          <Button
            startIcon={<LibraryBooksIcon />}
            onClick={onManageKnowledgeSets}
            sx={{
              color: 'white',
              '&:hover': {
                backgroundColor: 'rgba(255, 255, 255, 0.1)',
              },
            }}
          >
            Knowledge Sets
          </Button>
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
        </Box>
      </Toolbar>
    </StyledAppBar>
  );
};

export default TopBar;