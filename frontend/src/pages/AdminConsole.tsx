import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { Users, Shield, Building, Loader2, AlertCircle, CheckCircle, RefreshCw } from 'lucide-react';

interface UserDirectoryItem {
  id: string;
  email: string;
  full_name: string;
  role_id: string;
  department_id: string | null;
  created_at: string;
}

interface DepartmentItem {
  id: string;
  name: string;
  code: string;
}

export const AdminConsole: React.FC = () => {
  const [users, setUsers] = useState<UserDirectoryItem[]>([]);
  const [departments, setDepartments] = useState<DepartmentItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [updatingUserId, setUpdatingUserId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const fetchUsersAndDepts = async () => {
    setIsLoading(true);
    setError(null);
    try {
      // Fetch both concurrently to speed up loaders
      const [usersList, deptsList] = await Promise.all([
        api.get('/api/v1/users'),
        api.get('/api/v1/users/departments')
      ]);
      
      setUsers(Array.isArray(usersList) ? usersList : []);
      setDepartments(Array.isArray(deptsList) ? deptsList : []);
    } catch (err: any) {
      console.error(err);
      setError(err.message || 'Failed to load corporate user directory or departments list.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchUsersAndDepts();
  }, []);

  const handleRoleChange = async (userId: string, newRoleId: string) => {
    setUpdatingUserId(userId);
    setError(null);
    setSuccess(null);
    try {
      // Call standard PUT endpoint to update user roles
      await api.post(`/api/v1/users/${userId}`, { role_id: newRoleId }, {
        headers: { 'Content-Type': 'application/json' }
      });
      // FastAPI router might require PUT method for updating, let's verify:
      // Our backend uses router.put("/{id}") for update_user_profile, but wait:
      // In FastAPI, does api.post work for PUT? No, we should use PUT method!
      // In api.ts:
      // public async request(url: string, options: FetchOptions = {}) { ... }
      // So let's construct a standard fetch PUT request using our api client request wrapper:
      await api.request(`/api/v1/users/${userId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ role_id: newRoleId })
      });
      
      setSuccess('User role updated successfully.');
      
      // Refresh local directory list
      const usersList = await api.get('/api/v1/users');
      setUsers(Array.isArray(usersList) ? usersList : []);
    } catch (err: any) {
      setError(err.message || 'Failed to update user role.');
    } finally {
      setUpdatingUserId(null);
    }
  };

  const handleDepartmentChange = async (userId: string, newDeptId: string | null) => {
    setUpdatingUserId(userId);
    setError(null);
    setSuccess(null);
    try {
      // Call standard PUT endpoint to update user departments
      await api.request(`/api/v1/users/${userId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ department_id: newDeptId || null })
      });
      
      setSuccess('User department updated successfully.');
      
      // Refresh local directory list
      const usersList = await api.get('/api/v1/users');
      setUsers(Array.isArray(usersList) ? usersList : []);
    } catch (err: any) {
      setError(err.message || 'Failed to update user department.');
    } finally {
      setUpdatingUserId(null);
    }
  };

  const userItems = Array.isArray(users) ? users : [];
  const deptItems = Array.isArray(departments) ? departments : [];

  return (
    <div className="container mx-auto px-4 py-8">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
        <div className="flex items-center gap-3">
          <div className="p-2.5 bg-brand-500/10 border border-brand-500/20 rounded-xl text-brand-400">
            <Users className="h-6 w-6" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-white">Admin Directory Console</h1>
            <p className="text-gray-400 text-sm">Manage user workspace roles and department scopes</p>
          </div>
        </div>
        <button
          onClick={fetchUsersAndDepts}
          disabled={isLoading}
          className="flex items-center justify-center gap-2 px-4 py-2.5 bg-gray-900 border border-gray-800 rounded-xl hover:bg-gray-800 text-gray-300 transition-colors text-sm disabled:opacity-50 cursor-pointer"
        >
          <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
          <span>Reload</span>
        </button>
      </div>

      {/* Success Alert */}
      {success && (
        <div className="mb-6 flex items-start gap-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20 p-4 text-emerald-400 text-sm">
          <CheckCircle className="h-5 w-5 shrink-0 mt-0.5" />
          <span>{success}</span>
        </div>
      )}

      {/* Error Alert */}
      {error && (
        <div className="mb-6 flex items-start gap-3 rounded-xl bg-red-500/10 border border-red-500/20 p-4 text-red-400 text-sm">
          <AlertCircle className="h-5 w-5 shrink-0 mt-0.5" />
          <span>{error}</span>
        </div>
      )}

      {/* Directory Table Area */}
      {isLoading ? (
        <div className="flex items-center justify-center py-20">
          <div className="flex flex-col items-center gap-3">
            <Loader2 className="h-10 w-10 animate-spin text-brand-500" />
            <span className="text-gray-400 text-sm">Loading corporate directory...</span>
          </div>
        </div>
      ) : error && userItems.length === 0 ? (
        <div className="glass-panel rounded-2xl p-12 text-center text-gray-500">
          <AlertCircle className="h-12 w-12 mx-auto text-red-500/50 mb-3 animate-pulse" />
          <p className="font-semibold text-gray-300 text-base">Failed to Load User Directory</p>
          <p className="text-sm text-gray-500 mt-1 max-w-sm mx-auto">{error}</p>
          <button
            onClick={fetchUsersAndDepts}
            className="mt-6 px-4 py-2 bg-gray-900 border border-gray-800 rounded-xl hover:bg-gray-800 text-gray-300 transition-colors text-sm cursor-pointer inline-flex items-center gap-1.5"
          >
            <RefreshCw className="h-4 w-4" />
            <span>Try Again</span>
          </button>
        </div>
      ) : userItems.length === 0 ? (
        <div className="glass-panel rounded-2xl p-12 text-center text-gray-500">
          <Users className="h-12 w-12 mx-auto text-gray-700 mb-3" />
          <p className="font-medium text-gray-300 text-base">No Users Found</p>
          <p className="text-sm text-gray-500 mt-1">There are no registered users in this environment database.</p>
        </div>
      ) : (
        <div className="glass-panel rounded-2xl overflow-hidden shadow-xl border border-gray-800/40">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-gray-800 bg-darkSurface/50 text-gray-400 text-xs font-semibold uppercase tracking-wider">
                  <th className="py-4 px-6">User Details</th>
                  <th className="py-4 px-6">Current Role</th>
                  <th className="py-4 px-6">Department Scope</th>
                  <th className="py-4 px-6">Registered At</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800/50 text-sm">
                {userItems.map((item) => (
                  <tr key={item.id} className="hover:bg-darkSurface/30 transition-colors">
                    {/* User Profile Info */}
                    <td className="py-4 px-6">
                      <div className="flex flex-col">
                        <span className="text-white font-medium">{item.full_name || 'Unnamed User'}</span>
                        <span className="text-gray-500 text-xs mt-0.5">{item.email}</span>
                      </div>
                    </td>

                    {/* Role Dropdown */}
                    <td className="py-4 px-6">
                      <div className="flex items-center gap-2">
                        <Shield className="h-4 w-4 text-brand-400 shrink-0" />
                        <select
                          disabled={updatingUserId === item.id}
                          className="bg-darkSurface border border-gray-800 text-gray-200 rounded-lg py-1.5 px-3 focus:outline-none focus:border-brand-500 text-xs focus:ring-1 focus:ring-brand-500 disabled:opacity-50 cursor-pointer"
                          value={item.role_id}
                          onChange={(e) => handleRoleChange(item.id, e.target.value)}
                        >
                          <option value="ADMIN">ADMIN</option>
                          <option value="MANAGER">MANAGER</option>
                          <option value="ENGINEER">ENGINEER</option>
                          <option value="VIEWER">VIEWER</option>
                        </select>
                      </div>
                    </td>

                    {/* Department Dropdown */}
                    <td className="py-4 px-6">
                      <div className="flex items-center gap-2">
                        <Building className="h-4 w-4 text-accent-teal shrink-0" />
                        <select
                          disabled={updatingUserId === item.id}
                          className="bg-darkSurface border border-gray-800 text-gray-200 rounded-lg py-1.5 px-3 focus:outline-none focus:border-brand-500 text-xs focus:ring-1 focus:ring-brand-500 disabled:opacity-50 cursor-pointer"
                          value={item.department_id || ''}
                          onChange={(e) => handleDepartmentChange(item.id, e.target.value || null)}
                        >
                          <option value="">No Department Scoping</option>
                          {deptItems.map((dept) => (
                            <option key={dept.id} value={dept.id}>
                              {dept.name} ({dept.code})
                            </option>
                          ))}
                        </select>
                      </div>
                    </td>

                    {/* Registration Date */}
                    <td className="py-4 px-6 text-gray-500 text-xs">
                      {item.created_at ? (
                        new Date(item.created_at).toLocaleDateString(undefined, {
                          year: 'numeric',
                          month: 'short',
                          day: 'numeric'
                        })
                      ) : (
                        'N/A'
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
