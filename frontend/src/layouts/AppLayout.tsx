import React from "react";
import { Link, Outlet, useNavigate } from "react-router";
import { useAuthStore } from "@/stores/authStore";
import { useUIStore } from "@/stores/uiStore";
import { useThemeStore } from "@/stores/themeStore";
import { useNotificationStore } from "@/stores/notificationStore";
import { CommandPalette } from "@/components/CommandPalette";
import { useKeyboardShortcuts } from "@/hooks/useKeyboardShortcuts";
import {
  Menu,
  X,
  LogOut,
  Sun,
  Moon,
  Search,
  Bell,
  ShoppingBag,
  List,
  Layers,
  Settings,
  LayoutDashboard,
  ShoppingCart,
  Warehouse,
  Users as UsersIcon,
  BarChart3,
} from "lucide-react";

export const AppLayout: React.FC = () => {
  const navigate = useNavigate();
  const { user, logout } = useAuthStore();
  const { sidebarOpen, toggleSidebar } = useUIStore();
  const { theme, setTheme } = useThemeStore();
  const unreadCount = useNotificationStore((s) => s.notifications.filter((n) => !n.read).length);

  // Register global keyboard shortcuts
  useKeyboardShortcuts();

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  const toggleTheme = () => {
    setTheme(theme === "dark" ? "light" : "dark");
  };

  return (
    <div className="min-h-screen flex bg-gray-50 dark:bg-gray-900 transition-colors duration-200" role="application">
      <CommandPalette />
      {/* ── Sidebar ───────────────────────────────────────────────────────────── */}
      <aside
        role="navigation"
        aria-label="Main navigation"
        className={`fixed inset-y-0 left-0 z-50 flex flex-col bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 transition-all duration-300 ${
          sidebarOpen ? "w-64" : "w-20"
        }`}
      >
        {/* Sidebar Header */}
        <div className="h-16 flex items-center justify-between px-4 border-b border-gray-200 dark:border-gray-700">
          <Link to="/" className="flex items-center space-x-2">
            <ShoppingBag className="h-8 w-8 text-primary" />
            {sidebarOpen && (
              <span className="text-xl font-bold text-gray-900 dark:text-white">
                CloudScale
              </span>
            )}
          </Link>
          <button onClick={toggleSidebar} className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700">
            {sidebarOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
        </div>

        {/* Sidebar Navigation */}
        <nav className="flex-1 px-3 py-4 space-y-1">
          <Link
            to="/dashboard"
            className="flex items-center px-4 py-2.5 text-sm font-medium rounded-lg text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700"
          >
            <LayoutDashboard className="h-5 w-5 mr-3" />
            {sidebarOpen && <span>Dashboard</span>}
          </Link>
          <Link
            to="/products"
            className="flex items-center px-4 py-2.5 text-sm font-medium rounded-lg text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700"
          >
            <List className="h-5 w-5 mr-3" />
            {sidebarOpen && <span>Catalog</span>}
          </Link>
          <Link
            to="/cart"
            className="flex items-center px-4 py-2.5 text-sm font-medium rounded-lg text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700"
          >
            <ShoppingCart className="h-5 w-5 mr-3" />
            {sidebarOpen && <span>Shopping Cart</span>}
          </Link>
          <Link
            to="/orders"
            className="flex items-center px-4 py-2.5 text-sm font-medium rounded-lg text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700"
          >
            <Layers className="h-5 w-5 mr-3" />
            {sidebarOpen && <span>Orders</span>}
          </Link>
          <Link
            to="/inventory"
            className="flex items-center px-4 py-2.5 text-sm font-medium rounded-lg text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700"
          >
            <Warehouse className="h-5 w-5 mr-3" />
            {sidebarOpen && <span>Inventory</span>}
          </Link>
          <Link
            to="/users"
            className="flex items-center px-4 py-2.5 text-sm font-medium rounded-lg text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700"
          >
            <UsersIcon className="h-5 w-5 mr-3" />
            {sidebarOpen && <span>Users</span>}
          </Link>
          <Link
            to="/admin"
            className="flex items-center px-4 py-2.5 text-sm font-medium rounded-lg text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700"
          >
            <BarChart3 className="h-5 w-5 mr-3" />
            {sidebarOpen && <span>Admin KPIs</span>}
          </Link>
          <Link
            to="/workspace"
            className="flex items-center px-4 py-2.5 text-sm font-medium rounded-lg text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700"
          >
            <Layers className="h-5 w-5 mr-3" />
            {sidebarOpen && <span>Workspace</span>}
          </Link>
          <Link
            to="/settings"
            className="flex items-center px-4 py-2.5 text-sm font-medium rounded-lg text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700"
          >
            <Settings className="h-5 w-5 mr-3" />
            {sidebarOpen && <span>Settings</span>}
          </Link>
        </nav>
      </aside>

      {/* ── Main Panel ───────────────────────────────────────────────────────── */}
      <div className={`flex-1 flex flex-col transition-all duration-300 ${sidebarOpen ? "ml-64" : "ml-20"}`}>
        {/* Top Navbar */}
        <header className="h-16 flex items-center justify-between px-6 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
          {/* Search bar */}
          <div className="relative w-64">
            <span className="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none">
              <Search className="h-4 w-4 text-gray-400" />
            </span>
            <input
              type="text"
              placeholder="Search..."
              className="w-full pl-10 pr-4 py-2 text-sm bg-gray-100 dark:bg-gray-700 border border-transparent rounded-lg focus:outline-none focus:bg-white focus:border-primary dark:text-white"
            />
          </div>

          {/* Action buttons */}
          <div className="flex items-center space-x-4">
            <button onClick={toggleTheme} className="p-2 rounded-lg text-gray-500 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700">
              {theme === "dark" ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
            </button>
            <button className="relative p-2 rounded-lg text-gray-500 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700" aria-label={`Notifications, ${unreadCount} unread`}>
              <Bell className="h-5 w-5" />
              {unreadCount > 0 && (
                <span className="absolute -top-0.5 -right-0.5 h-5 w-5 flex items-center justify-center bg-red-500 text-white text-[10px] font-bold rounded-full">
                  {unreadCount > 9 ? "9+" : unreadCount}
                </span>
              )}
            </button>

            {/* Profile Dropdown */}
            <div className="flex items-center space-x-3">
              <div className="text-right hidden md:block">
                <p className="text-sm font-semibold text-gray-700 dark:text-white">
                  {user?.full_name}
                </p>
                <p className="text-xs text-gray-500 dark:text-gray-400 capitalize">
                  {user?.role}
                </p>
              </div>
              <button
                onClick={handleLogout}
                className="p-2 rounded-lg text-red-500 hover:bg-red-50 dark:hover:bg-red-950/20"
                title="Logout"
              >
                <LogOut className="h-5 w-5" />
              </button>
            </div>
          </div>
        </header>

        {/* Dynamic Route Outlet */}
        <main id="main-content" className="flex-grow p-6" role="main">
          <Outlet />
        </main>
      </div>
    </div>
  );
};
