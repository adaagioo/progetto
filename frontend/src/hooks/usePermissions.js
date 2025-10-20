import { useState, useEffect } from 'react';
import axios from 'axios';
import { API } from '../App';

/**
 * Hook to get user's capabilities for a specific resource
 * Returns: { canView, canCreate, canUpdate, canDelete, loading }
 */
export function useResourceCapabilities(resource) {
  const [capabilities, setCapabilities] = useState({
    canView: false,
    canCreate: false,
    canUpdate: false,
    canDelete: false
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!resource) {
      setLoading(false);
      return;
    }

    const fetchCapabilities = async () => {
      try {
        setLoading(true);
        const response = await axios.get(`${API}/rbac/capabilities/${resource}`);
        setCapabilities(response.data);
      } catch (error) {
        console.error(`Failed to fetch capabilities for ${resource}:`, error);
        // Default to no permissions on error
        setCapabilities({
          canView: false,
          canCreate: false,
          canUpdate: false,
          canDelete: false
        });
      } finally {
        setLoading(false);
      }
    };

    fetchCapabilities();
  }, [resource]);

  return { ...capabilities, loading };
}

/**
 * Hook for simple permission check
 * Returns: boolean indicating if user has permission
 */
export function useHasPermission(resource, action) {
  const { canView, canCreate, canUpdate, canDelete, loading } = useResourceCapabilities(resource);
  
  if (loading) return false;
  
  switch (action) {
    case 'view':
      return canView;
    case 'create':
      return canCreate;
    case 'update':
      return canUpdate;
    case 'delete':
      return canDelete;
    default:
      return false;
  }
}
