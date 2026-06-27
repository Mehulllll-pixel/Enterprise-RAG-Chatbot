// API communication layer with automatic token injection and auto-refresh interceptors.

export const API_BASE = import.meta.env.VITE_API_URL || '';

export interface FetchOptions extends RequestInit {
  skipToken?: boolean;
}

class ApiClient {
  private activeRefreshPromise: Promise<string | null> | null = null;

  private getAccessToken(): string | null {
    return localStorage.getItem('access_token');
  }

  private getRefreshToken(): string | null {
    return localStorage.getItem('refresh_token');
  }

  private saveTokens(access: string, refresh: string) {
    localStorage.setItem('access_token', access);
    localStorage.setItem('refresh_token', refresh);
  }

  public logout() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user_profile');
    // Force redirect to login page
    if (window.location.pathname !== '/login') {
      window.location.href = '/login';
    }
  }

  /**
   * Refreshes the active access token using the stored refresh token.
   * Leverages a single active promise for concurrent overlapping requests.
   */
  private async performTokenRefresh(): Promise<string | null> {
    if (this.activeRefreshPromise) {
      return this.activeRefreshPromise;
    }

    const refresh_token = this.getRefreshToken();
    if (!refresh_token) {
      this.logout();
      return null;
    }

    this.activeRefreshPromise = (async () => {
      try {
        const response = await fetch(`${API_BASE}/api/v1/auth/refresh`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ refresh_token })
        });

        if (!response.ok) {
          throw new Error('Refresh token invalid');
        }

        const data = await response.json();
        this.saveTokens(data.access_token, data.refresh_token);
        return data.access_token;
      } catch (err) {
        console.error('Auto-refresh failed:', err);
        this.logout();
        return null;
      } finally {
        this.activeRefreshPromise = null;
      }
    })();

    return this.activeRefreshPromise;
  }

  /**
   * Base request wrapper injecting token headers, managing HTTP statuses and retries.
   */
  public async request(url: string, options: FetchOptions = {}): Promise<any> {
    const headers = new Headers(options.headers || {});
    
    // 1. Inject Token
    if (!options.skipToken) {
      const token = this.getAccessToken();
      if (token) {
        headers.set('Authorization', `Bearer ${token}`);
      }
    }

    const fetchConfig: RequestInit = {
      ...options,
      headers
    };

    const fullUrl = url.startsWith('/') ? `${API_BASE}${url}` : url;

    // 2. Perform Fetch
    let response = await fetch(fullUrl, fetchConfig);

    // 3. Intercept 401 Unauthorized and try to refresh
    if (response.status === 401 && !options.skipToken) {
      console.warn(`Request to ${fullUrl} returned 401. Triggering token refresh...`);
      const newAccessToken = await this.performTokenRefresh();
      
      if (newAccessToken) {
        // Retry request with new token
        headers.set('Authorization', `Bearer ${newAccessToken}`);
        response = await fetch(fullUrl, fetchConfig);
      }
    }

    // 4. Handle non-2xx responses
    if (!response.ok) {
      let errorMessage = 'An unexpected API error occurred.';
      try {
        const errJson = await response.json();
        errorMessage = errJson.detail || errorMessage;
      } catch {
        // Ignore JSON decode error on raw responses
      }
      throw new Error(errorMessage);
    }

    // 5. Success
    if (response.status === 204) {
      return null;
    }
    
    return await response.json();
  }

  // HTTP wrappers
  public async get(url: string, options: FetchOptions = {}) {
    return this.request(url, { ...options, method: 'GET' });
  }

  public async post(url: string, body: any, options: FetchOptions = {}) {
    const headers = new Headers(options.headers || {});
    let finalBody = body;
    
    if (!(body instanceof FormData)) {
      headers.set('Content-Type', 'application/json');
      finalBody = JSON.stringify(body);
    }

    return this.request(url, {
      ...options,
      method: 'POST',
      headers,
      body: finalBody
    });
  }

  public async delete(url: string, options: FetchOptions = {}) {
    return this.request(url, { ...options, method: 'DELETE' });
  }
}

export const api = new ApiClient();
