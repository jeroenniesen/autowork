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
  Alert,
  CircularProgress,
  Snackbar,
} from '@mui/material';
import { Delete as DeleteIcon, Edit as EditIcon, CloudUpload as CloudUploadIcon } from '@mui/icons-material';
import axios from 'axios';

// Change the API_URL to match what the nginx.conf is expecting
const API_URL = '/api';

interface KnowledgeSet {
  name: string;
  description: string;
  document_count: number;
  created_at: string;
  assigned_profiles: string[];
}

interface KnowledgeSetManagerProps {
  open: boolean;
  onClose: () => void;
  profiles: Array<{ name: string; description: string; }>;
}

interface KnowledgeSetDialogState {
  name: string;
  description: string;
}

const KnowledgeSetManager: React.FC<KnowledgeSetManagerProps> = ({
  open,
  onClose,
  profiles,
}) => {
  const [knowledgeSets, setKnowledgeSets] = useState<KnowledgeSet[]>([]);
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [editingKnowledgeSet, setEditingKnowledgeSet] = useState<KnowledgeSetDialogState | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [selectedKnowledgeSet, setSelectedKnowledgeSet] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [isUploadingDocument, setIsUploadingDocument] = useState(false);
  const [isLoadingKnowledgeSets, setIsLoadingKnowledgeSets] = useState(false);

  // Fetch knowledge sets when the component mounts or the dialog opens
  useEffect(() => {
    if (open) {
      fetchKnowledgeSets();
    }
  }, [open]);

  const fetchKnowledgeSets = async () => {
    setIsLoadingKnowledgeSets(true);
    try {
      console.log("Fetching knowledge sets...");
      const response = await axios.get(`${API_URL}/knowledge-sets`);
      console.log("Knowledge sets response:", response.data);
      
      // Check if knowledge_sets is undefined or null
      if (!response.data.knowledge_sets) {
        console.error("No knowledge_sets property in response:", response.data);
        setKnowledgeSets([]);
        setErrorMessage('Invalid response from server (missing knowledge_sets)');
        return;
      }
      
      setKnowledgeSets(response.data.knowledge_sets || []);
      
      // Reset selectedKnowledgeSet if it's no longer valid
      if (selectedKnowledgeSet && !response.data.knowledge_sets.some((ks: KnowledgeSet) => ks.name === selectedKnowledgeSet)) {
        setSelectedKnowledgeSet(null);
      }
      
      console.log(`Loaded ${response.data.knowledge_sets.length} knowledge sets`);
    } catch (error) {
      console.error('Error fetching knowledge sets:', error);
      setErrorMessage('Failed to load knowledge sets');
      setKnowledgeSets([]);
    } finally {
      setIsLoadingKnowledgeSets(false);
    }
  };

  const handleCreate = () => {
    setEditingKnowledgeSet({ name: '', description: '' });
    setShowCreateDialog(true);
  };

  const handleEdit = (knowledgeSet: KnowledgeSet) => {
    setEditingKnowledgeSet({
      name: knowledgeSet.name,
      description: knowledgeSet.description,
    });
    setShowCreateDialog(true);
  };

  const handleSubmit = async () => {
    if (!editingKnowledgeSet) return;
    if (!editingKnowledgeSet.name || !editingKnowledgeSet.description) {
      setErrorMessage('Please provide both name and description');
      return;
    }

    setIsSubmitting(true);
    setErrorMessage(null);

    try {
      const isEditing = knowledgeSets.some(ks => ks.name === editingKnowledgeSet.name);
      console.log("Is editing existing knowledge set:", isEditing);
      console.log("Knowledge set data:", editingKnowledgeSet);

      if (isEditing) {
        console.log(`Updating knowledge set: ${editingKnowledgeSet.name}`);
        const response = await axios.put(
          `${API_URL}/knowledge-sets/${editingKnowledgeSet.name}`, 
          editingKnowledgeSet
        );
        console.log("Update response:", response.data);
        setSuccessMessage(`Knowledge set "${editingKnowledgeSet.name}" updated successfully`);
      } else {
        console.log(`Creating new knowledge set: ${editingKnowledgeSet.name}`);
        const response = await axios.post(
          `${API_URL}/knowledge-sets`, 
          editingKnowledgeSet
        );
        console.log("Create response:", response.data);
        setSuccessMessage(`Knowledge set "${editingKnowledgeSet.name}" created successfully`);
      }
      
      setShowCreateDialog(false);
      setEditingKnowledgeSet(null);
      await fetchKnowledgeSets();
    } catch (error: any) {
      console.error('Error saving knowledge set:', error);
      if (error.response) {
        console.error('Response data:', error.response.data);
        console.error('Response status:', error.response.status);
        setErrorMessage(`Error: ${error.response.data.detail || 'Unknown error'}`);
      } else if (error.request) {
        console.error('Request error:', error.request);
        setErrorMessage('Network error. Please check your connection.');
      } else {
        setErrorMessage(`Error: ${error.message || 'Unknown error'}`);
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDelete = async (name: string) => {
    try {
      console.log(`Deleting knowledge set: ${name}`);
      const response = await axios.delete(`${API_URL}/knowledge-sets/${name}`);
      console.log("Delete response:", response.data);
      setSuccessMessage(`Knowledge set "${name}" deleted successfully`);
      fetchKnowledgeSets();
    } catch (error: any) {
      console.error('Error deleting knowledge set:', error);
      if (error.response?.status === 400) {
        alert('Cannot delete knowledge set as it is assigned to one or more profiles');
      } else {
        setErrorMessage(`Error deleting knowledge set: ${error.response?.data?.detail || 'Unknown error'}`);
      }
    }
  };

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files && event.target.files[0]) {
      setSelectedFile(event.target.files[0]);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile || !selectedKnowledgeSet) {
      setUploadError('Please select both a file and a knowledge set');
      return;
    }

    setIsUploadingDocument(true);
    setUploadError(null);
    
    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
      console.log(`Uploading file to knowledge set: ${selectedKnowledgeSet}`);
      const response = await axios.post(
        `${API_URL}/upload-document/${selectedKnowledgeSet}`, 
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        }
      );
      console.log("Upload response:", response.data);
      setSelectedFile(null);
      setUploadError(null);
      setSuccessMessage(`Document uploaded successfully to "${selectedKnowledgeSet}"`);
      fetchKnowledgeSets();
    } catch (error: any) {
      console.error('Error uploading document:', error);
      setUploadError(`Error uploading document: ${error.response?.data?.detail || 'Unknown error'}`);
    } finally {
      setIsUploadingDocument(false);
    }
  };

  const handleSnackbarClose = () => {
    setErrorMessage(null);
    setSuccessMessage(null);
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>Manage Knowledge Sets</DialogTitle>
      <DialogContent>
        <Box sx={{ mb: 2 }}>
          <Button variant="contained" color="primary" onClick={handleCreate}>
            Create New Knowledge Set
          </Button>
        </Box>

        {/* Upload Section */}
        <Box sx={{ mb: 3, p: 2, border: '1px solid', borderColor: 'divider', borderRadius: 1 }}>
          <Typography variant="h6" sx={{ mb: 2 }}>Upload Document</Typography>
          <FormControl fullWidth sx={{ mb: 2 }}>
            <InputLabel>Knowledge Set</InputLabel>
            <Select
              value={selectedKnowledgeSet || ''}
              onChange={(e) => setSelectedKnowledgeSet(e.target.value)}
              label="Knowledge Set"
              displayEmpty
              disabled={isUploadingDocument}
            >
              <MenuItem value="" disabled>
                <em>Select a knowledge set</em>
              </MenuItem>
              {knowledgeSets && knowledgeSets.length > 0 ? (
                knowledgeSets.map((ks) => (
                  <MenuItem key={ks.name} value={ks.name}>{ks.name}</MenuItem>
                ))
              ) : (
                <MenuItem value="" disabled>
                  <em>No knowledge sets available - create one first</em>
                </MenuItem>
              )}
            </Select>
          </FormControl>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Button
              variant="contained"
              component="label"
              startIcon={<CloudUploadIcon />}
              disabled={isUploadingDocument}
            >
              Select File
              <input
                type="file"
                hidden
                onChange={handleFileSelect}
                disabled={isUploadingDocument}
              />
            </Button>
            <Button
              variant="contained"
              color="primary"
              onClick={handleUpload}
              disabled={!selectedFile || !selectedKnowledgeSet || isUploadingDocument}
              startIcon={isUploadingDocument ? <CircularProgress size={20} color="inherit" /> : undefined}
            >
              {isUploadingDocument ? 'Uploading...' : 'Upload'}
            </Button>
          </Box>
          {selectedFile && (
            <Typography variant="body2" sx={{ mt: 1 }}>
              Selected file: {selectedFile.name}
            </Typography>
          )}
          {uploadError && (
            <Alert severity="error" sx={{ mt: 1 }}>
              {uploadError}
            </Alert>
          )}
          {knowledgeSets.length === 0 && (
            <Alert severity="info" sx={{ mt: 1 }}>
              Create a knowledge set first before uploading documents.
            </Alert>
          )}
        </Box>

        {isLoadingKnowledgeSets ? (
          <Box display="flex" justifyContent="center" p={3}>
            <CircularProgress />
          </Box>
        ) : (
          <List>
            {knowledgeSets.length > 0 ? (
              knowledgeSets.map((knowledgeSet) => (
                <ListItem key={knowledgeSet.name}>
                  <ListItemText
                    primary={knowledgeSet.name}
                    secondary={
                      <>
                        {knowledgeSet.description}
                        <br />
                        Documents: {knowledgeSet.document_count}
                        <br />
                        Used by profiles: {knowledgeSet.assigned_profiles.join(', ') || 'None'}
                      </>
                    }
                  />
                  <ListItemSecondaryAction>
                    <IconButton edge="end" onClick={() => handleEdit(knowledgeSet)}>
                      <EditIcon />
                    </IconButton>
                    <IconButton
                      edge="end"
                      onClick={() => handleDelete(knowledgeSet.name)}
                    >
                      <DeleteIcon />
                    </IconButton>
                  </ListItemSecondaryAction>
                </ListItem>
              ))
            ) : (
              <ListItem>
                <ListItemText primary="No knowledge sets found. Create one to get started." />
              </ListItem>
            )}
          </List>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Close</Button>
      </DialogActions>

      {/* Create/Edit Dialog */}
      <Dialog open={showCreateDialog} onClose={() => setShowCreateDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>
          {editingKnowledgeSet?.name && knowledgeSets.some(ks => ks.name === editingKnowledgeSet.name) 
            ? `Edit Knowledge Set: ${editingKnowledgeSet.name}` 
            : 'Create New Knowledge Set'}
        </DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 2 }}>
            <TextField
              label="Name"
              value={editingKnowledgeSet?.name || ''}
              onChange={(e) => setEditingKnowledgeSet(prev => prev ? { ...prev, name: e.target.value } : null)}
              disabled={!!knowledgeSets.find(ks => ks.name === editingKnowledgeSet?.name)}
              required
            />
            <TextField
              label="Description"
              value={editingKnowledgeSet?.description || ''}
              onChange={(e) => setEditingKnowledgeSet(prev => prev ? { ...prev, description: e.target.value } : null)}
              multiline
              rows={4}
              required
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowCreateDialog(false)}>Cancel</Button>
          <Button 
            onClick={handleSubmit} 
            variant="contained" 
            color="primary"
            disabled={isSubmitting}
          >
            {isSubmitting ? <CircularProgress size={24} /> : 'Save'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Snackbar for messages */}
      <Snackbar
        open={!!errorMessage}
        autoHideDuration={6000}
        onClose={handleSnackbarClose}
        message={errorMessage}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert onClose={handleSnackbarClose} severity="error" sx={{ width: '100%' }}>
          {errorMessage}
        </Alert>
      </Snackbar>

      <Snackbar
        open={!!successMessage}
        autoHideDuration={6000}
        onClose={handleSnackbarClose}
        message={successMessage}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert onClose={handleSnackbarClose} severity="success" sx={{ width: '100%' }}>
          {successMessage}
        </Alert>
      </Snackbar>
    </Dialog>
  );
};

export default KnowledgeSetManager;