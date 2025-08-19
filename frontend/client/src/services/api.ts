import { queryClient } from "@/lib/queryClient";

// For development: point to local Django server
const API_BASE_URL = "http://localhost:8000/api";

// Current: using built-in Express API for MVP
// const API_BASE_URL = "/api";

interface ApiRequestOptions {
  method?: string;
  data?: any;
  headers?: Record<string, string>;
}

export async function apiRequest(
  endpoint: string,
  options: ApiRequestOptions = {}
): Promise<Response> {
  const { method = "GET", data, headers = {} } = options;
  
  const token = localStorage.getItem("auth_token");
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  if (data) {
    headers["Content-Type"] = "application/json";
  }

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    method,
    headers,
    body: data ? JSON.stringify(data) : undefined,
    credentials: "include",
  });

  if (!response.ok) {
    if (response.status === 401) {
      localStorage.removeItem("auth_token");
      localStorage.removeItem("user");
      queryClient.clear();
      window.location.href = "/login";
    }
    
    const errorText = await response.text();
    throw new Error(`${response.status}: ${errorText}`);
  }

  return response;
}

export async function apiGet<T>(endpoint: string): Promise<T> {
  const response = await apiRequest(endpoint);
  return response.json();
}

export async function apiPost<T>(endpoint: string, data: any): Promise<T> {
  const response = await apiRequest(endpoint, {
    method: "POST",
    data,
  });
  return response.json();
}

export async function apiPut<T>(endpoint: string, data: any): Promise<T> {
  const response = await apiRequest(endpoint, {
    method: "PUT",
    data,
  });
  return response.json();
}

export async function apiPatch<T>(endpoint: string, data: any): Promise<T> {
  const response = await apiRequest(endpoint, {
    method: "PATCH",
    data,
  });
  return response.json();
}

export async function apiDelete(endpoint: string): Promise<void> {
  await apiRequest(endpoint, {
    method: "DELETE",
  });
}
