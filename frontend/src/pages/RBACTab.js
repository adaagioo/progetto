import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import axios from 'axios';
import { API } from '../App';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Checkbox } from '../components/ui/checkbox';
import { toast } from 'sonner';
import { Shield, RotateCcw, Save, AlertCircle } from 'lucide-react';
import { getErrorMessage } from '../utils/errorHandler';

function RBACTab() {
  const { t } = useTranslation();
  const [roles, setRoles] = useState([]);
  const [resources, setResources] = useState([]);
  const [loading, setLoading] = useState(true);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    fetchRBACData();
  }, []);

  const fetchRBACData = async () => {
    try {
      setLoading(true);
      const [rolesRes, resourcesRes] = await Promise.all([
        axios.get(`${API}/rbac/roles`),
        axios.get(`${API}/rbac/resources`)
      ]);
      
      setRoles(rolesRes.data);
      setResources(resourcesRes.data);
    } catch (error) {
      toast.error(getErrorMessage(error, t('rbac.error.load') || 'Failed to load RBAC data'));
    } finally {
      setLoading(false);
    }
  };

  const togglePermission = (roleKey, resourceKey, action) => {
    setRoles(prevRoles => 
      prevRoles.map(role => {
        if (role.roleKey !== roleKey) return role;
        
        const currentActions = role.permissions[resourceKey] || [];
        const newActions = currentActions.includes(action)
          ? currentActions.filter(a => a !== action)
          : [...currentActions, action];
        
        return {
          ...role,
          permissions: {
            ...role.permissions,
            [resourceKey]: newActions
          }
        };
      })
    );
    
    setHasUnsavedChanges(true);
  };

  const saveRole = async (role) => {
    try {
      setSaving(true);
      await axios.put(`${API}/rbac/roles/${role.roleKey}/permissions`, role.permissions);
      toast.success(t('rbac.success.saved', { role: role.roleName }) || `${role.roleName} permissions saved`);
      setHasUnsavedChanges(false);
      await fetchRBACData(); // Refresh to show isCustomized status
    } catch (error) {
      toast.error(getErrorMessage(error, t('rbac.error.save') || 'Failed to save permissions'));
    } finally {
      setSaving(false);
    }
  };

  const resetRole = async (role) => {
    if (!window.confirm(t('rbac.confirm.reset', { role: role.roleName }) || `Reset ${role.roleName} permissions to defaults?`)) {
      return;
    }
    
    try {
      await axios.post(`${API}/rbac/roles/${role.roleKey}/reset`);
      toast.success(t('rbac.success.reset', { role: role.roleName }) || `${role.roleName} permissions reset`);
      setHasUnsavedChanges(false);
      await fetchRBACData();
    } catch (error) {
      toast.error(getErrorMessage(error, t('rbac.error.reset') || 'Failed to reset permissions'));
    }
  };

  const hasPermission = (role, resourceKey, action) => {
    const resourceActions = role.permissions[resourceKey] || [];
    return resourceActions.includes(action);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-center">
          <Shield className="mx-auto h-12 w-12 text-gray-400 animate-pulse" />
          <p className="mt-2 text-sm text-gray-600">{t('rbac.loading') || 'Loading RBAC settings...'}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">{t('rbac.title') || 'Role-Based Access Control'}</h2>
          <p className="text-sm text-muted-foreground mt-1">
            {t('rbac.description') || 'Manage permissions for each role in your organization'}
          </p>
        </div>
        {hasUnsavedChanges && (
          <div className="flex items-center gap-2 text-amber-600">
            <AlertCircle className="h-5 w-5" />
            <span className="text-sm font-medium">{t('rbac.unsavedChanges') || 'Unsaved changes'}</span>
          </div>
        )}
      </div>

      {/* Permission Matrix for each role */}
      {roles.map(role => (
        <Card key={role.roleKey}>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <Shield className="h-5 w-5" />
                  {t(`rbac.roles.${role.roleKey}`) || role.roleName}
                  {role.isCustomized && (
                    <span className="ml-2 px-2 py-0.5 text-xs bg-blue-100 text-blue-800 rounded">
                      {t('rbac.customized') || 'Customized'}
                    </span>
                  )}
                </CardTitle>
                <CardDescription>
                  {t(`rbac.roleDescription.${role.roleKey}`) || `Permissions for ${role.roleName} role`}
                </CardDescription>
              </div>
              <div className="flex gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => resetRole(role)}
                  disabled={!role.isCustomized}
                >
                  <RotateCcw className="h-4 w-4 mr-2" />
                  {t('rbac.reset') || 'Reset'}
                </Button>
                <Button
                  size="sm"
                  onClick={() => saveRole(role)}
                  disabled={saving}
                >
                  <Save className="h-4 w-4 mr-2" />
                  {t('rbac.save') || 'Save'}
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b">
                    <th className="text-left py-2 px-4 font-medium text-sm text-muted-foreground">
                      {t('rbac.resource') || 'Resource'}
                    </th>
                    <th className="text-center py-2 px-4 font-medium text-sm text-muted-foreground">
                      {t('rbac.actions.view') || 'View'}
                    </th>
                    <th className="text-center py-2 px-4 font-medium text-sm text-muted-foreground">
                      {t('rbac.actions.create') || 'Create'}
                    </th>
                    <th className="text-center py-2 px-4 font-medium text-sm text-muted-foreground">
                      {t('rbac.actions.update') || 'Update'}
                    </th>
                    <th className="text-center py-2 px-4 font-medium text-sm text-muted-foreground">
                      {t('rbac.actions.delete') || 'Delete'}
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {resources.map(resource => (
                    <tr key={resource.key} className="border-b hover:bg-muted/50">
                      <td className="py-3 px-4 font-medium">
                        {t(`rbac.resources.${resource.key}`) || resource.name}
                      </td>
                      {resource.actions.map(action => (
                        <td key={action} className="text-center py-3 px-4">
                          <Checkbox
                            checked={hasPermission(role, resource.key, action)}
                            onCheckedChange={() => togglePermission(role.roleKey, resource.key, action)}
                          />
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

export default RBACTab;
