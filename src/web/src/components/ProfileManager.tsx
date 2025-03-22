import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  IconButton,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  Box,
  Typography,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  SelectChangeEvent,
  Chip,
  OutlinedInput,
} from '@mui/material';
import { Delete as DeleteIcon, Edit as EditIcon } from '@mui/icons-material';
import axios from 'axios';
import { Profile, ProfileConfig, ProfileCreateRequest } from '../types';

const API_URL = '/api';

interface KnowledgeSet {
  name: string;
  description: string;
  document_count: number;
}

interface ProfileManagerProps {
  open: boolean;
  onClose: () => void;
  profiles: Profile[];
  onCreateProfile: (profile: ProfileCreateRequest) => Promise<void>;
  onUpdateProfile: (name: string, profile: ProfileCreateRequest) => Promise<void>;
  onDeleteProfile: (name: string) => Promise<void>;
}

const defaultProfileConfig: ProfileConfig = {
  name: '',
  description: '',
  model: {
    provider: 'ollama',
    name: 'phi4-mini',
    temperature: 0.7,
  },
  agent: {
    persona: 'You are a helpful assistant.',
    type: 'conversation',
  },
  memory: {
    type: 'conversation_buffer',
    max_token_limit: 2000,
  },
  knowledge_sets: [],
};

const ProfileManager: React.FC<ProfileManagerProps> = ({
  open,
  onClose,
  profiles,
  onCreateProfile,
  onUpdateProfile,
  onDeleteProfile,
}) => {
  const [editingProfile, setEditingProfile] = useState<ProfileConfig | null>(null);
  const [showEditDialog, setShowEditDialog] = useState(false);
  const [knowledgeSets, setKnowledgeSets] = useState<KnowledgeSet[]>([]);

  useEffect(() => {
    fetchKnowledgeSets();
  }, []);

  const fetchKnowledgeSets = async () => {
    try {
      const response = await axios.get(`${API_URL}/knowledge-sets`);
      setKnowledgeSets(response.data.knowledge_sets);
    } catch (error) {
      console.error('Error fetching knowledge sets:', error);
    }
  };

  const handleCreate = () => {
    setEditingProfile({ ...defaultProfileConfig });
    setShowEditDialog(true);
  };

  const handleEdit = async (profileName: string) => {
    try {
      const response = await fetch(`${API_URL}/profiles/${profileName}`);
      if (!response.ok) throw new Error('Failed to fetch profile');
      const data = await response.json();
      setEditingProfile({
        name: data.name,
        description: data.description,
        model: data.config.model,
        agent: data.config.agent,
        memory: data.config.memory,
        knowledge_sets: data.config.knowledge_sets || [],
      });
      setShowEditDialog(true);
    } catch (error) {
      console.error('Error fetching profile:', error);
    }
  };

  const handleSubmit = async () => {
    if (!editingProfile) return;

    const profileData: ProfileCreateRequest = {
      name: editingProfile.name,
      description: editingProfile.description,
      model: editingProfile.model,
      agent: editingProfile.agent,
      memory: editingProfile.memory,
      knowledge_sets: editingProfile.knowledge_sets,
    };

    try {
      const existingProfile = profiles.find(p => p.name === editingProfile.name);
      if (existingProfile) {
        await onUpdateProfile(editingProfile.name, profileData);
      } else {
        await onCreateProfile(profileData);
      }
      setShowEditDialog(false);
      setEditingProfile(null);
    } catch (error) {
      console.error('Error saving profile:', error);
    }
  };

  const handleModelProviderChange = (event: SelectChangeEvent<string>) => {
    if (!editingProfile) return;
    setEditingProfile({
      ...editingProfile,
      model: {
        ...editingProfile.model,
        provider: event.target.value,
      },
    });
  };

  const handleKnowledgeSetsChange = (event: SelectChangeEvent<string[]>) => {
    if (!editingProfile) return;
    setEditingProfile({
      ...editingProfile,
      knowledge_sets: event.target.value as string[],
    });
  };

  const handleAgentTypeChange = (event: SelectChangeEvent<string>) => {
    if (!editingProfile) return;
    setEditingProfile({
      ...editingProfile,
      agent: {
        ...editingProfile.agent,
        type: event.target.value,
      },
    });
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>Manage Profiles</DialogTitle>
      <DialogContent>
        <Box sx={{ mb: 2 }}>
          <Button variant="contained" color="primary" onClick={handleCreate}>
            Create New Profile
          </Button>
        </Box>
        <List>
          {profiles.map((profile) => (
            <ListItem key={profile.name}>
              <ListItemText
                primary={profile.name}
                secondary={profile.description}
              />
              <ListItemSecondaryAction>
                <IconButton edge="end" onClick={() => handleEdit(profile.name)}>
                  <EditIcon />
                </IconButton>
                <IconButton
                  edge="end"
                  onClick={() => onDeleteProfile(profile.name)}
                  disabled={profile.name === 'default'}
                >
                  <DeleteIcon />
                </IconButton>
              </ListItemSecondaryAction>
            </ListItem>
          ))}
        </List>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Close</Button>
      </DialogActions>

      {/* Edit/Create Dialog */}
      <Dialog open={showEditDialog} onClose={() => setShowEditDialog(false)} maxWidth="md" fullWidth>
        <DialogTitle>
          {editingProfile?.name ? `Edit Profile: ${editingProfile.name}` : 'Create New Profile'}
        </DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 2 }}>
            <TextField
              label="Name"
              value={editingProfile?.name || ''}
              onChange={(e) => setEditingProfile(prev => prev ? { ...prev, name: e.target.value } : null)}
              disabled={!!profiles.find(p => p.name === editingProfile?.name)}
            />
            <TextField
              label="Description"
              value={editingProfile?.description || ''}
              onChange={(e) => setEditingProfile(prev => prev ? { ...prev, description: e.target.value } : null)}
            />
            
            <Typography variant="h6" sx={{ mt: 2 }}>Model Configuration</Typography>
            <FormControl fullWidth>
              <InputLabel>Provider</InputLabel>
              <Select
                value={editingProfile?.model.provider || ''}
                onChange={handleModelProviderChange}
                label="Provider"
              >
                <MenuItem value="ollama">Ollama</MenuItem>
                <MenuItem value="openai">OpenAI</MenuItem>
                <MenuItem value="anthropic">Anthropic</MenuItem>
              </Select>
            </FormControl>
            <TextField
              label="Model Name"
              value={editingProfile?.model.name || ''}
              onChange={(e) => setEditingProfile(prev => prev ? {
                ...prev,
                model: { ...prev.model, name: e.target.value }
              } : null)}
            />
            <TextField
              label="Temperature"
              type="number"
              inputProps={{ min: 0, max: 1, step: 0.1 }}
              value={editingProfile?.model.temperature || 0.7}
              onChange={(e) => setEditingProfile(prev => prev ? {
                ...prev,
                model: { ...prev.model, temperature: parseFloat(e.target.value) }
              } : null)}
            />
            
            <Typography variant="h6" sx={{ mt: 2 }}>Agent Configuration</Typography>
            <FormControl fullWidth>
              <InputLabel>Type</InputLabel>
              <Select
                value={editingProfile?.agent.type || 'conversation'}
                onChange={handleAgentTypeChange}
                label="Type"
              >
                <MenuItem value="conversation">Conversation</MenuItem>
                <MenuItem value="rag">RAG</MenuItem>
              </Select>
            </FormControl>
            <TextField
              label="Persona"
              multiline
              rows={4}
              value={editingProfile?.agent.persona || ''}
              onChange={(e) => setEditingProfile(prev => prev ? {
                ...prev,
                agent: { ...prev.agent, persona: e.target.value }
              } : null)}
            />

            {editingProfile?.agent.type === 'rag' && (
              <>
                <Typography variant="h6" sx={{ mt: 2 }}>Knowledge Sets</Typography>
                <FormControl fullWidth>
                  <InputLabel>Knowledge Sets</InputLabel>
                  <Select
                    multiple
                    value={editingProfile?.knowledge_sets || []}
                    onChange={handleKnowledgeSetsChange}
                    input={<OutlinedInput label="Knowledge Sets" />}
                    renderValue={(selected) => (
                      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                        {(selected as string[]).map((value) => (
                          <Chip key={value} label={value} />
                        ))}
                      </Box>
                    )}
                  >
                    {knowledgeSets.map((ks) => (
                      <MenuItem key={ks.name} value={ks.name}>
                        {ks.name}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </>
            )}
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowEditDialog(false)}>Cancel</Button>
          <Button onClick={handleSubmit} variant="contained" color="primary">
            Save
          </Button>
        </DialogActions>
      </Dialog>
    </Dialog>
  );
};

export default ProfileManager;