import React, { useState, useEffect } from 'react';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import axios from 'axios';
import Chat from './components/Chat';
import TopBar from './components/TopBar';
import SessionList from './components/SessionList';
import ProfileManager from './components/ProfileManager';
import { Profile, Session, ProfileCreateRequest } from './types';
import './App.css';

const theme = createTheme({
  palette: {
    mode: 'dark',
    background: {
      default: '#343541',
      paper: '#444654',
    },
    grey: {
      900: '#202123', // Darker shade for sidebar
    },
    text: {
      primary: '#FFFFFF',
      secondary: '#ECECF1',
    },
    primary: {
      main: '#19C37D',
      light: '#1BD385',
      dark: '#17B374',
    },
    divider: 'rgba(0,0,0,0.1)', // Subtle divider color
  },
  typography: {
    fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif",
  },
});

const API_URL = '/api';

function App() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [showProfileManager, setShowProfileManager] = useState(false);

  const fetchSessions = async () => {
    try {
      const response = await axios.get(`${API_URL}/sessions`);
      setSessions(response.data.sessions);
    } catch (error) {
      console.error('Error fetching sessions:', error);
    }
  };

  const fetchProfiles = async () => {
    try {
      const response = await axios.get(`${API_URL}/profiles`);
      setProfiles(response.data.profiles);
    } catch (error) {
      console.error('Error fetching profiles:', error);
    }
  };

  useEffect(() => {
    fetchProfiles();
    fetchSessions();
  }, []);

  const handleSendMessage = async (message: string, profileName?: string): Promise<string> => {
    try {
      // Use provided profileName for new chats, otherwise use session's profile
      const currentSession = sessions.find(s => s.session_id === sessionId);
      const activeProfile = profileName || currentSession?.profile_name || 'default';

      const response = await axios.post(`${API_URL}/chat`, {
        text: message,
        profile_name: activeProfile,
        session_id: sessionId
      });
      
      if (!sessionId && response.data.session_id) {
        setSessionId(response.data.session_id);
        fetchSessions();
      }
      
      return response.data.response;
    } catch (error) {
      console.error('Error sending message:', error);
      throw error;
    }
  };

  const handleSelectSession = (selectedSessionId: string) => {
    setSessionId(selectedSessionId);
  };

  const handleDeleteSession = async (sessionIdToDelete: string) => {
    try {
      await axios.delete(`${API_URL}/sessions/${sessionIdToDelete}`);
      fetchSessions();
      if (sessionId === sessionIdToDelete) {
        setSessionId(null);
      }
    } catch (error) {
      console.error('Error deleting session:', error);
    }
  };

  const handleNewChat = () => {
    setSessionId(null);
  };

  const handleCreateProfile = async (profile: ProfileCreateRequest) => {
    try {
      await axios.post(`${API_URL}/profiles`, profile);
      fetchProfiles();
    } catch (error) {
      console.error('Error creating profile:', error);
      throw error;
    }
  };

  const handleUpdateProfile = async (name: string, profile: ProfileCreateRequest) => {
    try {
      await axios.put(`${API_URL}/profiles/${name}`, profile);
      fetchProfiles();
    } catch (error) {
      console.error('Error updating profile:', error);
      throw error;
    }
  };

  const handleDeleteProfile = async (name: string) => {
    try {
      await axios.delete(`${API_URL}/profiles/${name}`);
      fetchProfiles();
    } catch (error) {
      console.error('Error deleting profile:', error);
      throw error;
    }
  };

  const getCurrentProfile = () => {
    const currentSession = sessions.find(s => s.session_id === sessionId);
    return currentSession?.profile_name || 'default';
  };

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <div className="App">
        <TopBar onManageProfiles={() => setShowProfileManager(true)} />
        <div className="content-container">
          <div className="sidebar">
            <SessionList
              sessions={sessions}
              currentSessionId={sessionId}
              onSelectSession={handleSelectSession}
              onDeleteSession={handleDeleteSession}
              onNewChat={handleNewChat}
            />
          </div>
          <div className="chat-container">
            <Chat 
              onSendMessage={handleSendMessage} 
              sessionId={sessionId}
              profile={getCurrentProfile()}
              profiles={profiles}
            />
          </div>
        </div>
        <ProfileManager
          open={showProfileManager}
          onClose={() => setShowProfileManager(false)}
          profiles={profiles}
          onCreateProfile={handleCreateProfile}
          onUpdateProfile={handleUpdateProfile}
          onDeleteProfile={handleDeleteProfile}
        />
      </div>
    </ThemeProvider>
  );
}

export default App;
