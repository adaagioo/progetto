import React, { useContext } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { AuthContext } from '../App';
import { useTranslation } from 'react-i18next';
import { Button } from './ui/button';
import { ChefHat, LayoutDashboard, BookOpen, Package, ShoppingCart, AlertTriangle, TrendingUp, UtensilsCrossed, LogOut, Settings as SettingsIcon, Truck, PackageCheck, Utensils, ClipboardList, ListOrdered, FileText, MenuSquare } from 'lucide-react';

function Layout({ children }) {
  const { t } = useTranslation();
  const { user, logout } = useContext(AuthContext);
  const location = useLocation();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  // Feature flags
  const FEATURE_DOCUMENT_IMPORT = process.env.REACT_APP_FEATURE_DOCUMENT_IMPORT === 'true';

  const allNavItems = [
    { path: '/', label: t('nav.dashboard'), icon: LayoutDashboard },
    { path: '/ingredients', label: t('nav.ingredients'), icon: UtensilsCrossed },
    { path: '/recipes', label: t('nav.recipes'), icon: BookOpen },
    { path: '/preparations', label: t('nav.preparations'), icon: Utensils },
    { path: '/current-menu', label: t('nav.currentMenu'), icon: MenuSquare },
    { path: '/suppliers', label: t('nav.suppliers'), icon: Truck },
    { path: '/receiving', label: t('nav.receiving'), icon: PackageCheck },
    { path: '/document-import', label: t('nav.documentImport'), icon: FileText, featureFlag: 'DOCUMENT_IMPORT' },
    { path: '/inventory', label: t('nav.inventory'), icon: Package },
    { path: '/sales', label: t('nav.sales'), icon: ShoppingCart },
    { path: '/wastage', label: t('nav.wastage'), icon: AlertTriangle },
    { path: '/prep-list', label: t('nav.prepList'), icon: ClipboardList },
    { path: '/order-list', label: t('nav.orderList'), icon: ListOrdered },
    { path: '/profit-loss', label: t('nav.pl'), icon: TrendingUp },
    { path: '/settings', label: t('nav.settings'), icon: SettingsIcon }
  ];

  // Filter nav items based on feature flags
  const navItems = allNavItems.filter(item => {
    if (item.featureFlag === 'DOCUMENT_IMPORT') {
      return FEATURE_DOCUMENT_IMPORT;
    }
    return true;
  });

  return (
    <div className="min-h-screen bg-gradient-to-br from-emerald-50 via-teal-50 to-green-50">
      {/* Top Navigation */}
      <nav className="glass-morphism border-b sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <Link to="/" className="flex items-center gap-2" data-testid="logo-link">
              <div className="w-10 h-10 bg-gradient-to-br from-emerald-500 to-teal-600 rounded-xl flex items-center justify-center">
                <ChefHat className="w-6 h-6 text-white" />
              </div>
              <span className="text-xl font-bold gradient-text">RistoBrain</span>
            </Link>

            <div className="flex items-center gap-4">
              <div className="text-right hidden sm:block">
                <p className="text-sm font-medium text-gray-800" data-testid="user-name">{user?.displayName}</p>
                <p className="text-xs text-gray-500" data-testid="user-role">{user?.role}</p>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={handleLogout}
                className="text-red-600 hover:text-red-700 hover:bg-red-50"
                data-testid="logout-button"
              >
                <LogOut className="w-4 h-4" />
              </Button>
            </div>
          </div>
        </div>
      </nav>

      {/* Side Navigation & Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="flex flex-col lg:flex-row gap-6">
          {/* Sidebar */}
          <aside className="w-full lg:w-64 flex-shrink-0">
            <div className="glass-morphism rounded-2xl p-4 space-y-2">
              {navItems.map((item) => {
                const Icon = item.icon;
                const isActive = location.pathname === item.path;
                
                return (
                  <Link
                    key={item.path}
                    to={item.path}
                    data-testid={`nav-${item.label.toLowerCase()}`}
                    className={`flex items-center gap-3 px-4 py-3 rounded-xl transition-all ${
                      isActive
                        ? 'bg-gradient-to-r from-emerald-500 to-teal-600 text-white shadow-lg'
                        : 'text-gray-700 hover:bg-emerald-50'
                    }`}
                  >
                    <Icon className="w-5 h-5" />
                    <span className="font-medium">{item.label}</span>
                  </Link>
                );
              })}
            </div>
          </aside>

          {/* Main Content */}
          <main className="flex-1 min-w-0">
            {children}
          </main>
        </div>
        
        {/* Build Version Footer */}
        <footer className="text-center py-2 text-xs text-gray-400 border-t border-gray-200 mt-4">
          Build: {process.env.REACT_APP_BUILD_VERSION || 'v1.0.0-p3-inventory-fixes'} • {new Date().toISOString().split('T')[0]}
        </footer>
      </div>
    </div>
  );
}

export default Layout;