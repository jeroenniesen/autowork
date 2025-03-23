import React, { useState, useRef, useEffect } from 'react';
import { Box, TextField, IconButton, Typography, Select, MenuItem, FormControl, InputLabel, CircularProgress, Collapse, Divider, Chip, Tab, Tabs, Accordion, AccordionSummary, AccordionDetails } from '@mui/material';
import SendIcon from '@mui/icons-material/Send';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import AssignmentIcon from '@mui/icons-material/Assignment';
import AutoGraphIcon from '@mui/icons-material/AutoGraph';
import PsychologyIcon from '@mui/icons-material/Psychology';
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

// New styled components for manager agent
const ManagerMessageContainer = styled(Box)(({ theme }) => ({
  display: 'flex',
  flexDirection: 'column',
  width: '100%',
}));

const TaskSection = styled(Box)(({ theme }) => ({
  marginTop: '12px',
  borderRadius: '8px',
  overflow: 'hidden',
  border: `1px solid ${theme.palette.divider}`,
}));

const ThinkingSection = styled(Box)(({ theme }) => ({
  marginTop: '12px',
  padding: '12px',
  backgroundColor: 'rgba(45, 55, 72, 0.5)',
  borderRadius: '8px',
  border: `1px solid ${theme.palette.divider}`,
}));

const TaskResult = styled(Box)(({ theme }) => ({
  padding: '12px',
  marginTop: '8px',
  backgroundColor: theme.palette.background.paper,
  borderRadius: '6px',
  border: `1px solid ${theme.palette.divider}`,
}));

const TaskChip = styled(Chip)(({ theme }) => ({
  margin: '4px',
  backgroundColor: theme.palette.primary.dark,
}));

const StyledAccordion = styled(Accordion)(({ theme }) => ({
  backgroundColor: 'rgba(30, 41, 59, 0.7)',
  color: theme.palette.text.primary,
  '&:before': {
    display: 'none',
  },
  '& .MuiAccordionSummary-root': {
    minHeight: '48px',
  },
  '& .MuiAccordionDetails-root': {
    padding: '8px 16px 16px',
  },
}));

interface Message {
  text: string;
  isUser: boolean;
  profileType?: string; // Add profileType to track if message is from manager
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
  const [isStartingNewChat, setIsStartingNewChat] = useState(false);
  const [selectedProfile, setSelectedProfile] = useState(profile);
  const [expandedTasks, setExpandedTasks] = useState<{[key: string]: boolean}>({});
  const messagesEndRef = useRef<null | HTMLDivElement>(null);

  // Function to check if a message is from a manager agent and contains tasks
  const isManagerMessage = (message: string): boolean => {
    return message.includes('# Task Results') || 
           message.includes('# Thinking Process') || 
           message.includes('TASK PLAN:');
  };

  // Function to parse and render manager agent messages
  const renderManagerMessage = (message: string) => {
    // Check for task sections
    const hasThinkingProcess = message.includes('# Thinking Process');
    const hasTaskResults = message.includes('# Task Results');
    
    // Split the message into sections
    let mainContent = message;
    let thinkingContent = '';
    let taskResults = '';
    
    if (hasThinkingProcess) {
      const parts = message.split('# Thinking Process');
      mainContent = parts[0].trim();
      const remainingContent = parts[1];
      
      if (hasTaskResults) {
        const taskParts = remainingContent.split('# Task Results');
        thinkingContent = taskParts[0].trim();
        taskResults = taskParts[1].trim();
      } else {
        thinkingContent = remainingContent.trim();
      }
    } else if (hasTaskResults) {
      const parts = message.split('# Task Results');
      mainContent = parts[0].trim();
      taskResults = parts[1].trim();
    }
    
    // Parse task results into separate tasks if possible
    const taskItems: {id: string, title: string, content: string, agent: string, status: string}[] = [];
    
    if (taskResults) {
      // Use regex to extract task information
      const taskRegex = /## Task (\d+): (.*?)(?=\n)/g;
      const statusRegex = /Status: (.*?)(?=\n)/g;
      const agentRegex = /Agent: (.*?)(?=\n)/g;
      const resultRegex = /Result: (.*?)(?=(?:## Task \d+:|$))/gs;
      
      let taskMatch;
      let i = 0;
      const taskContent = taskResults.split('## Task');
      
      // Extract tasks one by one
      while ((taskMatch = taskRegex.exec(taskResults)) !== null) {
        const taskId = `task-${i}`;
        const taskNumber = taskMatch[1];
        const taskTitle = taskMatch[2];
        
        // Find corresponding content for this task
        const fullTaskContent = taskContent[parseInt(taskNumber)];
        if (fullTaskContent) {
          const statusMatch = /Status: (.*?)(?=\n)/.exec(fullTaskContent);
          const agentMatch = /Agent: (.*?)(?=\n)/.exec(fullTaskContent);
          const resultMatch = /Result: ([\s\S]*)/.exec(fullTaskContent);
          
          taskItems.push({
            id: taskId,
            title: taskTitle,
            agent: agentMatch ? agentMatch[1].trim() : 'Unknown',
            status: statusMatch ? statusMatch[1].trim() : 'Unknown',
            content: resultMatch ? resultMatch[1].trim() : 'No result found'
          });
        }
        i++;
      }
    }
    
    // Toggle task expansion
    const handleToggleTask = (taskId: string) => {
      setExpandedTasks(prev => ({
        ...prev,
        [taskId]: !prev[taskId]
      }));
    };
    
    return (
      <ManagerMessageContainer>
        {/* Main reasoning content */}
        <MarkdownContent>
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {mainContent}
          </ReactMarkdown>
        </MarkdownContent>
        
        {/* Task section */}
        {taskItems.length > 0 && (
          <TaskSection>
            <Box sx={{ p: 1, display: 'flex', alignItems: 'center', backgroundColor: 'rgba(25, 118, 210, 0.1)' }}>
              <AssignmentIcon sx={{ mr: 1 }} />
              <Typography variant="subtitle1">
                Manager delegated {taskItems.length} task{taskItems.length > 1 ? 's' : ''}
              </Typography>
            </Box>
            
            <Divider />
            
            {taskItems.map((task) => (
              <StyledAccordion 
                key={task.id}
                expanded={expandedTasks[task.id] || false}
                onChange={() => handleToggleTask(task.id)}
              >
                <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                  <Box sx={{ display: 'flex', alignItems: 'center', width: '100%' }}>
                    <Typography sx={{ flexGrow: 1 }}>{task.title}</Typography>
                    <TaskChip 
                      size="small" 
                      label={task.agent}
                      sx={{ mr: 1 }}
                    />
                    <Chip 
                      size="small" 
                      label={task.status} 
                      color={task.status === 'success' ? 'success' : 'error'}
                    />
                  </Box>
                </AccordionSummary>
                <AccordionDetails>
                  <MarkdownContent>
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {task.content}
                    </ReactMarkdown>
                  </MarkdownContent>
                </AccordionDetails>
              </StyledAccordion>
            ))}
          </TaskSection>
        )}
        
        {/* Thinking process section */}
        {thinkingContent && (
          <StyledAccordion>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Box sx={{ display: 'flex', alignItems: 'center' }}>
                <PsychologyIcon sx={{ mr: 1 }} />
                <Typography>Thinking Process</Typography>
              </Box>
            </AccordionSummary>
            <AccordionDetails>
              <MarkdownContent>
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {thinkingContent}
                </ReactMarkdown>
              </MarkdownContent>
            </AccordionDetails>
          </StyledAccordion>
        )}
      </ManagerMessageContainer>
    );
  };

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

  const handleProfileSelect = async (newProfile: string) => {
    setSelectedProfile(newProfile);
    setIsStartingNewChat(true);
    
    // Start a new chat with the selected profile
    try {
      const response = await onSendMessage("Hello", newProfile);
      const agentMsg = { text: response, isUser: false };
      setMessages([agentMsg]);
    } catch (error) {
      console.error('Error starting new chat:', error);
      const errorMsg = { text: "Sorry, I couldn't start a new conversation.", isUser: false };
      setMessages([errorMsg]);
    } finally {
      setIsStartingNewChat(false);
    }
  };

  if (!sessionId && messages.length === 0 && !isStartingNewChat) {
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

  if (isStartingNewChat) {
    return (
      <WelcomeContainer>
        <CircularProgress size={40} />
        <Typography variant="body1" gutterBottom>
          Starting new conversation with {selectedProfile} profile...
        </Typography>
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
                    isManagerMessage(message.text) ? (
                      renderManagerMessage(message.text)
                    ) : (
                      <MarkdownContent>
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                          {message.text}
                        </ReactMarkdown>
                      </MarkdownContent>
                    )
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