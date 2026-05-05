export interface User {
  id: number;
  username: string;
  email: string;
  phone: string;
  avatar: string;
  created_at: string;
}

export interface Favorite {
  id: number;
  listing_id: number;
  created_at: string;
}

export interface SavedSearch {
  id: number;
  name: string;
  filters: Record<string, any>;
  alert_on: boolean;
  created_at: string;
}

export interface AuthTokens {
  access: string;
  refresh: string;
}

export interface LoginResponse {
  access: string;
  refresh: string;
  user: User;
}
