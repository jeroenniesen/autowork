import React, { useState, useRef, useEffect } from 'react';
import { Box, TextField, IconButton, Paper, Typography, Select, MenuItem, FormControl, InputLabel } from '@mui/material';
import SendIcon from '@mui/icons-material/Send';
import { styled } from '@mui/material/styles';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import TypingIndicator from './TypingIndicator';
import axios from 'axios';
import { Profile } from '../types';

const API_URL = 'http://localhost:8000';

const ChatContainer = styled(Box)(({ theme }) => ({
  height: '100%',
  display: 'flex',
  flexDirection: 'column',
  backgroundColor: theme.palette.background.default
}));

const MessagesContainer = styled(Box)(({ theme }) => ({
  flex: 1,
  overflow: 'auto',
  padding: '20px',
  display: 'flex',
  flexDirection: 'column',
  maxWidth: '800px',
  margin: '0 auto',
  width: '100%'
}));

const MessageBubble = styled(Box, {
  shouldForwardProp: (prop) => prop !== 'isUser'
})<{ isUser?: boolean }>(({ theme, isUser }) => ({
  padding: '20px',
  width: '100%',
  backgroundColor: isUser ? theme.palette.background.default : theme.palette.background.paper,
  transition: 'background-color 0.2s ease',
  '&:hover': {
    backgroundColor: isUser ? 
      'rgba(52, 53, 65, 0.9)' : // Slightly lighter version of default background
      'rgba(68, 70, 84, 0.9)',  // Slightly lighter version of paper background
  },
  '& .message-content': {
    maxWidth: '48rem',
    margin: isUser ? '0 0 0 auto' : '0 auto 0 0',
    padding: '0 1rem',
    width: 'fit-content',
  },
  '& + &': { // Add space between messages
    marginTop: '1px',
  }
}));

const InputContainer = styled(Box)(({ theme }) => ({
  padding: '24px',
  backgroundColor: theme.palette.background.default,
  borderTop: `1px solid ${theme.palette.divider}`,
  position: 'relative',
  maxWidth: '800px',
  margin: '0 auto',
  width: '100%'
}));

const StyledInputWrapper = styled(Box)(({ theme }) => ({
  maxWidth: '800px',
  margin: '0 auto',
  position: 'relative',
}));

const MarkdownContent = styled('div')(({ theme }) => ({
  textAlign: 'left',
  color: theme.palette.text.primary,
  '& p': {
    margin: '0 0 1em 0',
    lineHeight: '1.6',
    '&:last-child': {
      marginBottom: 0,
    }
  },
  '& pre': {
    backgroundColor: 'rgba(0,0,0,0.3)',
    padding: '12px',
    borderRadius: '6px',
    overflow: 'auto',
    fontSize: '0.9em',
  },
  '& code': {
    backgroundColor: 'rgba(0,0,0,0.2)',
    padding: '2px 4px',
    borderRadius: '4px',
    fontSize: '0.9em',
  },
  '& ul, & ol': {
    marginTop: '4px',
    marginBottom: '4px',
    paddingLeft: '20px',
  },
  '& table': {
    borderCollapse: 'collapse',
    width: '100%',
    marginBottom: '1em',
    '& th, & td': {
      border: `1px solid ${theme.palette.divider}`,
      padding: '8px',
    },
  },
  '& blockquote': {
    margin: '1em 0',
    padding: '0 1em',
    borderLeft: `3px solid ${theme.palette.primary.main}`,
    color: theme.palette.text.secondary,
  },
}));

const ProfileSelect = styled(FormControl)(({ theme }) => ({
  maxWidth: '600px',
  margin: '40px auto',
  width: '100%',
  '& .MuiInputLabel-root': {
    color: theme.palette.text.secondary,
  },
  '& .MuiSelect-root': {
    backgroundColor: theme.palette.background.paper,
  },
}));

const WelcomeContainer = styled(Box)(({ theme }) => ({
  height: '100%',
  display: 'flex',
  flexDirection: 'column',
  justifyContent: 'center',
  alignItems: 'center',
  gap: '20px',
  padding: '20px',
  textAlign: 'center',
  color: theme.palette.text.secondary,
}));

interface Message {
  text: string;
  isUser: boolean;
}

interface ChatProps {
  onSendMessage: (message: string, profileName?: string) => Promise<string>;
  sessionId: string | null;
  profile: string;
  profiles: Profile[];
}

const Chat: React.FC<ChatProps> = ({ onSendMessage, sessionId, profile, profiles }) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const [selectedProfile, setSelectedProfile] = useState(profile);
  const messagesEndRef = useRef<null | HTMLDivElement>(null);

  // Load chat history when switching sessions
  useEffect(() => {
    const loadHistory = async () => {
      if (sessionId) {
        setIsLoadingHistory(true);
        try {
          const response = await axios.get(`${API_URL}/sessions/${sessionId}/history`);
          setMessages(response.data.messages);
        } catch (error) {
          console.error('Error loading chat history:', error);
          setMessages([]);
        } finally {
          setIsLoadingHistory(false);
        }
      } else {
        // Clear messages when no session is selected
        setMessages([]);
      }
    };

    loadHistory();
  }, [sessionId]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage = input.trim();
    setInput('');
    setIsLoading(true);

    const userMsg = { text: userMessage, isUser: true };
    setMessages(prev => [...prev, userMsg]);

    try {
      // Only pass profile for new chats
      const response = await onSendMessage(userMessage, !sessionId ? selectedProfile : undefined);
      const agentMsg = { text: response, isUser: false };
      setMessages(prev => [...prev, agentMsg]);
    } catch (error) {
      const errorMsg = { text: "Sorry, I couldn't process your message.", isUser: false };
      setMessages(prev => [...prev, errorMsg]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (event: React.KeyboardEvent) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      handleSend();
    }
  };

  const handleProfileSelect = (newProfile: string) => {
    setSelectedProfile(newProfile);
    // Start a new chat with the selected profile
    onSendMessage("Hello", newProfile).catch(console.error);
  };

  if (!sessionId && messages.length === 0) {
    return (
      <WelcomeContainer>
        <Typography variant="h4" gutterBottom>
          Welcome to Agent Chat
        </Typography>
        <Typography variant="body1" gutterBottom>
          Select an agent profile to start a new conversation
        </Typography>
        <ProfileSelect>
          <InputLabel>Select Profile</InputLabel>
          <Select
            value={selectedProfile}
            label="Select Profile"
            onChange={(e) => handleProfileSelect(e.target.value)}
          >
            {profiles.map((profile) => (
              <MenuItem key={profile.name} value={profile.name}>
                {profile.description}
              </MenuItem>
            ))}
          </Select>
        </ProfileSelect>
      </WelcomeContainer>
    );
  }

  return (
    <ChatContainer>
      <MessagesContainer>
        {isLoadingHistory ? (
          <Box display="flex" justifyContent="center" alignItems="center" height="100%">
            <TypingIndicator />
          </Box>
        ) : (
          <>
            {messages.length === 0 && !isLoading && (
              <Box 
                display="flex" 
                justifyContent="center" 
                alignItems="center" 
                height="100%"
                color="text.secondary"
              >
                <Typography variant="body1">
                  Start a new conversation
                </Typography>
              </Box>
            )}
            {messages.map((message, index) => (
              <MessageBubble key={index} isUser={message.isUser}>
                <Box className="message-content">
                  {message.isUser ? (
                    <Typography>{message.text}</Typography>
                  ) : (
                    <MarkdownContent>
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {message.text}
                      </ReactMarkdown>
                    </MarkdownContent>
                  )}
                </Box>
              </MessageBubble>
            ))}
            {isLoading && <TypingIndicator />}
            <div ref={messagesEndRef} />
          </>
        )}
      </MessagesContainer>
      <InputContainer>
        <StyledInputWrapper>
          <TextField
            fullWidth
            multiline
            maxRows={4}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder={isLoadingHistory ? "Loading history..." : "Type a message..."}
            disabled={isLoading || isLoadingHistory}
            sx={{
              '& .MuiInputBase-root': {
                backgroundColor: theme => theme.palette.background.paper,
                borderRadius: '8px',
                padding: '12px',
                '& .MuiInputBase-input': {
                  color: theme => theme.palette.text.primary,
                },
              },
              '& .MuiOutlinedInput-notchedOutline': {
                borderColor: 'rgba(255, 255, 255, 0.1)',
              },
              '&:hover .MuiOutlinedInput-notchedOutline': {
                borderColor: 'rgba(255, 255, 255, 0.2)',
              },
            }}
          />
          <IconButton
            color="primary"
            onClick={handleSend}
            disabled={isLoading || isLoadingHistory || !input.trim()}
            sx={{
              position: 'absolute',
              right: '8px',
              bottom: '8px',
              backgroundColor: theme => theme.palette.primary.main,
              color: 'white',
              '&:hover': {
                backgroundColor: theme => theme.palette.primary.dark,
              },
              '&.Mui-disabled': {
                backgroundColor: 'rgba(255, 255, 255, 0.1)',
                color: 'rgba(255, 255, 255, 0.3)',
              },
            }}
          >
            <SendIcon />
          </IconButton>
        </StyledInputWrapper>
      </InputContainer>
    </ChatContainer>
  );
};

export default Chat;