import { request } from "./client";

export interface UserProfile {
  id: string;
  email: string;
  role_id: string;
  is_active: boolean;
  email_verified: boolean;
}

export function getUser(userId: string): Promise<UserProfile> {
  return request<UserProfile>(`/users/${userId}`);
}
