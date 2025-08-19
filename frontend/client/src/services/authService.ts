import { apiPost, apiGet } from "./api";
import { LoginCredentials, RegisterData, AuthResponse, User } from "@/types";

export const authService = {
  async login(credentials: LoginCredentials): Promise<AuthResponse> {
    const response = await apiPost<AuthResponse>("/auth/login/", credentials);
    
    // Store token and user in localStorage
    localStorage.setItem("auth_token", response.token);
    localStorage.setItem("user", JSON.stringify(response.user));
    
    return response;
  },

  async register(data: RegisterData): Promise<AuthResponse> {
    const response = await apiPost<AuthResponse>("/auth/register/", data);
    
    // Store token and user in localStorage
    localStorage.setItem("auth_token", response.token);
    localStorage.setItem("user", JSON.stringify(response.user));
    
    return response;
  },

  async getCurrentUser(): Promise<User> {
    return apiGet<User>("/users/me/");
  },

  logout(): void {
    localStorage.removeItem("auth_token");
    localStorage.removeItem("user");
  },

  getStoredUser(): User | null {
    const user = localStorage.getItem("user");
    return user ? JSON.parse(user) : null;
  },

  getStoredToken(): string | null {
    return localStorage.getItem("auth_token");
  },

  isAuthenticated(): boolean {
    return !!this.getStoredToken();
  }
};
