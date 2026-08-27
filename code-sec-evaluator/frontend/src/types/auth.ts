import type { UserRole } from './enums';

export interface User {
  id: number;
  username: string;
  role: UserRole;
}

export interface InitRequest {
  username: string;
  password: string;
}

export interface InitData {
  id: number;
  username: string;
  role: UserRole;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginData {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}
