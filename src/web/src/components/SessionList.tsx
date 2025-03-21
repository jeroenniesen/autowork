import React from 'react';
import { 
  List, 
  ListItem, 
  ListItemText, 
  IconButton, 
  Typography,
  ListItemButton,
  Button,
  Box
} from '@mui/material';
import DeleteIcon from '@mui/icons-material/Delete';
import AddIcon from '@mui/icons-material/Add';
import { styled } from '@mui/material/styles';
import { Session } from '../types';

const SessionListContainer = styled(Box)(({ theme }) => ({
  height: '100%',
  display: 'flex',
  flexDirection: 'column',
  backgroundColor: theme.palette.grey[900],
  padding: '8px',
}));

const StyledList = styled(List)({
  padding: '8px',
  flex: 1,
  overflowY: 'auto'
});

const NewChatButton = styled(Button)(({ theme }) => ({
  backgroundColor: 'transparent',
  color: theme.palette.text.primary,
  border: `1px solid ${theme.palette.divider}`,
  '&:hover': {
    backgroundColor: theme.palette.action.hover,
  },
  textTransform: 'none',
  justifyContent: 'flex-start',
  padding: '10px 16px',
  borderRadius: '8px',
  width: '100%',
}));

const StyledListItemButton = styled(ListItemButton)(({ theme }) => ({
  borderRadius: '8px',
  margin: '4px 0',
  '&.Mui-selected': {
    backgroundColor: theme.palette.action.selected,
    '&:hover': {
      backgroundColor: theme.palette.action.selected,
    }
  },
  '&:hover': {
    backgroundColor: theme.palette.action.hover,
  }
}));

interface SessionListProps {
  sessions: Session[];
  currentSessionId: string | null;
  onSelectSession: (sessionId: string) => void;
  onDeleteSession: (sessionId: string) => void;
  onNewChat: () => void;
}

const SessionList: React.FC<SessionListProps> = ({
  sessions,
  currentSessionId,
  onSelectSession,
  onDeleteSession,
  onNewChat,
}) => {
  return (
    <SessionListContainer>
      <NewChatButton
        startIcon={<AddIcon />}
        onClick={onNewChat}
      >
        New chat
      </NewChatButton>
      <StyledList>
        {sessions.map((session) => (
          <ListItem
            key={session.session_id}
            disablePadding
            secondaryAction={
              <IconButton
                edge="end"
                aria-label="delete"
                onClick={(e) => {
                  e.stopPropagation();
                  onDeleteSession(session.session_id);
                }}
                sx={{ 
                  opacity: 0,
                  color: 'text.secondary',
                  '.MuiListItem-root:hover &': { opacity: 1 },
                  '&:hover': {
                    color: 'error.main',
                  }
                }}
              >
                <DeleteIcon />
              </IconButton>
            }
          >
            <StyledListItemButton
              selected={session.session_id === currentSessionId}
              onClick={() => onSelectSession(session.session_id)}
            >
              <ListItemText
                primary={`Chat with ${session.profile_name}`}
                secondary={new Date(session.created_at).toLocaleString()}
                primaryTypographyProps={{
                  fontSize: '14px',
                  fontWeight: session.session_id === currentSessionId ? 600 : 400,
                  color: 'text.primary',
                }}
                secondaryTypographyProps={{
                  fontSize: '12px',
                  color: 'text.secondary',
                }}
              />
            </StyledListItemButton>
          </ListItem>
        ))}
        {sessions.length === 0 && (
          <ListItem>
            <ListItemText
              primary={
                <Typography color="text.secondary" variant="body2">
                  No active sessions
                </Typography>
              }
            />
          </ListItem>
        )}
      </StyledList>
    </SessionListContainer>
  );
};

export default SessionList;