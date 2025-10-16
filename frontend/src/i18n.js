import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';

// Translation resources
const resources = {
  en: {
    translation: {
      // Navigation
      'nav.dashboard': 'Dashboard',
      'nav.recipes': 'Recipes',
      'nav.ingredients': 'Ingredients',
      'nav.inventory': 'Inventory',
      'nav.sales': 'Sales',
      'nav.wastage': 'Wastage',
      'nav.pl': 'P&L',
      'nav.settings': 'Settings',
      
      // Auth
      'auth.login': 'Login',
      'auth.register': 'Register',
      'auth.logout': 'Logout',
      'auth.email': 'Email',
      'auth.password': 'Password',
      'auth.displayName': 'Your Name',
      'auth.restaurantName': 'Restaurant Name',
      'auth.signIn': 'Sign In',
      'auth.signUp': 'Create Account',
      'auth.welcome': 'Welcome',
      'auth.welcomeBack': 'Welcome back!',
      'auth.forgotPassword': 'Forgot password?',
      
      // Dashboard
      'dashboard.title': 'Dashboard',
      'dashboard.subtitle': 'Overview of your restaurant performance',
      'dashboard.foodCost': 'Food Cost %',
      'dashboard.lowStock': 'Low Stock',
      'dashboard.expiringSoon': 'Expiring Soon',
      'dashboard.lastMonthGM': 'Last Month GM',
      'dashboard.totalRevenue': 'Total Revenue',
      'dashboard.totalCogs': 'Total COGS',
      
      // Common
      'common.save': 'Save',
      'common.cancel': 'Cancel',
      'common.delete': 'Delete',
      'common.edit': 'Edit',
      'common.add': 'Add',
      'common.create': 'Create',
      'common.update': 'Update',
      'common.search': 'Search',
      'common.filter': 'Filter',
      'common.loading': 'Loading...',
      'common.noData': 'No data available',
      
      // Settings
      'settings.title': 'Settings',
      'settings.general': 'General Settings',
      'settings.currency': 'Currency',
      'settings.locale': 'Language',
      'settings.restaurant': 'Restaurant',
      'settings.roles': 'Roles & Permissions',
      
      // Messages
      'msg.success': 'Success',
      'msg.error': 'Error',
      'msg.saved': 'Saved successfully',
      'msg.deleted': 'Deleted successfully',
      'msg.updated': 'Updated successfully'
    }
  },
  it: {
    translation: {
      // Navigation
      'nav.dashboard': 'Cruscotto',
      'nav.recipes': 'Ricette',
      'nav.ingredients': 'Ingredienti',
      'nav.inventory': 'Inventario',
      'nav.sales': 'Vendite',
      'nav.wastage': 'Scarti',
      'nav.pl': 'P&L',
      'nav.settings': 'Impostazioni',
      
      // Auth
      'auth.login': 'Accedi',
      'auth.register': 'Registrati',
      'auth.logout': 'Esci',
      'auth.email': 'Email',
      'auth.password': 'Password',
      'auth.displayName': 'Il tuo nome',
      'auth.restaurantName': 'Nome Ristorante',
      'auth.signIn': 'Accedi',
      'auth.signUp': 'Crea Account',
      'auth.welcome': 'Benvenuto',
      'auth.welcomeBack': 'Bentornato!',
      'auth.forgotPassword': 'Password dimenticata?',
      
      // Dashboard
      'dashboard.title': 'Cruscotto',
      'dashboard.subtitle': 'Panoramica delle prestazioni del ristorante',
      'dashboard.foodCost': 'Costo Cibo %',
      'dashboard.lowStock': 'Scorte Basse',
      'dashboard.expiringSoon': 'In Scadenza',
      'dashboard.lastMonthGM': 'Margine Mese Scorso',
      'dashboard.totalRevenue': 'Ricavi Totali',
      'dashboard.totalCogs': 'COGS Totali',
      
      // Common
      'common.save': 'Salva',
      'common.cancel': 'Annulla',
      'common.delete': 'Elimina',
      'common.edit': 'Modifica',
      'common.add': 'Aggiungi',
      'common.create': 'Crea',
      'common.update': 'Aggiorna',
      'common.search': 'Cerca',
      'common.filter': 'Filtra',
      'common.loading': 'Caricamento...',
      'common.noData': 'Nessun dato disponibile',
      
      // Settings
      'settings.title': 'Impostazioni',
      'settings.general': 'Impostazioni Generali',
      'settings.currency': 'Valuta',
      'settings.locale': 'Lingua',
      'settings.restaurant': 'Ristorante',
      'settings.roles': 'Ruoli e Permessi',
      
      // Messages
      'msg.success': 'Successo',
      'msg.error': 'Errore',
      'msg.saved': 'Salvato con successo',
      'msg.deleted': 'Eliminato con successo',
      'msg.updated': 'Aggiornato con successo'
    }
  }
};

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources,
    fallbackLng: 'en',
    supportedLngs: ['en', 'it'],
    detection: {
      order: ['localStorage', 'navigator'],
      caches: ['localStorage']
    },
    interpolation: {
      escapeValue: false
    }
  });

export default i18n;
