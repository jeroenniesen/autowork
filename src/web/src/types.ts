export interface Profile {
  name: string;
  description: string;
}

export interface Session {
  session_id: string;
  profile_name: string;
  created_at: string;
}

export interface ProfileConfig {
  name: string;
  description: string;
  model: {
    provider: string;
    name: string;
    temperature?: number;
    max_tokens?: number;
    top_p?: number;
  };
  agent: {
    persona: string;
    type?: string;
    tools?: string[];
    // Manager agent specific properties
    available_agents?: string[];
    delegation_strategy?: 'automatic' | 'specified';
    show_thinking?: boolean;
    fallback_agent?: string;
  };
  memory?: {
    type: string;
    max_token_limit: number;
  };
  knowledge_sets?: string[];
}

export interface ProfileCreateRequest {
  name: string;
  description: string;
  model: Record<string, any>;
  agent: Record<string, any>;
  memory?: Record<string, any>;
  knowledge_sets?: string[];
}

export interface KnowledgeSet {
  name: string;
  description: string;
  document_count: number;
  created_at: string;
  assigned_profiles: string[];
}