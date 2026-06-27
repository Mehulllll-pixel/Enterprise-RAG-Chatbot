import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { Users, Shield, Building, Loader2, AlertCircle, CheckCircle, RefreshCw, Search, ChevronLeft, ChevronRight, Filter } from 'lucide-react';

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

  // Search & Filter state
  const [searchQuery, setSearchQuery] = useState('');
  const [roleFilter, setRoleFilter] = useState('');
  const [deptFilter, setDeptFilter] = useState('');

  // Pagination state
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 8;

  const fetchUsersAndDepts = async () => {
    setIsLoading(true);
    setError(null);
    try {
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

  // Helper mapping role badges
  const renderRoleBadge = (roleId: string) => {
    switch (roleId) {
      case 'ADMIN':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-red-500/10 border border-red-500/20 text-red-400 text-[10px] font-bold uppercase tracking-wider">
            Admin
          </span>
        );
      case 'MANAGER':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-orange-500/10 border border-orange-500/20 text-orange-400 text-[10px] font-bold uppercase tracking-wider">
            Manager
          </span>
        );
      case 'ENGINEER':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-blue-500/10 border border-blue-500/20 text-blue-400 text-[10px] font-bold uppercase tracking-wider">
            Developer
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-[10px] font-bold uppercase tracking-wider">
            Viewer
          </span>
        );
    }
  };

  const userItems = Array.isArray(users) ? users : [];
  const deptItems = Array.isArray(departments) ? departments : [];

  // Filter and search computation
  const filteredUsers = userItems.filter((user) => {
    const matchesSearch = 
      (user.full_name || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
      user.email.toLowerCase().includes(searchQuery.toLowerCase());
    
    const matchesRole = roleFilter === '' || user.role_id === roleFilter;
    const matchesDept = deptFilter === '' || user.department_id === deptFilter;

    return matchesSearch && matchesRole && matchesDept;
  });

  // Pagination calculation
  const totalPages = Math.ceil(filteredUsers.length / itemsPerPage);
  const paginatedUsers = filteredUsers.slice(
    (currentPage - 1) * itemsPerPage,
    currentPage * itemsPerPage
  );

  return (
    <div className="container mx-auto px-4 py-8 max-w-7xl font-sans text-white">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
        <div className="flex items-center gap-3.5">
          <div className="p-3 bg-brand-500/10 border border-brand-500/20 rounded-2xl text-brand-400 shadow-inner">
            <Users className="h-6 w-6" />
          </div>
          <div>
            <h1 className="text-2xl font-extrabold text-white tracking-tight">Admin Directory Console</h1>
            <p className="text-gray-400 text-xs mt-0.5">Manage user workspace access roles and departmental index boundaries</p>
          </div>
        </div>
        <button
          onClick={fetchUsersAndDepts}
          disabled={isLoading}
          className="flex items-center justify-center gap-2 px-4 py-2.5 bg-gray-900 border border-gray-800 rounded-xl hover:bg-gray-850 hover:border-gray-700 text-gray-300 transition-all text-xs disabled:opacity-50 cursor-pointer font-semibold"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${isLoading ? 'animate-spin' : ''}`} />
          <span>Reload List</span>
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
        <div className="mb-6 flex items-start gap-3 rounded-xl bg-red-500/10 border border-red-500/20 p-4 text-red-400 text-sm animate-pulse">
          <AlertCircle className="h-5 w-5 shrink-0 mt-0.5" />
          <span>{error}</span>
        </div>
      )}

      {/* Filters and Search panel */}
      <div className="glass-panel rounded-2xl p-4 border border-gray-900/60 flex flex-col md:flex-row gap-4 items-center justify-between text-xs mb-6">
        
        {/* Search */}
        <div className="w-full md:w-72 relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-gray-650" />
          <input
            type="text"
            className="w-full bg-darkSurface border border-gray-800 text-white rounded-xl py-2 pl-9 pr-4 focus:outline-none focus:border-brand-500 text-xs"
            placeholder="Search employees by name/email..."
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value);
              setCurrentPage(1);
            }}
          />
        </div>

        {/* Filters */}
        <div className="flex items-center gap-3 w-full md:w-auto justify-end">
          <span className="text-gray-500 font-bold uppercase tracking-wider text-[10px] flex items-center gap-1.5">
            <Filter className="h-3.5 w-3.5" />
            <span>Filter List:</span>
          </span>

          {/* Role Filter */}
          <select
            className="bg-darkSurface border border-gray-800 text-gray-300 rounded-lg py-1.5 px-3 focus:outline-none focus:border-brand-500 text-[11px]"
            value={roleFilter}
            onChange={(e) => {
              setRoleFilter(e.target.value);
              setCurrentPage(1);
            }}
          >
            <option value="">All Roles</option>
            <option value="ADMIN">ADMIN</option>
            <option value="MANAGER">MANAGER</option>
            <option value="ENGINEER">ENGINEER</option>
            <option value="VIEWER">VIEWER</option>
          </select>

          {/* Department Filter */}
          <select
            className="bg-darkSurface border border-gray-800 text-gray-300 rounded-lg py-1.5 px-3 focus:outline-none focus:border-brand-500 text-[11px]"
            value={deptFilter}
            onChange={(e) => {
              setDeptFilter(e.target.value);
              setCurrentPage(1);
            }}
          >
            <option value="">All Departments</option>
            {deptItems.map(dept => (
              <option key={dept.id} value={dept.id}>{dept.name}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Directory Table Area */}
      {isLoading ? (
        <div className="flex items-center justify-center py-20">
          <div className="flex flex-col items-center gap-3">
            <Loader2 className="h-10 w-10 animate-spin text-brand-500" />
            <span className="text-gray-400 text-sm font-semibold">Loading corporate directory...</span>
          </div>
        </div>
      ) : error && userItems.length === 0 ? (
        <div className="glass-panel rounded-2xl p-12 text-center text-gray-500 border border-gray-900/60">
          <AlertCircle className="h-12 w-12 mx-auto text-red-500/50 mb-3 animate-pulse" />
          <p className="font-semibold text-gray-300 text-base">Failed to Load User Directory</p>
          <p className="text-xs text-gray-550 mt-1 max-w-sm mx-auto">{error}</p>
          <button
            onClick={fetchUsersAndDepts}
            className="mt-6 px-4 py-2 bg-gray-900 border border-gray-800 rounded-xl hover:bg-gray-850 text-gray-305 transition-colors text-xs cursor-pointer inline-flex items-center gap-1.5 font-semibold"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            <span>Try Again</span>
          </button>
        </div>
      ) : filteredUsers.length === 0 ? (
        <div className="glass-panel rounded-2xl p-12 text-center text-gray-550 border border-gray-900/60">
          <Users className="h-12 w-12 mx-auto text-gray-800 mb-3" />
          <p className="font-semibold text-gray-300 text-base">No Matching Employees</p>
          <p className="text-xs text-gray-500 mt-1">Try adjusting search or filter criteria.</p>
        </div>
      ) : (
        <div className="glass-panel rounded-2xl overflow-hidden shadow-xl border border-gray-900/60 flex flex-col">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-gray-900/60 bg-darkSurface/50 text-gray-500 text-[10px] font-bold uppercase tracking-wider">
                  <th className="py-4 px-6">User Details</th>
                  <th className="py-4 px-6">Security Badge</th>
                  <th className="py-4 px-6">Modify Role Permissions</th>
                  <th className="py-4 px-6">Department Scope boundaries</th>
                  <th className="py-4 px-6">Registered Date</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-900/40 text-sm">
                {paginatedUsers.map((item) => (
                  <tr key={item.id} className="hover:bg-darkSurface/15 transition-colors">
                    {/* User Profile Info */}
                    <td className="py-4 px-6">
                      <div className="flex flex-col">
                        <span className="text-white font-semibold text-sm">{item.full_name || 'Unnamed Employee'}</span>
                        <span className="text-gray-500 text-xs mt-0.5">{item.email}</span>
                      </div>
                    </td>

                    {/* Badge */}
                    <td className="py-4 px-6">
                      {renderRoleBadge(item.role_id)}
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
                    <td className="py-4 px-6 text-gray-500 text-xs font-medium">
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

          {/* Pagination Footer */}
          {totalPages > 1 && (
            <div className="p-4 border-t border-gray-900/60 bg-darkSurface/30 flex items-center justify-between text-xs text-gray-500">
              <span>
                Showing page <strong className="text-white">{currentPage}</strong> of <strong className="text-white">{totalPages}</strong> (Filtered: {filteredUsers.length} total)
              </span>
              
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                  disabled={currentPage === 1}
                  className="p-1.5 bg-gray-900 border border-gray-800 rounded-lg text-gray-400 hover:text-white disabled:opacity-30 cursor-pointer"
                >
                  <ChevronLeft className="h-4 w-4" />
                </button>
                <button
                  onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
                  disabled={currentPage === totalPages}
                  className="p-1.5 bg-gray-900 border border-gray-800 rounded-lg text-gray-400 hover:text-white disabled:opacity-30 cursor-pointer"
                >
                  <ChevronRight className="h-4 w-4" />
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
