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
  };
  memory?: {
    type: string;
    max_token_limit: number;
  };
}

export interface ProfileCreateRequest {
  name: string;
  description: string;
  model: Record<string, any>;
  agent: Record<string, any>;
  memory?: Record<string, any>;
}